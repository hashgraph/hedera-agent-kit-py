"""Tool matching integration tests for delete topic tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from pprint import pprint
from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_consensus_plugin import (
    core_consensus_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

DELETE_TOPIC_TOOL = core_consensus_plugin_tool_names["DELETE_TOPIC_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_delete_topic_tool_with_topic_id(
    agent_executor, toolkit, monkeypatch
):
    """Test that the delete topic tool matches when topic_id is provided."""
    input_text = "Delete topic 0.0.5005"
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
    assert args[0] == DELETE_TOPIC_TOOL
    payload = args[1]
    assert payload.get("topic_id") == "0.0.5005"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("Remove topic 0.0.6006", {"topic_id": "0.0.6006"}),
        (
            "Delete the Hedera topic 0.0.7007",
            {"topic_id": "0.0.7007"},
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for delete topic tool."""
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
    assert args[0] == DELETE_TOPIC_TOOL
    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that delete topic tool is available in the toolkit."""
    tools = toolkit.get_tools()
    pprint(tools)
    delete_topic_tool = next(
        (tool for tool in tools if tool.name == DELETE_TOPIC_TOOL), None
    )

    assert delete_topic_tool is not None
    assert delete_topic_tool.name == DELETE_TOPIC_TOOL
    assert "delete a given Hedera network topic" in delete_topic_tool.description
