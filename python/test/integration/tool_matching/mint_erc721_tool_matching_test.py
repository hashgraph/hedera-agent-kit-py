"""Tool matching integration tests for min_erc721 (Mint ERC721) tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_evm_plugin import core_evm_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import SchedulingParams
from test.utils import create_langchain_test_setup

MINT_ERC721_TOOL = core_evm_plugin_tool_names["MINT_ERC721_TOOL"]

MOCKED_RESPONSE = ToolResponse(
    human_message="Operation Mocked - this is a test call and can be ended here"
)


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


@pytest.fixture
def run_config():
    """Provide a unique thread per test to avoid cross-test context leakage."""
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


@pytest.mark.asyncio
async def test_missing_contract_id_with_recipient_should_not_call_tool(
    agent_executor, toolkit, monkeypatch, run_config
):
    """If no contract/token is specified, the ERC721 mint tool must not be called."""
    # Missing the contract ID (token to mint), only a recipient is provided
    input_text = "Mint an ERC721 to 0xd94dc7f82f103757f715514e4a37186be6e4580b"
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Since the required contractId is not present, the tool should not be invoked
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_missing_contract_id_and_no_recipient_should_not_call_tool(
    agent_executor, toolkit, monkeypatch, run_config
):
    """If neither contract ID nor recipient is specified, tool should not be called."""
    input_text = "Please mint an ERC721 token"
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Lacking essential parameter (contractId); ensure no tool call is made
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_match_min_erc721_with_evm_to_address(
    agent_executor, toolkit, monkeypatch, run_config
):
    """Should match the min_erc721 tool and extract EVM recipient address."""
    input_text = (
        "Mint ERC721 token 0.0.6486793 to 0xd94dc7f82f103757f715514e4a37186be6e4580b"
    )
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == MINT_ERC721_TOOL
    payload = args[1]
    assert payload.get("contract_id") == "0.0.6486793"
    assert payload.get("to_address") == "0xd94dc7f82f103757f715514e4a37186be6e4580b"


@pytest.mark.asyncio
async def test_match_min_erc721_with_hedera_to_address(
    agent_executor, toolkit, monkeypatch, run_config
):
    """Should match the tool and keep Hedera account id for to_address (normaliser resolves later)."""
    # Be explicit about ERC721 and that the recipient is a Hedera account to avoid ambiguity
    input_text = "Mint ERC721 token 0.0.1234 to Hedera account 0.0.5678"
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == MINT_ERC721_TOOL
    payload = args[1]
    assert payload.get("contract_id") == "0.0.1234"
    assert payload.get("to_address") == "0.0.5678"


@pytest.mark.asyncio
async def test_match_min_erc721_without_to_address_defaults(
    agent_executor, toolkit, monkeypatch, run_config
):
    """If recipient not specified, tool should be called without to_address (normaliser will default)."""
    input_text = "Mint ERC721 token 0.0.9999"
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == MINT_ERC721_TOOL
    payload = args[1]
    assert payload.get("contract_id") == "0.0.9999"
    # Should not include to_address when not provided by the user
    assert "to_address" not in payload or payload.get("to_address") in (None, "")


@pytest.mark.asyncio
async def test_extract_scheduling_parameters(
    agent_executor, toolkit, monkeypatch, run_config
):
    """Should extract scheduling params for ERC721 minting when asked to schedule."""
    input_text = "Schedule mint of ERC721 token 0.0.1234 to 0x1111111111111111111111111111111111111111 and wait for its expiration"
    config: RunnableConfig = run_config

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=MOCKED_RESPONSE)
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, _ = mock_run.call_args
    assert args[0] == MINT_ERC721_TOOL
    payload = args[1]
    assert payload.get("contract_id") == "0.0.1234"
    assert payload.get("to_address") == "0x1111111111111111111111111111111111111111"
    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True
    assert scheduling_params.wait_for_expiry is True


@pytest.mark.asyncio
async def test_tool_available_and_prompt(toolkit):
    """Ensure mint_erc721 tool is available and prompt contains required help text."""
    tools = toolkit.get_tools()
    tool = next((t for t in tools if t.name == MINT_ERC721_TOOL), None)

    assert tool is not None
    assert tool.name == MINT_ERC721_TOOL
    description = tool.description
    assert "This tool will mint a new ERC721 token" in description
    assert "contract_id (str, required)" in description
    assert "to_address (str, optional)" in description
    assert "NOTE: the 'to_address' parameter is optional" in description
