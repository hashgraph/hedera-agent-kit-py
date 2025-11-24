"""Tool matching integration tests for create fungible token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from pprint import pprint
from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_token_plugin import core_token_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import SchedulingParams
from test import create_langchain_test_setup

CREATE_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"]

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
async def test_match_create_fungible_token_minimal(
    agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches when only the required token name is provided."""
    input_text = (
        "Create a new fungible token named 'GoldCoin', symbol 'GC' and decimals 8"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    resp = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    pprint(resp)

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "GoldCoin"


@pytest.mark.asyncio
async def test_match_create_fungible_token_full_spec(
    agent_executor, toolkit, monkeypatch
):
    """Test tool matching with full specification including supply and decimals."""
    input_text = "Create a new token called 'Stable Dollar' with symbol 'USD', 6 decimals and initial supply 10000"
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
    assert args[0] == CREATE_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "Stable Dollar"
    assert payload.get("token_symbol") == "USD"
    assert payload.get("decimals") == 6
    assert payload.get("initial_supply") == 10000


@pytest.mark.asyncio
async def test_parse_finite_supply_and_max_supply(agent_executor, toolkit, monkeypatch):
    """Test parsing for finite supply type and explicit max supply."""
    input_text = "Create token 'Limited' , symbol 'LTD' with max supply 500000 and finite supply type"
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
    assert args[0] == CREATE_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "Limited"
    assert payload.get("max_supply") == 500000
    assert payload.get("supply_type") == 1  # SupplyType.FINITE = 1


@pytest.mark.asyncio
async def test_parse_infinite_supply(agent_executor, toolkit, monkeypatch):
    """Test parsing for infinite supply type."""
    input_text = "Create an infinite supply token 'UtilityToken' with 2 decimals, symbol 'UT' and supply type 'infinite'"
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
    assert args[0] == CREATE_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "UtilityToken"
    assert payload.get("supply_type") == 0  # SupplyType.INFINITE = 0
    assert payload.get("decimals") == 2


@pytest.mark.asyncio
async def test_match_and_extract_params_for_scheduled_creation(
    agent_executor, toolkit, monkeypatch
):
    """Test matching and parameter extraction for a scheduled token creation."""
    input_text = (
        "Schedule creation of token 'FutureCoin' with symbol 'FC'. "
        "Make it execute immediately."
    )
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

    assert args[0] == CREATE_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "FutureCoin"
    assert payload.get("token_symbol") == "FC"

    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True


@pytest.mark.asyncio
async def test_parse_infinite_supply(agent_executor, toolkit, monkeypatch):
    """Test parsing for infinite supply type."""
    input_text = "Create a token with 2 decimals and 1000 initial balance"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # the params lacks token symbol and name, so the tool should not be called
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that create fungible token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    create_token_tool = next(
        (tool for tool in tools if tool.name == CREATE_FUNGIBLE_TOKEN_TOOL),
        None,
    )

    assert create_token_tool is not None
    assert create_token_tool.name == CREATE_FUNGIBLE_TOKEN_TOOL
    assert "creates a fungible token on Hedera" in create_token_tool.description
