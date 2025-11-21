import asyncio
from typing import cast

import pytest
from eth_keys.datatypes import PublicKey
from hiero_sdk_python import Client, PrivateKey, Hbar

from hedera_agent_kit_py.plugins.core_consensus_plugin import UpdateTopicTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    UpdateTopicParameters,
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import get_operator_client_for_tests, get_custom_client, MIRROR_NODE_WAITING_TIME
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5, in_tinybars=False),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "context": context,
    }

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


async def create_updatable_topic(
    wrapper: HederaOperationsWrapper, client: Client
) -> str:
    """Create a topic with an admin key so it can be updated."""
    create_params = CreateTopicParametersNormalised(
        memo="Original Memo",
        # Must set admin_key to the executor's key to allow updates by this client
        admin_key=client.operator_private_key.public_key(),
        submit_key=client.operator_private_key.public_key(),
    )
    resp = await wrapper.create_topic(create_params)

    await wait(MIRROR_NODE_WAITING_TIME)

    return str(resp.topic_id)


@pytest.mark.asyncio
async def test_update_topic_memo(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    topic_id = await create_updatable_topic(executor_wrapper, executor_client)

    tool = UpdateTopicTool(context)
    params = UpdateTopicParameters(
        topic_id=topic_id,
        topic_memo="Updated Memo",
        admin_key=True,  # Sign with current operator key
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Topic successfully updated" in result.human_message
    assert exec_result.raw.status == "SUCCESS"

    # Verify on-chain state
    info = executor_wrapper.get_topic_info(topic_id)
    assert info.memo == "Updated Memo"


@pytest.mark.asyncio
async def test_update_topic_submit_key(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    topic_id = await create_updatable_topic(executor_wrapper, executor_client)

    # Generate a new key for the submit key
    new_submit_key = PrivateKey.generate_ecdsa().public_key()

    tool = UpdateTopicTool(context)
    params = UpdateTopicParameters(
        topic_id=topic_id,
        submit_key=new_submit_key.to_string(),
        admin_key=True,  # Required to authorize the update
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"

    # Verify on-chain state
    info = executor_wrapper.get_topic_info(topic_id)
    assert info.submit_key.ECDSA_secp256k1.hex() == new_submit_key.to_string()


@pytest.mark.asyncio
async def test_fail_update_immutable_topic(setup_accounts):
    """Test updating a topic that has no admin key (immutable)."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    # Create immutable topic (no admin key)
    create_params = CreateTopicParametersNormalised(memo="Immutable Topic")
    resp = await executor_wrapper.create_topic(create_params)
    topic_id = str(resp.topic_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = UpdateTopicTool(context)
    params = UpdateTopicParameters(
        topic_id=topic_id,
        topic_memo="Should Fail",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    # The tool's pre-check or the network should reject this
    assert (
        "Topic does not have an admin key" in result.human_message
        or "unauthorized" in result.human_message.lower()
        or "INVALID_SIGNATURE" in str(result.error)
    )


@pytest.mark.asyncio
async def test_fail_invalid_topic_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = UpdateTopicTool(context)
    params = UpdateTopicParameters(
        topic_id="0.0.999999999",
        topic_memo="Fail",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Topic not found" in result.human_message