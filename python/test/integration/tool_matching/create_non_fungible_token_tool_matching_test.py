"""Tool matching integration tests for create non-fungible token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin import core_token_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import SchedulingParams
from test import create_langchain_test_setup

CREATE_NON_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names[
    "CREATE_NON_FUNGIBLE_TOKEN_TOOL"
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
async def test_match_create_nft_minimal(agent_executor, toolkit, monkeypatch):
    """Test that the tool matches when only the required token name/symbol are provided."""
    input_text = "Create a new non-fungible token named 'MyNFT', symbol 'MNFT'"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    resp = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "MyNFT"
    assert payload.get("token_symbol") == "MNFT"


@pytest.mark.asyncio
async def test_match_create_nft_full_spec(agent_executor, toolkit, monkeypatch):
    """Test tool matching with full specification including max supply."""
    input_text = (
        "Create a new NFT called 'ArtToken' with symbol 'ART' and max supply 500"
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
    assert args[0] == CREATE_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "ArtToken"
    assert payload.get("token_symbol") == "ART"
    assert payload.get("max_supply") == 500


@pytest.mark.asyncio
async def test_match_create_nft_infinite_supply(agent_executor, toolkit, monkeypatch):
    """Test tool matching when user explicitly requests unlimited/infinite supply."""
    input_text = (
        "Create a new NFT called 'InfiniteArt' with symbol 'INF' and unlimited supply"
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
    assert args[0] == CREATE_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "InfiniteArt"
    assert payload.get("token_symbol") == "INF"
    # Ensure max_supply is NOT set (None) when unlimited is requested
    assert payload.get("max_supply") is None


@pytest.mark.asyncio
async def test_match_and_extract_params_for_scheduled_nft_creation(
    agent_executor, toolkit, monkeypatch
):
    """Test matching and parameter extraction for a scheduled NFT creation."""
    input_text = (
        "Schedule creation of NFT 'FutureNFT' with symbol 'FNFT'. "
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

    assert args[0] == CREATE_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_name") == "FutureNFT"
    assert payload.get("token_symbol") == "FNFT"

    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that create non-fungible token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    create_token_tool = next(
        (tool for tool in tools if tool.name == CREATE_NON_FUNGIBLE_TOKEN_TOOL),
        None,
    )

    assert create_token_tool is not None
    assert create_token_tool.name == CREATE_NON_FUNGIBLE_TOKEN_TOOL
    assert (
        "creates a non-fungible token (NFT) on Hedera" in create_token_tool.description
    )
