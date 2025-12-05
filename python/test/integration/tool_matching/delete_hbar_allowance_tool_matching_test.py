"""Tool matching integration tests for delete HBAR allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins import core_account_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

DELETE_HBAR_ALLOWANCE_TOOL = core_account_plugin_tool_names[
    "DELETE_HBAR_ALLOWANCE_TOOL"
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
async def test_match_delete_hbar_allowance_explicit(agent, toolkit, monkeypatch):
    """Test matching delete HBAR allowance with explicit owner and spender."""
    input_text = "Delete HBAR allowance from 0.0.1001 to 0.0.2002"
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
    assert args[0] == DELETE_HBAR_ALLOWANCE_TOOL
    assert payload.get("owner_account_id") == "0.0.1001"
    assert payload.get("spender_account_id") == "0.0.2002"


@pytest.mark.asyncio
async def test_match_delete_hbar_allowance_with_memo(agent, toolkit, monkeypatch):
    """Test matching delete HBAR allowance with memo included."""
    input_text = 'Revoke HBAR allowance to 0.0.3333 with memo "cleanup"'
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
    assert args[0] == DELETE_HBAR_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.3333"
    assert payload.get("transaction_memo") == "cleanup"


@pytest.mark.asyncio
async def test_match_implicit_owner(agent, toolkit, monkeypatch):
    """Test defaults to implicit owner when not provided."""
    input_text = "Remove HBAR allowance for spender 0.0.4444"
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
    assert args[0] == DELETE_HBAR_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.4444"
    # owner_account_id should either be None or missing if not extracted
    assert not payload.get("owner_account_id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Revoke allowance for HBAR spending given to 0.0.5555",
            {"spender_account_id": "0.0.5555"},
        ),
        (
            'Delete HBAR allowance for account 0.0.6666 with memo "expired"',
            {"spender_account_id": "0.0.6666", "transaction_memo": "expired"},
        ),
        (
            "Remove HBAR allowance from account 0.0.7777 given to spender 0.0.8888",
            {"owner_account_id": "0.0.7777", "spender_account_id": "0.0.8888"},
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for deleting HBAR allowance."""
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
    assert args[0] == DELETE_HBAR_ALLOWANCE_TOOL

    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that delete HBAR allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    delete_allowance_tool = next(
        (tool for tool in tools if tool.name == DELETE_HBAR_ALLOWANCE_TOOL),
        None,
    )

    assert delete_allowance_tool is not None
    assert delete_allowance_tool.name == DELETE_HBAR_ALLOWANCE_TOOL
    assert "deletes an HBAR allowance" in delete_allowance_tool.description
