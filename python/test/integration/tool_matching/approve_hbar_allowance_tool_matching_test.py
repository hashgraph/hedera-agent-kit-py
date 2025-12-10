"""Tool matching integration tests for approve HBAR allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin.approve_hbar_allowance import (
    APPROVE_HBAR_ALLOWANCE_TOOL,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup is implicitly handled by the setup utility


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_approve_hbar_allowance_minimal(
    agent_executor, toolkit, monkeypatch
):
    """Test matching approve allowance tool with minimal params (implicit owner)."""
    input_text = "Approve 0.75 HBAR allowance to 0.0.4444"
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
    assert args[0] == APPROVE_HBAR_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.4444"
    assert payload.get("amount") == 0.75
    assert "owner_account_id" not in payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Approve 1 HBAR allowance from 0.0.1001 to spender 0.0.2002",
            {
                "owner_account_id": "0.0.1001",
                "spender_account_id": "0.0.2002",
                "amount": 1,
            },
        ),
        (
            'Approve 0.25 HBAR allowance to 0.0.3333 with memo "gift"',
            {
                "spender_account_id": "0.0.3333",
                "amount": 0.25,
                "transaction_memo": "gift",
            },
        ),
        (
            "Give spending allowance of 1.5 HBAR to 0.0.5555",
            {"spender_account_id": "0.0.5555", "amount": 1.5},
        ),
        (
            "Authorize 0.01 HBAR for spender 0.0.6666",
            {"spender_account_id": "0.0.6666", "amount": 0.01},
        ),
        (
            'Approve HBAR allowance of 2 to account 0.0.7777 with memo "ops budget"',
            {
                "spender_account_id": "0.0.7777",
                "amount": 2,
                "transaction_memo": "ops budget",
            },
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for approve HBAR allowance tool."""
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
    assert args[0] == APPROVE_HBAR_ALLOWANCE_TOOL

    # Check that all expected keys are present and match
    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that approve HBAR allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    allowance_tool = next(
        (tool for tool in tools if tool.name == APPROVE_HBAR_ALLOWANCE_TOOL), None
    )

    assert allowance_tool is not None
    assert allowance_tool.name == APPROVE_HBAR_ALLOWANCE_TOOL
    assert "approves an HBAR allowance" in allowance_tool.description
