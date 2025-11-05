"""Tool matching integration tests for delete account tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins import core_account_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

DELETE_ACCOUNT_TOOL = core_account_plugin_tool_names["DELETE_ACCOUNT_TOOL"]


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
async def test_match_delete_account_tool_with_account_id_only(
    agent_executor, toolkit, monkeypatch
):
    """Test that the delete account tool matches when only accountId is provided."""
    input_text = "Delete account 0.0.12345"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked delete response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == DELETE_ACCOUNT_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.12345"


@pytest.mark.asyncio
async def test_match_delete_account_tool_with_transfer_account_id(
    agent_executor, toolkit, monkeypatch
):
    """Test that delete account tool matches with transferAccountId parameter."""
    input_text = "Delete the account 0.0.1111 and transfer funds to 0.0.2222"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked delete response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == DELETE_ACCOUNT_TOOL
    payload = args[1]
    assert payload.get("account_id") == "0.0.1111"
    assert payload.get("transfer_account_id") == "0.0.2222"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("Delete account 0.0.42", {"account_id": "0.0.42"}),
        (
            "Remove account id 0.0.77 and send balance to 0.0.88",
            {"account_id": "0.0.77", "transfer_account_id": "0.0.88"},
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for delete account tool."""
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked delete response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == DELETE_ACCOUNT_TOOL
    for key, value in expected.items():
        assert payload.get(key) == value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that delete account tool is available in the toolkit."""
    tools = toolkit.get_tools()
    delete_account_tool = next(
        (tool for tool in tools if tool.name == DELETE_ACCOUNT_TOOL), None
    )

    assert delete_account_tool is not None
    assert delete_account_tool.name == DELETE_ACCOUNT_TOOL
    assert "delete an existing Hedera account" in delete_account_tool.description
