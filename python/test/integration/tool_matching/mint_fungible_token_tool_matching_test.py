"""Tool matching integration tests for mint fungible token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_token_plugin import core_token_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import SchedulingParams
from test import create_langchain_test_setup

MINT_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["MINT_FUNGIBLE_TOKEN_TOOL"]

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
async def agent(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_mint_fungible_token_minimal(agent, toolkit, monkeypatch):
    """Test matching mint fungible token tool with minimal params."""
    input_text = "Mint 10 of token 0.0.12345"
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
    assert args[0] == MINT_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.12345"
    assert payload.get("amount") == 10


@pytest.mark.asyncio
async def test_extract_scheduling_parameters(agent, toolkit, monkeypatch):
    """Test matching and extracting scheduling parameters for minting."""
    input_text = (
        "Schedule mint 10 of token 0.0.12345. Make it expire tomorrow "
        "and wait for its expiration time with executing it."
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
    assert args[0] == MINT_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.12345"
    assert payload.get("amount") == 10

    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True
    assert scheduling_params.wait_for_expiry is True
    assert "expiration_time" in scheduling_params.model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected_token_id, expected_amount",
    [
        ("Mint 100 tokens of 0.0.56789", "0.0.56789", 100),
        ("Add 50 supply to fungible token 0.0.22222", "0.0.22222", 50),
        ("Increase supply of token 0.0.99999 by 200", "0.0.99999", 200),
    ],
)
async def test_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected_token_id, expected_amount
):
    """Test various natural language expressions for minting fungible tokens."""
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
    assert args[0] == MINT_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == expected_token_id
    assert payload.get("amount") == expected_amount


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that mint fungible token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    mint_tool = next(
        (tool for tool in tools if tool.name == MINT_FUNGIBLE_TOKEN_TOOL),
        None,
    )

    assert mint_tool is not None
    assert mint_tool.name == MINT_FUNGIBLE_TOKEN_TOOL
    assert "mint a given amount" in mint_tool.description
