"""Tool matching integration tests for get transaction record query tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_transaction_query_plugin import (
    core_transaction_query_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

GET_TRANSACTION_RECORD_QUERY_TOOL = core_transaction_query_plugin_tool_names[
    "GET_TRANSACTION_RECORD_QUERY_TOOL"
]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup


@pytest.fixture(scope="module")
async def agent(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_get_transaction_record_direct_request(agent, toolkit, monkeypatch):
    """Test matching the tool with a standard transaction ID format."""
    tx_id = "0.0.5-1755169980-651721264"
    input_text = f"Get the transaction record for transaction ID {tx_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked record response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TRANSACTION_RECORD_QUERY_TOOL
    assert payload.get("transaction_id") == tx_id


@pytest.mark.asyncio
async def test_match_get_transaction_record_and_parse_tx_id(
    agent, toolkit, monkeypatch
):
    """Test matching the tool and parsing the '@' transaction ID format."""
    tx_id = "0.0.90@1756968265.343000618"
    parsed_tx_id = "0.0.90-1756968265-343000618"
    input_text = f"Get the transaction record for transaction ID {tx_id}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked record response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == GET_TRANSACTION_RECORD_QUERY_TOOL
    assert payload.get("transaction_id") == parsed_tx_id


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that get transaction record tool is available in the toolkit."""
    tools = toolkit.get_tools()
    get_record_tool = next(
        (tool for tool in tools if tool.name == GET_TRANSACTION_RECORD_QUERY_TOOL),
        None,
    )

    assert get_record_tool is not None
    assert get_record_tool.name == GET_TRANSACTION_RECORD_QUERY_TOOL
    assert "return the transaction record" in get_record_tool.description
