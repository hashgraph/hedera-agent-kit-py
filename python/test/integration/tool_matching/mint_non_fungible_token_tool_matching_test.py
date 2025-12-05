"""Tool matching integration tests for mint non-fungible token tool.
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

MINT_NON_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names[
    "MINT_NON_FUNGIBLE_TOKEN_TOOL"
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
async def agent(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_mint_nft_single_uri(agent, toolkit, monkeypatch):
    """Test matching mint NFT tool with single URI."""
    input_text = "Mint 0.0.5005 with metadata: ipfs://bafyreiao6ajgsfji6qsgbqwdtjdu5gmul7tv2v3pd6kjgcw5o65b2ogst4/metadata.json"
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
    assert args[0] == MINT_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.5005"
    assert payload.get("uris") == [
        "ipfs://bafyreiao6ajgsfji6qsgbqwdtjdu5gmul7tv2v3pd6kjgcw5o65b2ogst4/metadata.json"
    ]


@pytest.mark.asyncio
async def test_match_mint_nft_multiple_uris(agent, toolkit, monkeypatch):
    """Test matching mint NFT tool with multiple URIs."""
    input_text = "Mint NFTs for token 0.0.6006 with metadata URIs: ipfs://uri1, ipfs://uri2, ipfs://uri3"
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
    assert args[0] == MINT_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.6006"
    assert payload.get("uris") == ["ipfs://uri1", "ipfs://uri2", "ipfs://uri3"]


@pytest.mark.asyncio
async def test_extract_scheduling_parameters(agent, toolkit, monkeypatch):
    """Test matching and extracting scheduling parameters for minting."""
    input_text = (
        "Schedule Mint 0.0.5005 with metadata: ipfs://meta.json. "
        "Make it expire tomorrow and wait for its expiration time with executing it."
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
    assert args[0] == MINT_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.5005"
    assert payload.get("uris") == ["ipfs://meta.json"]

    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True
    assert scheduling_params.wait_for_expiry is True
    assert "expiration_time" in scheduling_params.model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected_token_id, expected_uris",
    [
        (
            "Mint NFT 0.0.7007 with metadata ipfs://abc123",
            "0.0.7007",
            ["ipfs://abc123"],
        ),
        (
            "Mint NFTs 0.0.8008 with metadata URIs ipfs://meta1 and ipfs://meta2",
            "0.0.8008",
            ["ipfs://meta1", "ipfs://meta2"],
        ),
    ],
)
async def test_natural_language_variations(
    agent, toolkit, monkeypatch, input_text, expected_token_id, expected_uris
):
    """Test various natural language expressions for minting NFTs."""
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
    assert args[0] == MINT_NON_FUNGIBLE_TOKEN_TOOL
    assert payload.get("token_id") == expected_token_id
    assert payload.get("uris") == expected_uris


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that mint non-fungible token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    mint_tool = next(
        (tool for tool in tools if tool.name == MINT_NON_FUNGIBLE_TOKEN_TOOL),
        None,
    )

    assert mint_tool is not None
    assert mint_tool.name == MINT_NON_FUNGIBLE_TOKEN_TOOL
    assert "mint NFTs with its unique metadata" in mint_tool.description
