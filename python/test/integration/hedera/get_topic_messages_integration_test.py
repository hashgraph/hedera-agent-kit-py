"""Integration tests for GetTopicMessagesQueryTool.

This module validates querying topic messages through the tool -> mirror node flow,
testing message fetching, limit handling, and error scenarios.
"""

from typing import List

import pytest
from hiero_sdk_python import TopicId, PublicKey, PrivateKey, Hbar

from hedera_agent_kit.plugins.core_consensus_query_plugin import (
    GetTopicMessagesQueryTool,
)
from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.parameter_schemas import (
    TopicMessagesQueryParameters,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account
from test.utils.usd_to_hbar_service import UsdToHbarService


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ed25519()

    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key_pair.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.5)),
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
    operator_client.close()


@pytest.fixture
async def setup_topic_with_messages(setup_accounts):
    """Create a topic and submit multiple messages to it."""
    executor_client = setup_accounts["executor_client"]
    executor_wrapper = setup_accounts["executor_wrapper"]

    # Create a topic with executor as admin
    topic_admin_key: PublicKey = executor_client.operator_private_key.public_key()
    topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=topic_admin_key)
    )
    created_topic_id: TopicId = topic_resp.topic_id

    # Submit three messages to the topic
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=created_topic_id, message="Message 1"
        )
    )
    await wait(1000)
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=created_topic_id, message="Message 2"
        )
    )
    await wait(1000)
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=created_topic_id, message="Message 3"
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "created_topic_id": created_topic_id,
        "topic_admin_key": topic_admin_key,
    }


@pytest.mark.asyncio
async def test_fetch_all_topic_messages(setup_accounts, setup_topic_with_messages):
    """Should fetch all topic messages."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]
    created_topic_id = setup_topic_with_messages["created_topic_id"]

    tool = GetTopicMessagesQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id=str(created_topic_id)),
    )

    assert result.error is None
    assert result.extra is not None
    assert result.extra["topicId"] == str(created_topic_id)
    assert len(result.extra["messages"]) == 3

    # Messages are returned in descending order (newest first), reverse for assertion
    messages_text = [m["message"] for m in reversed(result.extra["messages"])]
    assert messages_text == ["Message 1", "Message 2", "Message 3"]

    assert "Messages for topic" in result.human_message
    assert "Message 1" in result.human_message


@pytest.mark.asyncio
async def test_fetch_messages_with_limit(setup_accounts, setup_topic_with_messages):
    """Should respect the limit parameter when fetching messages."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]
    created_topic_id = setup_topic_with_messages["created_topic_id"]

    tool = GetTopicMessagesQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id=str(created_topic_id), limit=2),
    )

    assert result.error is None
    assert result.extra is not None
    # Should return at most 2 messages
    assert len(result.extra["messages"]) <= 2


@pytest.mark.asyncio
async def test_fetch_messages_between_specific_timestamps(
    setup_accounts, setup_topic_with_messages
):
    """Should fetch messages between specific timestamps."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]
    created_topic_id = setup_topic_with_messages["created_topic_id"]

    tool = GetTopicMessagesQueryTool(context)

    # Fetch all messages first to get timestamps
    all_messages_result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id=str(created_topic_id)),
    )

    assert all_messages_result.error is None
    assert all_messages_result.extra is not None
    messages = all_messages_result.extra["messages"]
    assert len(messages) == 3

    # Get the second message's timestamp (messages are returned in descending order)
    # Reverse to get oldest first: [Message 1, Message 2, Message 3]
    ordered_messages = list(reversed(messages))
    message_2_timestamp = ordered_messages[1]["consensus_timestamp"]

    # Convert consensus_timestamp (e.g., "1234567890.123456789") to ISO format
    from datetime import datetime, timezone

    timestamp_seconds = int(message_2_timestamp.split(".")[0])
    start_time = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).isoformat()

    # Now query with start_time filter
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(
            topic_id=str(created_topic_id), start_time=start_time
        ),
    )

    assert result.error is None
    assert result.extra is not None
    # Should return 2 messages: Message 2 and Message 3
    assert len(result.extra["messages"]) == 2

    # Messages returned in descending order, reverse for assertion
    messages_text = [m["message"] for m in reversed(result.extra["messages"])]
    assert messages_text == ["Message 2", "Message 3"]


@pytest.mark.asyncio
async def test_fail_gracefully_for_nonexistent_topic(setup_accounts):
    """Should fail gracefully for a non-existent topic."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    tool = GetTopicMessagesQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id="0.0.999999999"),
    )

    # The tool returns "No messages found" for non-existent topics
    assert "No messages found for topic" in result.human_message


@pytest.mark.asyncio
async def test_empty_topic_returns_no_messages(setup_accounts):
    """Should return no messages for an empty topic."""
    executor_client = setup_accounts["executor_client"]
    executor_wrapper = setup_accounts["executor_wrapper"]
    context = setup_accounts["context"]

    # Create a new empty topic
    topic_admin_key: PublicKey = executor_client.operator_private_key.public_key()
    topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=topic_admin_key)
    )
    empty_topic_id: TopicId = topic_resp.topic_id

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = GetTopicMessagesQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id=str(empty_topic_id)),
    )

    assert "No messages found for topic" in result.human_message


@pytest.mark.asyncio
async def test_fetch_50_messages(setup_accounts):
    """Should fetch all topic messages from a topic with 5000 messages."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]
    executor_wrapper = setup_accounts["executor_wrapper"]
    topic_id = (
        await executor_wrapper.create_topic(
            CreateTopicParametersNormalised(
                submit_key=executor_client.operator_private_key.public_key()
            )
        )
    ).topic_id

    print(topic_id)

    for batch in range(4):
        params: List[SubmitTopicMessageParametersNormalised] = [
            SubmitTopicMessageParametersNormalised(
                topic_id=topic_id, message=f"Message {index}, Batch {batch}"
            )
            for index in range(25)
        ]
        await executor_wrapper.batch_submit_topic_message(
            params, batch_key=executor_client.operator_private_key
        )

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = GetTopicMessagesQueryTool(context)
    result = await tool.execute(
        executor_client,
        context,
        TopicMessagesQueryParameters(topic_id=str(topic_id)),
    )

    assert len(result.extra["messages"]) == 100
