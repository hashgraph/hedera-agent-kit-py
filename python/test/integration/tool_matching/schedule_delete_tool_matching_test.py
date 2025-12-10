"""Tool matching integration tests for schedule delete tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins import core_account_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

SCHEDULE_DELETE_TOOL = core_account_plugin_tool_names["SCHEDULE_DELETE_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_matches_schedule_delete_tool_for_simple_delete_request(
    agent_executor, toolkit, monkeypatch
):
    """Test matching schedule delete tool with a simple request."""
    input_text = "Delete the scheduled transaction with ID 0.0.123456"
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
    assert args[0] == SCHEDULE_DELETE_TOOL
    payload = args[1]
    assert payload.get("schedule_id") == "0.0.123456"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Cancel scheduled transaction 0.0.789012",
            {"schedule_id": "0.0.789012"},
        ),
        (
            "Abort the scheduled transaction with ID 0.0.901234",
            {"schedule_id": "0.0.901234"},
        ),
        (
            "Please delete the scheduled transaction with ID 0.0.123456789 immediately",
            {"schedule_id": "0.0.123456789"},
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for schedule delete tool."""
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
    payload = args[1]
    assert args[0] == SCHEDULE_DELETE_TOOL
    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that schedule delete tool is available in the toolkit."""
    tools = toolkit.get_tools()
    schedule_tool = next(
        (tool for tool in tools if tool.name == SCHEDULE_DELETE_TOOL), None
    )

    assert schedule_tool is not None
    assert schedule_tool.name == SCHEDULE_DELETE_TOOL
    assert "delete a scheduled transaction" in schedule_tool.description
