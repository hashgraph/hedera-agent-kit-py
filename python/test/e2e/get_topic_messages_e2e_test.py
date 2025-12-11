"""End-to-end tests for GetTopicMessagesQueryTool using pre-created topics.

This module validates querying topic messages through the full LLM → tool → mirror node flow.
"""

from typing import Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParametersNormalised,
)
from test import HederaOperationsWrapper, create_langchain_test_setup, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)

from test.utils.teardown import return_hbars_and_delete_account


@pytest.fixture(scope="session")
def operator_client():
    """Initialize operator client for test session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Provide a HederaOperationsWrapper for the operator."""
    return HederaOperationsWrapper(operator_client)


@pytest.fixture
async def executor_account(operator_wrapper, operator_client):
    """Create a funded executor account and yield its client + wrapper."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20, in_tinybars=False)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    # Cleanup: return balance and delete executor account
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def langchain_setup(executor_account):
    """Initialize LangChain with executor client."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_setup):
    """Provide LangChain agent executor."""
    return langchain_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide executor wrapper for creating topics and submitting messages."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide standard RunnableConfig."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def response_parser(langchain_setup):
    """Provide the LangChain response parser."""
    return langchain_setup.response_parser


@pytest.fixture
async def topic_with_messages(executor_account, executor_wrapper):
    """Create a topic and submit multiple messages to it."""
    _, _, executor_client, _ = executor_account

    # Create topic with submit key set
    submit_key = executor_client.operator_private_key.public_key()
    create_topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(
            submit_key=submit_key,
        )
    )
    topic_id = create_topic_resp.topic_id

    # Submit three messages
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=topic_id, message="E2E Message 1"
        )
    )
    await wait(1000)
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=topic_id, message="E2E Message 2"
        )
    )
    await wait(1000)
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=topic_id, message="E2E Message 3"
        )
    )

    # Wait for mirrornode indexing
    await wait(MIRROR_NODE_WAITING_TIME)

    return topic_id


async def execute_get_topic_messages_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute topic messages query through the agent and return parsed tool data."""
    query_result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(query_result)

    if not parsed_tool_calls:
        raise ValueError("The get_topic_messages_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_topic_messages_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_topic_messages_query_tool"
        )

    return tool_call.parsedData


@pytest.mark.asyncio
async def test_get_all_messages_via_agent(
    agent_executor,
    topic_with_messages,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching all messages from a topic through the agent executor."""
    topic_id = topic_with_messages

    input_text = f"Get all messages from topic {topic_id}"
    parsed_data = await execute_get_topic_messages_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    assert raw_data is not None
    assert raw_data.get("topicId") == str(topic_id)

    messages = raw_data.get("messages")
    assert messages is not None
    assert len(messages) == 3

    # Messages are returned in descending order (newest first), reverse for assertion
    messages_text = [m["message"] for m in reversed(messages)]
    assert messages_text == ["E2E Message 1", "E2E Message 2", "E2E Message 3"]

    assert "Messages for topic" in human_message
    assert "E2E Message 1" in human_message


@pytest.mark.asyncio
async def test_handle_nonexistent_topic_via_agent(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test handling a non-existent topic gracefully via the agent."""
    fake_topic_id = "0.0.999999999"
    input_text = f"Get messages from topic {fake_topic_id}"

    parsed_data = await execute_get_topic_messages_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    assert "No messages found for topic" in human_message
