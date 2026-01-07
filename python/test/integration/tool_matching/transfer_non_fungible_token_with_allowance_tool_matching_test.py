"""Tool matching integration tests for transfer NFT with allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin.transfer_non_fungible_token_with_allowance import (
    TRANSFER_NFT_WITH_ALLOWANCE_TOOL,
)
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup is implicitly handled by the setup utility


@pytest.fixture(scope="module")
async def agent_executor(test_setup):
    """Provide the agent executor."""
    return test_setup.agent


@pytest.fixture(scope="module")
async def toolkit(test_setup):
    """Provide the toolkit."""
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_tool_for_simple_nft_allowance_transfer(
    agent_executor, toolkit, monkeypatch
):
    """Test matching tool for simple NFT allowance transfer."""
    input_text = (
        "Transfer NFT 0.0.2001 serial 5 from 0.0.1002 to 0.0.3003 using allowance"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked transfer response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == TRANSFER_NFT_WITH_ALLOWANCE_TOOL
    assert payload.get("source_account_id") == "0.0.1002"
    assert payload.get("token_id") == "0.0.2001"

    recipients = payload.get("recipients")
    assert recipients is not None
    assert len(recipients) == 1
    # Updated to match schema: 'recipient' and 'serial_number'
    assert recipients[0].recipient == "0.0.3003"
    assert recipients[0].serial_number == 5


@pytest.mark.asyncio
async def test_support_multiple_serial_transfers_in_one_command(
    agent_executor, toolkit, monkeypatch
):
    """Test supporting multiple serial transfers in one command."""
    input_text = (
        "Use allowance from 0.0.1002 to send NFT 0.0.2001 serial 1 to 0.0.3003 "
        "and serial 2 to 0.0.4004"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked transfer response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == TRANSFER_NFT_WITH_ALLOWANCE_TOOL

    recipients = payload.get("recipients")
    assert recipients is not None
    assert len(recipients) == 2

    # Check that both recipients are present
    recipient_ids = [r.recipient for r in recipients]
    serial_numbers = [r.serial_number for r in recipients]

    assert "0.0.3003" in recipient_ids
    assert "0.0.4004" in recipient_ids
    assert 1 in serial_numbers
    assert 2 in serial_numbers


@pytest.mark.asyncio
async def test_match_with_transaction_memo(agent_executor, toolkit, monkeypatch):
    """Test matching with transaction memo."""
    input_text = (
        "Transfer NFT 0.0.2001 serial 3 from 0.0.1002 to 0.0.5005 "
        'using allowance with memo "batch transfer"'
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked transfer response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == TRANSFER_NFT_WITH_ALLOWANCE_TOOL
    assert payload.get("transaction_memo") == "batch transfer"


@pytest.mark.asyncio
async def test_match_alternate_phrasing(agent_executor, toolkit, monkeypatch):
    """Test matching with alternate phrasing variations."""
    variations = [
        "Send NFT token 0.0.2001 serial 7 from owner 0.0.1002 to 0.0.6006 with allowance",
        "Use approved allowance to move NFT 0.0.2001 serial 8 from 0.0.1002 to 0.0.7007",
        "Transfer via allowance NFT 0.0.2001 serial 9 from account 0.0.1002 to account 0.0.8008",
    ]

    hedera_api = toolkit.get_hedera_agentkit_api()
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    expected_serials = [7, 8, 9]
    expected_recipients = ["0.0.6006", "0.0.7007", "0.0.8008"]

    for i, input_text in enumerate(variations):
        mock_run = AsyncMock(
            return_value=ToolResponse(human_message="mocked transfer response")
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]}, config=config
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        payload = args[1]
        assert args[0] == TRANSFER_NFT_WITH_ALLOWANCE_TOOL
        assert payload.get("source_account_id") == "0.0.1002"
        assert payload.get("token_id") == "0.0.2001"

        recipients = payload.get("recipients")
        assert len(recipients) == 1
        # Updated to match schema: 'recipient' and 'serial_number'
        assert recipients[0].recipient == expected_recipients[i]
        assert recipients[0].serial_number == expected_serials[i]


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that transfer NFT with allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    transfer_nft_tool = next(
        (tool for tool in tools if tool.name == TRANSFER_NFT_WITH_ALLOWANCE_TOOL),
        None,
    )

    assert transfer_nft_tool is not None
    assert transfer_nft_tool.name == TRANSFER_NFT_WITH_ALLOWANCE_TOOL
    assert (
        "transfer non-fungible tokens (nfts) using an existing"
        in transfer_nft_tool.description.lower()
    )
