"""Tool matching integration tests for associate token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_token_plugin import core_token_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from test import create_langchain_test_setup

ASSOCIATE_TOKEN_TOOL = core_token_plugin_tool_names["ASSOCIATE_TOKEN_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup is implicitly handled by the setup utility, if designed that way
    # setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_associate_token_minimal(agent_executor, toolkit, monkeypatch):
    """Test matching associate token tool with minimal params (no account_id)."""
    input_text = "Associate token 0.0.12345 to my account"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked association response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == ASSOCIATE_TOKEN_TOOL
    assert payload.get("token_ids") == ["0.0.12345"]
    # account_id is optional and will be inferred from context by the tool
    assert "account_id" not in payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Associate tokens 0.0.11111 and 0.0.22222 with account 0.0.9999",
            {
                "account_id": "0.0.9999",
                "token_ids": ["0.0.11111", "0.0.22222"],
            },
        ),
        (
            "Link token 0.0.33333 to account 0.0.4444",
            {"account_id": "0.0.4444", "token_ids": ["0.0.33333"]},
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for associate token tool."""
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked association response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == ASSOCIATE_TOKEN_TOOL

    # Check that all expected keys are present and match
    if "account_id" in expected:
        assert payload.get("account_id") == expected["account_id"]

    # Check for token_ids list
    payload_token_ids = payload.get("token_ids", [])
    expected_token_ids = expected.get("token_ids", [])
    assert isinstance(payload_token_ids, list)
    assert sorted(payload_token_ids) == sorted(expected_token_ids)


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that associate token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    associate_tool = next(
        (tool for tool in tools if tool.name == ASSOCIATE_TOKEN_TOOL), None
    )

    assert associate_tool is not None
    assert associate_tool.name == ASSOCIATE_TOKEN_TOOL
    assert "associate one or more tokens" in associate_tool.description
