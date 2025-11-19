"""Tool matching integration tests for get exchange rate tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_misc_query_plugin import (
    core_misc_query_plugin_tool_names,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_EXCHANGE_RATE_TOOL = core_misc_query_plugin_tool_names["GET_EXCHANGE_RATE_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup the LangChain test environment once per test module."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor for invoking language queries."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit instance."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_get_exchange_rate_simple_query(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a simple query for the current HBAR exchange rate."""
    input_text = "What is the current HBAR exchange rate?"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == GET_EXCHANGE_RATE_TOOL
    payload = args[1]
    # No explicit timestamp expected
    assert payload == {} or payload.get("timestamp") is None


@pytest.mark.asyncio
async def test_extract_precise_timestamp_from_query(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool extracts a precise timestamp (with fractional seconds)."""
    input_text = "Get the HBAR exchange rate at 1726000000.123456789"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == GET_EXCHANGE_RATE_TOOL
    payload = args[1]
    assert payload.get("timestamp") == "1726000000.123456789"


@pytest.mark.asyncio
async def test_support_alternative_phrasing_and_integer_timestamp(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool supports alternative phrasing and integer timestamps."""
    input_text = "HBAR/USD rate at 1726000000"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == GET_EXCHANGE_RATE_TOOL
    payload = args[1]
    assert payload.get("timestamp") == "1726000000"


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get exchange rate tool is available in the toolkit."""
    tools = toolkit.get_tools()
    exchange_tool = next((t for t in tools if t.name == GET_EXCHANGE_RATE_TOOL), None)

    assert exchange_tool is not None
    assert exchange_tool.name == GET_EXCHANGE_RATE_TOOL
    assert "exchange rate" in exchange_tool.description
