"""End-to-end tests for Get Exchange Rate Tool.

This module validates the agent-driven execution of exchange rate queries via
the Hedera Mirror Node. It replicates the behavior of the TypeScript E2E tests.
"""

from typing import Any
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from test.utils import create_langchain_test_setup


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
async def langchain_test_setup():
    """Initialize LangChain test setup for the session."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
def langchain_config():
    """Provide the runnable configuration for LangChain execution."""
    return RunnableConfig(configurable={"thread_id": "exchange_rate_e2e"})


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTION
# ============================================================================


async def execute_exchange_rate_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Helper to invoke the agent with the given query text and return parsed tool data."""
    result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(result)

    if not parsed_tool_calls:
        raise ValueError("The get_exchange_rate_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_exchange_rate_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_exchange_rate_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_exchange_rate(
    agent_executor, langchain_config, response_parser
):
    """It should return the current exchange rate when no timestamp is provided."""
    input_text = "What is the current HBAR exchange rate?"

    parsed_data = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    assert isinstance(human_message, str)
    assert "Current Rate" in human_message
    assert "Next Rate" in human_message

    exchange_rate = raw_data.get("exchange_rate")
    assert exchange_rate is not None

    current_rate = exchange_rate.get("current_rate")
    assert current_rate is not None
    assert isinstance(current_rate.get("cent_equivalent"), (int, float))
    assert isinstance(current_rate.get("hbar_equivalent"), (int, float))
    assert isinstance(current_rate.get("expiration_time"), (int, float))


@pytest.mark.asyncio
async def test_valid_epoch_timestamp(agent_executor, langchain_config, response_parser):
    """It should return exchange rate for a valid epoch seconds timestamp."""
    ts = "1726000000"
    input_text = f"Get the HBAR exchange rate at timestamp {ts}"

    parsed_data = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    exchange_rate = raw_data.get("exchange_rate")
    assert exchange_rate is not None

    assert "current_rate" in exchange_rate
    assert isinstance(human_message, str)
    assert "Details for timestamp" in human_message
    assert "Current Rate" in human_message


@pytest.mark.asyncio
async def test_valid_precise_nanos_timestamp(
    agent_executor, langchain_config, response_parser
):
    """It should return precise exchange rate data for nanos timestamp input."""
    ts = "1757512862.640825000"
    input_text = f"Get the HBAR exchange rate at timestamp {ts}"

    parsed_data = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    exchange_rate = raw_data.get("exchange_rate")
    assert exchange_rate is not None

    assert "current_rate" in exchange_rate
    assert isinstance(human_message, str)
    assert "Details for timestamp" in human_message
    assert "Current Rate" in human_message
