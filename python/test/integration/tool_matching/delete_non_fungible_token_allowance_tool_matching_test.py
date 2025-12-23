"""Tool matching integration tests for delete NFT allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin import (
    core_token_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

DELETE_NFT_ALLOWANCE_TOOL = core_token_plugin_tool_names[
    "DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL"
]

MOCKED_RESPONSE = ToolResponse(
    human_message="Operation Mocked - this is a test call and can be ended here"
)


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture(scope="module")
async def agent(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_delete_nft_allowance_explicit(agent, toolkit, monkeypatch):
    """Test matching delete NFT allowance with explicit owner and serial numbers."""
    input_text = "Delete NFT allowance for token 0.0.3003 serials [1, 2] from owner 0.0.1001"
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

    assert args[0] == DELETE_NFT_ALLOWANCE_TOOL
    assert payload.get("owner_account_id") == "0.0.1001"
    assert payload.get("token_id") == "0.0.3003"
    assert payload.get("serial_numbers") == [1, 2]


@pytest.mark.asyncio
async def test_match_delete_nft_allowance_with_memo(agent, toolkit, monkeypatch):
    """Test matching delete NFT allowance with memo included."""
    input_text = (
        'Delete NFT allowance for token 0.0.5555 serials [1] with memo "cleanup"'
    )
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

    assert args[0] == DELETE_NFT_ALLOWANCE_TOOL
    assert payload.get("token_id") == "0.0.5555"
    assert payload.get("serial_numbers") == [1]
    assert payload.get("transaction_memo") == "cleanup"


@pytest.mark.asyncio
async def test_match_implicit_owner(agent, toolkit, monkeypatch):
    """Test defaults to implicit owner when not provided."""
    input_text = "Remove NFT allowance for token 0.0.6666 serial 3"
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

    assert args[0] == DELETE_NFT_ALLOWANCE_TOOL
    assert payload.get("token_id") == "0.0.6666"
    assert 3 in payload.get("serial_numbers", [])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected",
    [
        (
            "Revoke NFT allowance for token 0.0.1111 serials [1, 2]",
            {"token_id": "0.0.1111", "serial_numbers": [1, 2]},
        ),
        (
            'Delete NFT allowance for token 0.0.3333 serial 5 with memo "expired"',
            {
                "token_id": "0.0.3333",
                "serial_numbers": [5],
                "transaction_memo": "expired",
            },
        ),
    ],
)
async def test_handle_various_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected
):
    """Test various natural language expressions for deleting NFT allowance."""
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
    assert args[0] == DELETE_NFT_ALLOWANCE_TOOL

    # Check specific expected fields
    if "owner_account_id" in expected:
        assert payload.get("owner_account_id") == expected["owner_account_id"]
    if "token_id" in expected:
        assert payload.get("token_id") == expected["token_id"]
    if "serial_numbers" in expected:
        for serial in expected["serial_numbers"]:
            assert serial in payload.get("serial_numbers", [])
    if "transaction_memo" in expected:
        assert payload.get("transaction_memo") == expected["transaction_memo"]


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that delete NFT allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    tool = next(
        (tool for tool in tools if tool.name == DELETE_NFT_ALLOWANCE_TOOL),
        None,
    )

    assert tool is not None
    assert tool.name == DELETE_NFT_ALLOWANCE_TOOL
    assert "delete" in tool.description.lower() and "allowance" in tool.description.lower()
