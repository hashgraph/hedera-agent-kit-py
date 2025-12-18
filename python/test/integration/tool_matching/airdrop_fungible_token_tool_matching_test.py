"""Tool matching integration tests for Airdrop Fungible Token tool."""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin import (
    core_token_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

AIRDROP_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names[
    "AIRDROP_FUNGIBLE_TOKEN_TOOL"
]


@pytest.fixture(scope="module")
async def test_setup():
    # Setup before all tests
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture(scope="module")
async def agent_executor(test_setup):
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_airdrop_minimal(agent_executor, toolkit, monkeypatch):
    input_text = "Airdrop 10 tokens with id 0.0.1234 from acc 0.0.1001 to acc 0.0.2002"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Mock Hedera API
    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    # Invoke agent
    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Assertions
    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]

    assert args[0] == AIRDROP_FUNGIBLE_TOKEN_TOOL
    assert payload["token_id"] == "0.0.1234"
    assert payload["source_account_id"] == "0.0.1001"
    assert len(payload["recipients"]) == 1

    recipient = payload["recipients"][0]
    assert recipient.account_id == "0.0.2002"
    assert recipient.amount == 10


@pytest.mark.asyncio
async def test_match_airdrop_multiple_recipients(agent_executor, toolkit, monkeypatch):
    input_text = "Airdrop 5 of token 0.0.9999 from 0.0.1111 to 0.0.2222 and 0.0.3333"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Mock Hedera API
    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    # Invoke agent
    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Assertions
    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]

    assert args[0] == AIRDROP_FUNGIBLE_TOKEN_TOOL
    assert payload["token_id"] == "0.0.9999"
    assert payload["source_account_id"] == "0.0.1111"
    assert len(payload["recipients"]) == 2

    recipients = payload["recipients"]

    r1 = next((r for r in recipients if r.account_id == "0.0.2222"), None)
    r2 = next((r for r in recipients if r.account_id == "0.0.3333"), None)

    assert r1 is not None and r1.amount == 5
    assert r2 is not None and r2.amount == 5


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    tools = toolkit.get_tools()
    airdrop_tool = next(
        (tool for tool in tools if tool.name == AIRDROP_FUNGIBLE_TOKEN_TOOL),
        None,
    )

    assert airdrop_tool is not None
    assert airdrop_tool.name == AIRDROP_FUNGIBLE_TOKEN_TOOL
    assert "airdrop a fungible token" in airdrop_tool.description.lower()
