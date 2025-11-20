"""Tool matching integration tests for get HBAR balance query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_HBAR_BALANCE_QUERY_TOOL = "get_hbar_balance_query_tool"


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
async def test_match_get_hbar_balance_tool_simple_query(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a simple balance query with explicit account ID."""
    input_text = "What is the HBAR balance of account 0.0.1234?"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == GET_HBAR_BALANCE_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.1234"


@pytest.mark.asyncio
async def test_match_get_hbar_balance_without_account_keyword(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches when the input omits the word 'account'."""
    input_text = "Check HBAR for 0.0.4321"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == GET_HBAR_BALANCE_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.4321"


@pytest.mark.asyncio
async def test_match_get_hbar_balance_for_my_account(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a query referring to 'my account'."""
    input_text = "Check my HBAR balance"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == GET_HBAR_BALANCE_QUERY_TOOL
    payload = args[1]
    # For "my account", LLM should fall back to context defaults (no explicit account ID)
    assert payload == {} or payload.get("account_id") is None


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get HBAR balance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    balance_tool = next(
        (t for t in tools if t.name == GET_HBAR_BALANCE_QUERY_TOOL), None
    )

    assert balance_tool is not None
    assert balance_tool.name == GET_HBAR_BALANCE_QUERY_TOOL
    assert "HBAR balance" in balance_tool.description
