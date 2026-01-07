"""Tool matching integration tests for get token balances query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL = "get_account_token_balances_query_tool"


@pytest.fixture(scope="module")
async def test_setup():
    """Setup the LangChain test environment once per test module."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture(scope="module")
async def agent_executor(test_setup):
    """Provide the agent executor for invoking language queries."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit instance."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_get_token_balances_tool_direct_request(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a direct request with explicit account ID."""
    account_id = "0.0.5544333"
    input_text = f"Get the token balances for account {account_id}"
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
    assert args[0] == GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL
    payload = args[1]
    assert payload.get("account_id") == account_id


@pytest.mark.asyncio
async def test_match_get_token_balances_no_account_id(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches when no account ID is provided (defaults to operator)."""
    input_text = "Show me my token balances"
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
    assert args[0] == GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL
    payload = args[1]
    # Can be either None or the operator's account ID
    # If its None, the tool will inject the operator's account ID automatically
    assert (
        payload == {}
        or payload.get("account_id") is None
        or payload.get("account_id")
        == toolkit.get_hedera_agentkit_api().context.account_id
    )
