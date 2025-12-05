from typing import cast

import pytest

from hedera_agent_kit.plugins.core_consensus_plugin import SubmitTopicMessageTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    SubmitTopicMessageParameters,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import get_operator_client_for_tests, MIRROR_NODE_WAITING_TIME


@pytest.fixture(scope="module")
def setup_client():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    yield operator_client, operator_wrapper

    operator_client.close()


@pytest.fixture(scope="function")
async def setup_test_topic(setup_client):
    operator_client, operator_wrapper = setup_client

    # create a topic for each test so tests are isolated
    create_params = CreateTopicParametersNormalised(
        submit_key=None,  # No submit key
    )
    created = await operator_wrapper.create_topic(create_params)
    topic_id = str(created.topic_id)

    context = Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(operator_client.operator_account_id),
    )

    yield operator_client, operator_wrapper, context, topic_id


@pytest.mark.asyncio
async def test_submit_message_successfully(setup_test_topic):
    operator_client, operator_wrapper, context, topic_id = setup_test_topic

    tool = SubmitTopicMessageTool(context)
    params = SubmitTopicMessageParameters(
        topic_id=topic_id,
        message="hello from integration test",
        transaction_memo="integration tx memo",
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    mirror_node_messages = await operator_wrapper.get_topic_messages(topic_id)

    assert result is not None
    assert "Message submitted successfully" in result.human_message
    assert exec_result.raw is not None
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.status == "SUCCESS"

    assert len(mirror_node_messages["messages"]) != 0


@pytest.mark.asyncio
async def test_submit_message_invalid_topic_id(setup_test_topic):
    operator_client, _, context, _ = setup_test_topic

    tool = SubmitTopicMessageTool(context)
    params = SubmitTopicMessageParameters(
        topic_id="0.0.999999999",
        message="test message",
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert "Failed to submit message to topic" in result.human_message
    assert result.error is not None
    assert "INVALID_TOPIC_ID" in result.human_message or "INVALID_TOPIC_ID" in (
        result.error or ""
    )
