"""Tool matching integration tests for transfer HBAR with allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins import core_account_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

TRANSFER_HBAR_WITH_ALLOWANCE_TOOL = core_account_plugin_tool_names[
    "TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"
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


@pytest.fixture(scope="module")
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_simple_allowance_transfer(agent_executor, toolkit, monkeypatch):
    """Test matching transfer HBAR with an allowance tool for simple allowance transfer."""
    input_text = "Transfer 2 HBAR from 0.0.1002 to 0.0.2002 using allowance"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert any(t.account_id == "0.0.2002" and t.amount == 2 for t in transfers)


@pytest.mark.asyncio
async def test_handle_multiple_recipients(agent_executor, toolkit, monkeypatch):
    """Test handling multiple recipients in a single allowance transfer command."""
    input_text = (
        "Use allowance from 0.0.1002 to send 5 HBAR to 0.0.2002 and 10 HBAR to 0.0.3003"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert len(transfers) >= 2
    assert any(t.account_id == "0.0.2002" and t.amount == 5 for t in transfers)
    assert any(t.account_id == "0.0.3003" and t.amount == 10 for t in transfers)


@pytest.mark.asyncio
async def test_match_different_phrasing(agent_executor, toolkit, monkeypatch):
    """Test matching even if phrased differently ('spend allowance from...')."""
    input_text = "Spend allowance from account 0.0.1002 to send 3.5 HBAR to 0.0.2002"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert any(t.account_id == "0.0.2002" and t.amount == 3.5 for t in transfers)


@pytest.mark.asyncio
async def test_negative_match_without_allowance_keyword(
    agent_executor, toolkit, monkeypatch
):
    """Test that it does not falsely trigger when input does not mention allowance.
    It should likely trigger the standard transfer tool instead.
    """
    input_text = "Transfer 10 HBAR from 0.0.1002 to 0.0.2002"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # It might still call a tool (the standard transfer tool), but we ensure
    # it's NOT the allowance tool.
    if mock_run.called:
        args, _ = mock_run.call_args
        assert args[0] != TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
