"""Tool matching integration tests for submit topic message tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_consensus_plugin import (
    core_consensus_plugin_tool_names,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from test import create_langchain_test_setup

SUBMIT_TOPIC_MESSAGE_TOOL = core_consensus_plugin_tool_names[
    "SUBMIT_TOPIC_MESSAGE_TOOL"
]


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
async def test_simple_message_submission(agent_executor, toolkit, monkeypatch):
    """Test a simple message submission with topic_id and message."""
    input_text = "Submit message 'hello' to topic 0.0.123"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Mock the underlying Hedera API run method
    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    # Invoke agent
    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Assert call
    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == SUBMIT_TOPIC_MESSAGE_TOOL
    assert payload.get("topic_id") == "0.0.123"
    assert payload.get("message") == "hello"


@pytest.mark.asyncio
async def test_submission_with_memo(agent_executor, toolkit, monkeypatch):
    """Test a message submission that also includes a memo."""
    input_text = "Post 'test message' to topic 0.0.456 with memo 'testing'"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == SUBMIT_TOPIC_MESSAGE_TOOL
    assert payload.get("topic_id") == "0.0.456"
    assert payload.get("message") == "test message"
    assert payload.get("transaction_memo") == "testing"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected_topic_id, expected_message",
    [
        (
            "Send 'important update' to 0.0.789",
            "0.0.789",
            "important update",
        ),
        (
            "I want to publish 'new data' on topic 1.2.3",
            "1.2.3",
            "new data",
        ),
    ],
)
async def test_natural_language_variations(
    agent_executor,
    toolkit,
    monkeypatch,
    input_text,
    expected_topic_id,
    expected_message,
):
    """Test various natural language expressions for submitting a topic message."""
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == SUBMIT_TOPIC_MESSAGE_TOOL
    assert payload.get("topic_id") == expected_topic_id
    assert payload.get("message") == expected_message


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that submit topic message tool is available in the toolkit."""
    tools = toolkit.get_tools()
    submit_message_tool = next(
        (tool for tool in tools if tool.name == SUBMIT_TOPIC_MESSAGE_TOOL),
        None,
    )

    assert submit_message_tool is not None
    assert submit_message_tool.name == SUBMIT_TOPIC_MESSAGE_TOOL
    assert (
        "submit a message to a topic on the Hedera network"
        in submit_message_tool.description
    )
