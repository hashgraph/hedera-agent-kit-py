"""End-to-end tests for Get Exchange Rate Tool.

This module validates the agent-driven execution of exchange rate queries via
the Hedera Mirror Node. It replicates the behavior of the TypeScript E2E tests.
"""

import pytest
from langchain_core.runnables import RunnableConfig

from test.utils import create_langchain_test_setup
from test.utils.verification import extract_tool_response


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


# ============================================================================
# HELPER FUNCTION
# ============================================================================


async def execute_exchange_rate_query(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Helper to invoke the agent with the given query text."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_exchange_rate(agent_executor, langchain_config):
    """It should return the current exchange rate when no timestamp is provided."""
    input_text = "What is the current HBAR exchange rate?"

    result = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_exchange_rate_tool")

    assert observation is not None
    assert observation.extra is not None
    raw = observation.extra.get("exchange_rate")
    assert raw is not None

    current_rate = raw.get("current_rate")
    assert current_rate is not None
    assert isinstance(current_rate.get("cent_equivalent"), (int, float))
    assert isinstance(current_rate.get("hbar_equivalent"), (int, float))
    assert isinstance(current_rate.get("expiration_time"), (int, float))

    assert isinstance(observation.human_message, str)
    assert "Current Rate" in observation.human_message
    assert "Next Rate" in observation.human_message


@pytest.mark.asyncio
async def test_valid_epoch_timestamp(agent_executor, langchain_config):
    """It should return exchange rate for a valid epoch seconds timestamp."""
    ts = "1726000000"
    input_text = f"Get the HBAR exchange rate at timestamp {ts}"

    result = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_exchange_rate_tool")

    assert observation is not None
    assert observation.extra is not None
    raw = observation.extra.get("exchange_rate")
    assert raw is not None

    assert "current_rate" in raw
    assert isinstance(observation.human_message, str)
    assert "Details for timestamp" in observation.human_message
    assert "Current Rate" in observation.human_message


@pytest.mark.asyncio
async def test_valid_precise_nanos_timestamp(agent_executor, langchain_config):
    """It should return precise exchange rate data for nanos timestamp input."""
    ts = "1757512862.640825000"
    input_text = f"Get the HBAR exchange rate at timestamp {ts}"

    result = await execute_exchange_rate_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_exchange_rate_tool")

    assert observation is not None
    assert observation.extra is not None
    raw = observation.extra.get("exchange_rate")

    assert "current_rate" in raw
    assert isinstance(observation.human_message, str)
    assert "Details for timestamp" in observation.human_message
    assert "Current Rate" in observation.human_message
