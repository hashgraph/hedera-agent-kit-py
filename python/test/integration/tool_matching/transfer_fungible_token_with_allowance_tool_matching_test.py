"""Tool matching integration tests for transfer Fungible Token with allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins import core_token_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from test import create_langchain_test_setup

TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL = core_token_plugin_tool_names[
    "TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL"
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


@pytest.fixture
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_simple_transfer(agent_executor, toolkit, monkeypatch):
    """Test matching transfer fungible token with allowance."""
    input_text = "Transfer 100 of fungible token '0.0.33333' from 0.0.1002 to 0.0.2002 using allowance"
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
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert payload.get("token_id") == "0.0.33333"

    assert any(t.account_id  == "0.0.2002" and int(t.amount) == 100 for t in transfers)


@pytest.mark.asyncio
async def test_match_multiple_recipients(agent_executor, toolkit, monkeypatch):
    """Test matching transfer with multiple recipients."""
    input_text = "Use allowance from 0.0.1002 to send 50 TKN (Fungible token id: '0.0.33333') to account 0.0.2002 and 75 fungible tokens TKN to account 0.0.3003"
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
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert payload.get("token_id") == "0.0.33333"

    assert any(t.account_id == "0.0.2002" and int(t.amount) == 50 for t in transfers)
    assert any(t.account_id  == "0.0.3003" and int(t.amount) == 75 for t in transfers)


@pytest.mark.asyncio
async def test_match_spend_allowance_phrasing(agent_executor, toolkit, monkeypatch):
    """Test matching alternate phrasing ('spend allowance')."""
    input_text = "Spend allowance from account 0.0.1002 to send 25 fungible tokens with id 0.0.33333 to 0.0.2002"
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
    transfers = payload.get("transfers", [])

    assert args[0] == TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert payload.get("token_id") == "0.0.33333"
    assert any(t.account_id == "0.0.2002" and int(t.amount) == 25 for t in transfers)


@pytest.mark.asyncio
async def test_match_scheduling(agent_executor, toolkit, monkeypatch):
    """Test extraction of scheduling parameters."""
    input_text = "Transfer 100 of fungible token '0.0.33333' from 0.0.1002 to 0.0.2002 using allowance. Schedule this transaction and make it expire tomorrow and wait for its expiration time with executing it."
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

    assert args[0] == TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL

    scheduling = payload.get("scheduling_params")
    assert scheduling is not None
    assert scheduling.is_scheduled is True
    assert scheduling.wait_for_expiry is True