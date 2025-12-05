"""Tool matching integration tests for update topic tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_consensus_plugin import (
    core_consensus_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

UPDATE_TOPIC_TOOL = core_consensus_plugin_tool_names["UPDATE_TOPIC_TOOL"]

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
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_update_topic_tool_with_memo_and_submit_key(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update topic tool with memo and setting submit key to operator."""
    input_text = (
        "Update topic 0.0.5005 with memo 'new memo' and set submit key to my key"
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
    assert args[0] == UPDATE_TOPIC_TOOL
    assert payload.get("topic_id") == "0.0.5005"
    assert payload.get("topic_memo") == "new memo"
    # "my key" maps to boolean True in the schema for operator key injection
    assert payload.get("submit_key") is True


@pytest.mark.asyncio
async def test_match_with_multiple_fields(agent_executor, toolkit, monkeypatch):
    """Test matching update topic tool with memo, auto renew period and expiration."""
    input_text = (
        'For topic 0.0.1234 set memo "hello", auto renew period 7890000 '
        "and expiration time 2030-01-01T00:00:00Z"
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
    assert args[0] == UPDATE_TOPIC_TOOL
    assert payload.get("topic_id") == "0.0.1234"
    assert payload.get("topic_memo") == "hello"
    assert payload.get("auto_renew_period") == 7890000
    assert payload.get("expiration_time") == "2030-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that update topic tool is available in the toolkit."""
    tools = toolkit.get_tools()
    update_tool = next(
        (tool for tool in tools if tool.name == UPDATE_TOPIC_TOOL),
        None,
    )

    assert update_tool is not None
    assert update_tool.name == UPDATE_TOPIC_TOOL
    assert "update an existing Hedera Consensus Topic" in update_tool.description
