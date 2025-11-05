from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    # Setup before all tests
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup after all tests
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_simple_transfer(agent_executor, toolkit, monkeypatch):
    input_text = "Transfer 23 HBARs to 0.0.1"
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
    transfers = args[1]["transfers"]
    assert args[0] == TRANSFER_HBAR_TOOL
    assert any(t.account_id == "0.0.1" and t.amount == 23 for t in transfers)


@pytest.mark.asyncio
async def test_transfer_with_memo(agent_executor, toolkit, monkeypatch):
    input_text = 'Transfer 2 HBAR to 0.0.3333 with memo "Payment for services"'
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
    transfers = payload["transfers"]
    assert args[0] == TRANSFER_HBAR_TOOL
    assert any(t.account_id == "0.0.3333" and t.amount == 2 for t in transfers)
    assert payload["transaction_memo"] == "Payment for services"


@pytest.mark.asyncio
async def test_incorrect_params(agent_executor, toolkit, monkeypatch):
    # should match the tool anyway
    # the validation is performed on a tool level - not LLM level
    input_text = 'Transfer 1 HBAR to 0.0.0 with memo "Payment for services"'
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
    transfers = payload["transfers"]
    assert args[0] == TRANSFER_HBAR_TOOL
    assert any(t.account_id == "0.0.0" and t.amount == 1 for t in transfers)
    assert payload["transaction_memo"] == "Payment for services"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, account_id, amount",
    [
        ("Please send 5 HBAR to account 0.0.7777", "0.0.7777", 5),
        ("I want to transfer 3.14 HBAR to 0.0.8888", "0.0.8888", 3.14),
        ("Can you move 10 HBAR to 0.0.9999?", "0.0.9999", 10),
        ("Pay 0.01 HBAR to 0.0.1010", "0.0.1010", 0.01),
    ],
)
async def test_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, account_id, amount
):
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    transfers = args[1]["transfers"]
    assert args[0] == TRANSFER_HBAR_TOOL
    assert any(t.account_id == account_id and t.amount == amount for t in transfers)
