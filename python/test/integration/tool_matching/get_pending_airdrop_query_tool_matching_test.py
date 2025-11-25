"""Tool matching integration tests for get pending airdrop query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.plugins.core_token_query_plugin import (
    core_token_query_plugin_tool_names,
)
from test.utils import create_langchain_test_setup

GET_PENDING_AIRDROP_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_PENDING_AIRDROP_QUERY_TOOL"
]


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
async def test_match_get_pending_airdrops_query(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches a simple pending airdrop query with explicit account ID."""
    account_id = "0.0.1231233"
    input_text = f"Show pending airdrops for account {account_id}"
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
    assert args[0] == GET_PENDING_AIRDROP_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == account_id


@pytest.mark.asyncio
async def test_match_get_pending_airdrops_phrase(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches a query with 'get pending airdrops' phrase."""
    account_id = "0.0.8888"
    input_text = f"Get pending airdrops for {account_id}"
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
    assert args[0] == GET_PENDING_AIRDROP_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == account_id


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get pending airdrop query tool is available in the toolkit."""
    tools = toolkit.get_tools()
    airdrop_tool = next(
        (t for t in tools if t.name == GET_PENDING_AIRDROP_QUERY_TOOL), None
    )

    assert airdrop_tool is not None
    assert airdrop_tool.name == GET_PENDING_AIRDROP_QUERY_TOOL
    assert "pending airdrops" in airdrop_tool.description
