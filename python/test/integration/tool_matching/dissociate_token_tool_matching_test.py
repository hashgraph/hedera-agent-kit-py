"""Tool matching integration tests for dissociate token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins import core_token_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from test import create_langchain_test_setup

DISSOCIATE_TOKEN_TOOL = core_token_plugin_tool_names["DISSOCIATE_TOKEN_TOOL"]

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
async def test_match_dissociate_single_token(agent, toolkit, monkeypatch):
    """Test matching dissociate token tool for a single token."""
    input_text = "Dissociate token 0.0.12345 from my account"
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
    assert args[0] == DISSOCIATE_TOKEN_TOOL
    # The tool expects a list of token_ids
    assert payload.get("token_ids") == ["0.0.12345"]


@pytest.mark.asyncio
async def test_match_dissociate_multiple_tokens_explicit_account(
    agent, toolkit, monkeypatch
):
    """Test matching dissociation of multiple tokens from a specific account."""
    input_text = "Dissociate tokens 0.0.111 and 0.0.222 from account 0.0.999"
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
    assert args[0] == DISSOCIATE_TOKEN_TOOL

    # Check account ID
    assert payload.get("account_id") == "0.0.999"

    # Check token IDs list
    token_ids = payload.get("token_ids", [])
    assert isinstance(token_ids, list)
    assert "0.0.111" in token_ids
    assert "0.0.222" in token_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected_token_ids",
    [
        ("Remove association of token 0.0.555", ["0.0.555"]),
        ("Unlink token 0.0.777 from wallet", ["0.0.777"]),
    ],
)
async def test_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected_token_ids
):
    """Test various natural language expressions for dissociating tokens."""
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
    assert args[0] == DISSOCIATE_TOKEN_TOOL
    assert payload.get("token_ids") == expected_token_ids


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that dissociate token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    dissociate_tool = next(
        (tool for tool in tools if tool.name == DISSOCIATE_TOKEN_TOOL),
        None,
    )

    assert dissociate_tool is not None
    assert dissociate_tool.name == DISSOCIATE_TOKEN_TOOL
    assert "dissociate one or more tokens" in dissociate_tool.description
