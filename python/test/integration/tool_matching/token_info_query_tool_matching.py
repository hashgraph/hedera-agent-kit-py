"""Tool matching integration tests for get token info query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins import core_token_query_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from test import create_langchain_test_setup

GET_TOKEN_INFO_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_TOKEN_INFO_QUERY_TOOL"
]

MOCKED_RESPONSE = ToolResponse(
    human_message="Operation Mocked - this is a test call and can be ended here"
)


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_get_token_info_query(agent, toolkit, monkeypatch):
    """Test matching 'Get token info' phrase."""
    token_id = "0.0.1231233"
    input_text = f"Get token info for {token_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TOKEN_INFO_QUERY_TOOL
    assert payload.get("token_id") == token_id


@pytest.mark.asyncio
async def test_match_token_information_query(agent, toolkit, monkeypatch):
    """Test matching 'Get token information' phrase."""
    token_id = "0.0.1231233"
    input_text = f"Get token information for {token_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TOKEN_INFO_QUERY_TOOL
    assert payload.get("token_id") == token_id


@pytest.mark.asyncio
async def test_match_token_details_query(agent, toolkit, monkeypatch):
    """Test matching 'Get token details' phrase."""
    token_id = "0.0.1231233"
    input_text = f"Get token details for {token_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TOKEN_INFO_QUERY_TOOL
    assert payload.get("token_id") == token_id


@pytest.mark.asyncio
async def test_match_query_token_phrase(agent, toolkit, monkeypatch):
    """Test matching 'Query token' phrase."""
    token_id = "0.0.1231233"
    input_text = f"Query token {token_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TOKEN_INFO_QUERY_TOOL
    assert payload.get("token_id") == token_id


@pytest.mark.asyncio
async def test_match_check_token_phrase(agent, toolkit, monkeypatch):
    """Test matching 'Check token' phrase."""
    token_id = "0.0.1231233"
    input_text = f"Check token {token_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TOKEN_INFO_QUERY_TOOL
    assert payload.get("token_id") == token_id


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that get token info tool is available in the toolkit."""
    tools = toolkit.get_tools()
    info_tool = next(
        (tool for tool in tools if tool.name == GET_TOKEN_INFO_QUERY_TOOL),
        None,
    )

    assert info_tool is not None
    assert info_tool.name == GET_TOKEN_INFO_QUERY_TOOL
    assert "return the information for a given Hedera token" in info_tool.description
