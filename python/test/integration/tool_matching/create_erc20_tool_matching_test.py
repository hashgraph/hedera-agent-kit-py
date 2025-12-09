"""Tool matching integration tests for create ERC20 tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from __future__ import annotations
from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_evm_plugin import core_evm_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

CREATE_ERC20_TOOL = core_evm_plugin_tool_names["CREATE_ERC20_TOOL"]


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
async def test_match_simple_create_erc20_command(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches a simple ERC20 creation command."""
    input_text = (
        "Create an ERC20 token named TestToken with symbol TST and 1000 initial supply"
    )
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
    args, _ = mock_run.call_args
    assert args[0] == CREATE_ERC20_TOOL
    payload = args[1]
    assert payload.get("token_name") == "TestToken"
    assert payload.get("token_symbol") == "TST"
    assert payload.get("initial_supply") == 1000


@pytest.mark.asyncio
async def test_match_command_with_explicit_decimals(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches ERC20 creation with explicit decimals."""
    input_text = "Deploy ERC20 token called MyCoin with symbol MC, 500 initial supply, and 8 decimals"
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
    args, _ = mock_run.call_args
    assert args[0] == CREATE_ERC20_TOOL
    payload = args[1]
    assert payload.get("token_name") == "MyCoin"
    assert payload.get("token_symbol") == "MC"
    assert payload.get("initial_supply") == 500
    assert payload.get("decimals") == 8


@pytest.mark.asyncio
async def test_handle_minimal_input_with_defaults(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches when only token name and symbol are provided."""
    input_text = "Create an ERC20 token SampleCoin with symbol SC"
    config: "RunnableConfig" = {"configurable": {"thread_id": "1"}}

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
    args, _ = mock_run.call_args
    assert args[0] == CREATE_ERC20_TOOL
    payload = args[1]
    assert payload.get("token_name") == "SampleCoin"
    assert payload.get("token_symbol") == "SC"


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool correctly matches across multiple phrasing styles."""
    variations = [
        (
            "Deploy a new ERC20 called Alpha with symbol ALP",
            {"token_name": "Alpha", "token_symbol": "ALP"},
        ),
        (
            "Create token Alpha (symbol ALP) as ERC20",
            {"token_name": "Alpha", "token_symbol": "ALP"},
        ),
        (
            "Launch ERC20 token Alpha ticker ALP",
            {"token_name": "Alpha", "token_symbol": "ALP"},
        ),
    ]
    config: "RunnableConfig" = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()

    for input_text, expected in variations:
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
        args, _ = mock_run.call_args
        assert args[0] == CREATE_ERC20_TOOL
        payload = args[1]
        assert payload.get("token_name") == expected["token_name"]
        assert payload.get("token_symbol") == expected["token_symbol"]


@pytest.mark.asyncio
async def test_match_scheduled_transaction(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches when the user schedules the ERC20 creation."""
    input_text = (
        "Schedule deploy ERC20 token called MyCoin with symbol MC, 500 initial supply, and 8 decimals. "
        "Make it expire tomorrow and wait for its expiration time with executing it."
    )
    config: "RunnableConfig" = {"configurable": {"thread_id": "1"}}

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
    args, _ = mock_run.call_args
    assert args[0] == CREATE_ERC20_TOOL
    payload = args[1]
    assert payload.get("token_name") == "MyCoin"
    assert payload.get("token_symbol") == "MC"
    assert payload.get("initial_supply") == 500
    assert payload.get("decimals") == 8
    assert payload.get("scheduling_params") is not None
    scheduling = payload["scheduling_params"]
    assert scheduling.is_scheduled is True
    assert scheduling.wait_for_expiry is True
    assert scheduling.expiration_time is not None


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the create ERC20 tool is available in the toolkit."""
    tools = toolkit.get_tools()
    create_tool = next((t for t in tools if t.name == CREATE_ERC20_TOOL), None)

    assert create_tool is not None
    assert create_tool.name == CREATE_ERC20_TOOL
    assert "ERC20 token on Hedera" in create_tool.description
