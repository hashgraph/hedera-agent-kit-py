"""Tool matching integration tests for get account query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_ACCOUNT_QUERY_TOOL = "get_account_query_tool"


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
async def test_match_get_account_query_simple_request(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a simple get account info request with explicit account ID."""
    input_text = "Get account info for 0.0.1234"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == GET_ACCOUNT_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.1234"


@pytest.mark.asyncio
async def test_match_get_account_query_with_query_keyword(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches when user says 'query' instead of 'get'."""
    input_text = "Query details of account 0.0.5555"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == GET_ACCOUNT_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.5555"


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches for various natural language phrasings."""
    variations = [
        ("Please show me details for account 0.0.2222", "0.0.2222"),
        ("Look up account 0.0.3333", "0.0.3333"),
        ("Tell me about 0.0.4444", "0.0.4444"),
    ]
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()

    for input_text, expected_account_id in variations:
        mock_run = AsyncMock(return_value=ToolResponse(human_message="Operation Mocked - this is a test call and can be ended here"))
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]}, config=config
        )

        mock_run.assert_awaited_once()
        args, _ = mock_run.call_args
        assert args[0] == GET_ACCOUNT_QUERY_TOOL
        payload = args[1]
        assert payload.get("account_id") == expected_account_id


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get account query tool is available in the toolkit."""
    tools = toolkit.get_tools()
    account_tool = next((t for t in tools if t.name == GET_ACCOUNT_QUERY_TOOL), None)

    assert account_tool is not None
    assert account_tool.name == GET_ACCOUNT_QUERY_TOOL
    assert "account information" in account_tool.description
