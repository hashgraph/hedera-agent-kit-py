"""Tool matching integration tests for get topic info query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_TOPIC_INFO_QUERY_TOOL = "get_topic_info_query_tool"


@pytest.fixture(scope="module")
async def test_setup():
    """Setup the LangChain test environment once per test module."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor for invoking language queries."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit instance."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_get_topic_info_simple_request(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches a simple get topic info request with explicit topic ID."""
    input_text = "Get topic info for 0.0.1234"
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
    assert args[0] == GET_TOPIC_INFO_QUERY_TOOL
    payload = args[1]
    assert payload.get("topic_id") == "0.0.1234"


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches for various natural language phrasings."""
    variations = [
        ("Show topic info 0.0.2222", "0.0.2222"),
        ("Please get topic details for 0.0.3333", "0.0.3333"),
        ("Display HCS topic 0.0.4444 info", "0.0.4444"),
    ]
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()

    for input_text, expected_topic in variations:
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
        assert args[0] == GET_TOPIC_INFO_QUERY_TOOL
        payload = args[1]
        assert payload.get("topic_id") == expected_topic


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get topic info tool is available in the toolkit."""
    tools = toolkit.get_tools()
    tool = next((t for t in tools if t.name == GET_TOPIC_INFO_QUERY_TOOL), None)

    assert tool is not None
    assert tool.name == GET_TOPIC_INFO_QUERY_TOOL
    assert (
        "This tool will return the information for a given Hedera topic"
        in tool.description
    )
