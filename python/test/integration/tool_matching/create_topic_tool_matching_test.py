"""Tool matching integration tests for create topic tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

CREATE_TOPIC_TOOL = "create_topic_tool"


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
async def test_match_create_topic_tool_with_default_params(
    agent_executor, toolkit, monkeypatch
):
    """Test that the create topic tool matches with default parameters."""
    input_text = "Create a new topic"
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
    assert args[0] == CREATE_TOPIC_TOOL
    payload = args[1]
    assert isinstance(payload, dict)


@pytest.mark.asyncio
async def test_match_create_topic_with_memo_and_submit_key(
    agent_executor, toolkit, monkeypatch
):
    """Test tool matching when memo and submit key parameters are provided."""
    input_text = 'Create a topic with memo "Payments" and set submit key'
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
    assert args[0] == CREATE_TOPIC_TOOL
    assert payload.get("topic_memo") == "Payments"
    assert payload.get("submit_key") is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("Open a new consensus topic", {}),
        ('Create topic with memo "My memo"', {"topic_memo": "My memo"}),
        ("Create topic and set submit key", {"submit_key": True}),
        (
            'Create topic with transaction memo "TX: memo"',
            {"transaction_memo": "TX: memo"},
        ),
        ("Create topic without admin key", {"admin_key": False}),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for create topic tool."""
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
    assert args[0] == CREATE_TOPIC_TOOL
    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that create topic tool is available in the toolkit."""
    tools = toolkit.get_tools()
    create_topic_tool = next(
        (tool for tool in tools if tool.name == CREATE_TOPIC_TOOL), None
    )

    assert create_topic_tool is not None
    assert create_topic_tool.name == CREATE_TOPIC_TOOL
    assert "create a new topic" in create_topic_tool.description
