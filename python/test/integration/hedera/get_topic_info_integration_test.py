import pytest
from hiero_sdk_python import TopicId, PublicKey, PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS

from hedera_agent_kit.plugins.core_consensus_query_plugin import (
    GetTopicInfoQueryTool,
)
from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.parameter_schemas import (
    GetTopicInfoParameters,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ed25519()

    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key_pair.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(executor_account_id),
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "operator_wrapper": operator_wrapper,
        "context": context,
    }

    # Cleanup
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()


@pytest.fixture
async def setup_topic(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    executor_wrapper = setup_accounts["executor_wrapper"]

    # Create a topic with executor as admin
    topic_admin_key: PublicKey = executor_client.operator_private_key.public_key()
    topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=topic_admin_key)
    )
    created_topic_id: TopicId = topic_resp.topic_id

    # Submit a message to ensure the topic is active
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=created_topic_id, message="Hello"
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "created_topic_id": created_topic_id,
        "topic_admin_key": topic_admin_key,
    }


@pytest.mark.asyncio
async def test_fetch_topic_info(setup_accounts, setup_topic):
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]
    created_topic_id = setup_topic["created_topic_id"]

    tool = GetTopicInfoQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        GetTopicInfoParameters(topic_id=str(created_topic_id)),
    )

    assert result.error is None
    assert result.extra["topic_id"] == str(created_topic_id)
    assert result.extra["topic_info"]["topic_id"] == str(created_topic_id)
    assert "Here are the details for topic" in result.human_message


@pytest.mark.asyncio
async def test_fail_for_nonexistent_topic(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    tool = GetTopicInfoQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        GetTopicInfoParameters(topic_id="0.0.999999999"),
    )

    assert "Failed to get topic info" in result.human_message
