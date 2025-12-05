"""End-to-end tests for delete topic tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey, Client, TopicId
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService

from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
)
from test.utils.teardown import return_hbars_and_delete_account


DEFAULT_EXECUTOR_BALANCE = Hbar(20, in_tinybars=False)

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
    """Create a temporary executor account for tests."""
    executor_key_pair = PrivateKey.generate_ecdsa()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    account_id = resp.account_id
    client = get_custom_client(account_id, executor_key_pair)
    wrapper = HederaOperationsWrapper(client)

    yield account_id, executor_key_pair, client, wrapper

    await return_hbars_and_delete_account(
        wrapper, account_id, operator_client.operator_account_id
    )


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Setup LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def toolkit(langchain_test_setup):
    """Provide the LangChain toolkit."""
    return langchain_test_setup.toolkit


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_call(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute a tool call via the agent and return the parsed response data."""
    raw = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(raw)

    if not parsed_tool_calls:
        raise ValueError("The delete_topic_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "delete_topic_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of delete_topic_tool"
        )

    return tool_call.parsedData


async def create_test_topic(
    wrapper: HederaOperationsWrapper, client: Client
) -> TopicId:
    """Create a topic to be deleted later."""
    admin_key = client.operator_private_key.public_key()
    resp = await wrapper.create_topic(
        CreateTopicParametersNormalised(admin_key=admin_key)
    )
    return resp.topic_id


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_delete_pre_created_topic(
    agent_executor,
    executor_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """E2E: delete an existing topic via agent command."""
    _, _, client, _ = executor_account
    topic_id = await create_test_topic(executor_wrapper, client)
    topic_str = str(topic_id)

    # Delete the topic
    parsed_data = await execute_agent_call(
        agent_executor,
        f"Delete the topic {topic_str}",
        langchain_config,
        response_parser,
    )

    human_message = parsed_data["humanMessage"]

    assert "deleted successfully" in human_message.lower()
    assert topic_str in human_message


@pytest.mark.asyncio
async def test_delete_non_existent_topic(
    agent_executor, langchain_config, response_parser
):
    """E2E: attempt to delete a non-existent topic."""
    fake_topic = "0.0.999999999"

    # We expect this call to fail and the agent to return an error/ToolResponse,
    # which is encapsulated in the parsed_data dictionary's 'humanMessage' field.
    parsed_data = await execute_agent_call(
        agent_executor,
        f"Delete the topic {fake_topic}",
        langchain_config,
        response_parser,
    )

    human_message = parsed_data["humanMessage"]

    assert any(
        err in human_message.upper()
        for err in ["INVALID_TOPIC_ID", "TOPIC_WAS_DELETED", "NOT_FOUND", "ERROR"]
    )
