"""Tool matching integration tests for approve fungible token allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin.approve_fungible_token_allowance import (
    APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup is implicitly handled by the setup utility


@pytest.fixture(scope="module")
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_approve_token_allowance_minimal(
    agent_executor, toolkit, monkeypatch
):
    """Test matching approve token allowance tool with minimal params (implicit owner)."""
    input_text = "Approve allowance of 1.23 tokens with id 0.0.7777 to spender 0.0.2002"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.2002"
    assert len(payload.get("token_approvals")) == 1

    approval = payload.get("token_approvals")[0]
    assert approval.token_id == "0.0.7777"
    assert approval.amount == 1.23
    assert "owner_account_id" not in payload or payload.get("owner_account_id") is None


@pytest.mark.asyncio
async def test_match_approve_token_allowance_with_owner_and_memo(
    agent_executor, toolkit, monkeypatch
):
    """Test matching approve token allowance tool with explicit owner and memo."""
    input_text = 'Approve allowance of 50 tokens for token 0.0.8888 from 0.0.1001 to spender 0.0.3003 with memo "marketing"'
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("owner_account_id") == "0.0.1001"
    assert payload.get("spender_account_id") == "0.0.3003"
    assert payload.get("transaction_memo") == "marketing"
    assert len(payload.get("token_approvals")) == 1

    approval = payload.get("token_approvals")[0]
    assert approval.token_id == "0.0.8888"
    assert approval.amount == 50


@pytest.mark.asyncio
async def test_match_multiple_token_allowances(agent_executor, toolkit, monkeypatch):
    """Test matching multiple token allowances."""
    input_text = (
        "Approve 10 tokens of 0.0.1 and 20 tokens of 0.0.2 for spender 0.0.4444"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.4444"
    approvals = payload.get("token_approvals")
    assert len(approvals) == 2

    t1 = next((a for a in approvals if a.token_id == "0.0.1"), None)
    t2 = next((a for a in approvals if a.token_id == "0.0.2"), None)

    assert t1 is not None and t1.amount == 10
    assert t2 is not None and t2.amount == 20


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that approve fungible token allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    allowance_tool = next(
        (tool for tool in tools if tool.name == APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL),
        None,
    )

    assert allowance_tool is not None
    assert allowance_tool.name == APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
    assert (
        "approves allowances for one or more fungible tokens"
        in allowance_tool.description
    )
