"""End-to-end tests for submit topic message tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey, TopicId
from langchain_core.runnables import RunnableConfig
import base64

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(
    10, in_tinybars=False
)  # Needs to cover account + topic ops


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """Initialize operator client once per test session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Create a wrapper for operator client operations."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary executor account for tests.
    Yields:
        tuple: (account_id, private_key, client, wrapper)
    Teardown:
        Returns funds and deletes the account.
    """
    executor_key: PrivateKey = PrivateKey.generate_ecdsa()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=executor_key.public_key()
        )
    )
    executor_account_id = resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Wait for account creation to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Set up LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "submit_topic_message_e2e"})


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> TopicId:
    """Helper function to create a topic for message submission tests.

    Creates a topic with no submit key, so the executor (as creator) can
    submit messages freely.
    """
    resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=None)
    )
    assert resp.topic_id is not None
    # Wait for topic creation to propagate to mirror node
    await wait(MIRROR_NODE_WAITING_TIME)
    return resp.topic_id


@pytest.fixture
async def pre_created_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> AsyncGenerator[TopicId, None]:
    """Provides a pre-created topic ID for tests."""
    topic_id = await create_test_topic(executor_wrapper)
    yield topic_id


async def execute_submit_message(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute message submission through the agent and return parsed tool data."""
    result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    parsed_tool_calls = response_parser.parse_new_tool_messages(result)

    if not parsed_tool_calls:
        raise ValueError("The submit_topic_message_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "submit_topic_message_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of submit_topic_message_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_submit_message_to_pre_created_topic(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    pre_created_topic: TopicId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test submitting a message to a topic via natural language."""
    target_topic_id = str(pre_created_topic)
    message = "Hello Hedera from the E2E test"

    input_text = f"Submit message '{message}' to topic {target_topic_id}"
    parsed_data = await execute_submit_message(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "submitted successfully" in human_message.lower()
    assert raw_data.get("transaction_id") is not None

    # Wait for mirror node ingestion
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify message was received
    topic_messages = await executor_wrapper.get_topic_messages(target_topic_id)
    # Check that at least one message exists (it might be the first or a subsequent one)
    assert len(topic_messages["messages"]) >= 1
    # Check that the submitted message content is present
    message_content_exists = any(
        base64.b64decode(msg["message"]).decode("utf-8") == message
        for msg in topic_messages["messages"]
    )
    assert message_content_exists


@pytest.mark.asyncio
async def test_fail_submit_to_non_existent_topic(
    agent_executor, langchain_config: RunnableConfig, response_parser: ResponseParserService
):
    """Test attempting to submit a message to a topic that does not exist."""
    fake_topic_id = "0.0.999999999"
    input_text = f"Submit message 'test' to topic {fake_topic_id}"

    parsed_data = await execute_submit_message(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]

    # Check for expected error codes in the message
    assert any(
        err in human_message.upper()
        for err in [
            "INVALID_TOPIC_ID",
            "NOT_FOUND",
            "ERROR",
        ]
    )
    assert parsed_data.get("raw", {}).get("error") is not None


@pytest.mark.asyncio
async def test_submit_message_scheduled(
    agent_executor,
    pre_created_topic: TopicId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test scheduling a topic message submission via natural language."""
    target_topic_id = str(pre_created_topic)
    message = "This is a scheduled message"

    input_text = f"Submit message '{message}' to topic {target_topic_id}. Schedule this transaction."

    parsed_data = await execute_submit_message(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert (
        "scheduled transaction created successfully"
        in human_message.lower()
    )
    assert raw_data.get("schedule_id") is not None
    assert raw_data.get("transaction_id") is not None