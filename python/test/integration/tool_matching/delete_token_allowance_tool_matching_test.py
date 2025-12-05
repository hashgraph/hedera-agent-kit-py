"""Tool matching integration tests for delete Token allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin import (
    core_token_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

DELETE_TOKEN_ALLOWANCE_TOOL = core_token_plugin_tool_names[
    "DELETE_TOKEN_ALLOWANCE_TOOL"
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
async def test_match_delete_token_allowance_explicit(agent, toolkit, monkeypatch):
    """Test matching delete Token allowance with explicit owner, spender and token."""
    input_text = "Delete token allowance given from 0.0.1001 to account 0.0.2002 for token 0.0.3003"
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

    assert args[0] == DELETE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("owner_account_id") == "0.0.1001"
    assert payload.get("spender_account_id") == "0.0.2002"
    # Token IDs are typically expected as a list
    assert "0.0.3003" in payload.get("token_ids", [])


@pytest.mark.asyncio
async def test_match_delete_token_allowance_with_memo(agent, toolkit, monkeypatch):
    """Test matching delete Token allowance with memo included."""
    input_text = (
        'Delete allowance for account 0.0.4444 for token 0.12345 with memo "cleanup"'
    )
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

    assert args[0] == DELETE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.4444"
    assert "0.12345" in payload.get("token_ids", [])
    assert payload.get("transaction_memo") == "cleanup"


@pytest.mark.asyncio
async def test_match_implicit_owner(agent, toolkit, monkeypatch):
    """Test defaults to implicit owner when not provided."""
    input_text = "Remove token allowance for spender 0.0.5555 on token 0.0.6666"
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

    assert args[0] == DELETE_TOKEN_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.5555"
    assert "0.0.6666" in payload.get("token_ids", [])
    # Owner should be None/implicit here
    assert not payload.get("owner_account_id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Revoke allowance for token 0.0.1111 given to 0.0.2222",
            {"spender_account_id": "0.0.2222", "token_id": "0.0.1111"},
        ),
        (
            'Delete allowance for token 0.0.3333 spender 0.0.4444 with memo "expired"',
            {
                "spender_account_id": "0.0.4444",
                "token_id": "0.0.3333",
                "transaction_memo": "expired",
            },
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for deleting Token allowance."""
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
    assert args[0] == DELETE_TOKEN_ALLOWANCE_TOOL

    # Check specific expected fields
    if "owner_account_id" in expected:
        assert payload.get("owner_account_id") == expected["owner_account_id"]
    if "spender_account_id" in expected:
        assert payload.get("spender_account_id") == expected["spender_account_id"]
    if "token_id" in expected:
        assert expected["token_id"] in payload.get("token_ids", [])
    if "transaction_memo" in expected:
        assert payload.get("transaction_memo") == expected["transaction_memo"]


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that delete Token allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    tool = next(
        (tool for tool in tools if tool.name == DELETE_TOKEN_ALLOWANCE_TOOL),
        None,
    )

    assert tool is not None
    assert tool.name == DELETE_TOKEN_ALLOWANCE_TOOL
    assert "This tool deletes token allowance" in tool.description
