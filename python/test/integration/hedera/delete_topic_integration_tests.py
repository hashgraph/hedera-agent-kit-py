from typing import cast

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar

from hedera_agent_kit_py.plugins.core_consensus_plugin import DeleteTopicTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    DeleteTopicParameters,
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
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
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "context": context,
    }

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


async def create_temp_topic(
    executor_wrapper: HederaOperationsWrapper, executor_client: Client
):
    create_params = CreateTopicParametersNormalised(
        admin_key=executor_client.operator_private_key.public_key()
    )
    resp = await executor_wrapper.create_topic(create_params)
    return resp.topic_id


@pytest.mark.asyncio
async def test_delete_topic_successfully(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    topic_id = await create_temp_topic(executor_wrapper, executor_client)
    assert topic_id is not None
    print(f"Created topic {str(topic_id)}")

    tool = DeleteTopicTool(context)
    params = DeleteTopicParameters(topic_id=str(topic_id))
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Topic with id" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.status == "SUCCESS"


@pytest.mark.asyncio
async def test_delete_invalid_topic_id_should_fail(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = DeleteTopicTool(context)
    params = DeleteTopicParameters(topic_id="invalid-topic")
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Failed to delete the topic" in result.human_message
    assert result.error is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_topic_should_fail(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = DeleteTopicTool(context)
    params = DeleteTopicParameters(topic_id="0.0.999999999")
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "INVALID_TOPIC_ID" in result.human_message or result.error is not None
    assert result.error is not None
    assert "Failed to delete the topic" in result.human_message
