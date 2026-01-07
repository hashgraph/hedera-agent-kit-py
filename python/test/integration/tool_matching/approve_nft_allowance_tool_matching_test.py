"""Tool matching integration tests for approve NFT allowance tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin.approve_non_fungible_token_allowance import (
    APPROVE_NFT_ALLOWANCE_TOOL,
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
async def test_match_approve_nft_allowance_with_explicit_owner_single_serial_and_memo(
    agent_executor, toolkit, monkeypatch
):
    """Test matching approve NFT allowance with explicit owner, single serial and memo."""
    input_text = (
        "Approve NFT allowance for token 0.0.5005 serial 1 to spender 0.0.7007 "
        "from 0.0.6006 with memo 'gift'"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_NFT_ALLOWANCE_TOOL
    assert payload.get("owner_account_id") == "0.0.6006"
    assert payload.get("spender_account_id") == "0.0.7007"
    assert payload.get("token_id") == "0.0.5005"
    assert payload.get("serial_numbers") == [1]
    assert payload.get("transaction_memo") == "gift"


@pytest.mark.asyncio
async def test_match_approve_nft_allowance_implicit_owner_multiple_serials(
    agent_executor, toolkit, monkeypatch
):
    """Test matching approve NFT allowance using implicit owner for multiple serials."""
    input_text = "Approve NFT allowance for token 0.0.1111 serials 2 and 3 to 0.0.2222"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_NFT_ALLOWANCE_TOOL
    assert payload.get("spender_account_id") == "0.0.2222"
    assert payload.get("token_id") == "0.0.1111"
    assert payload.get("serial_numbers") == [2, 3]


@pytest.mark.asyncio
async def test_match_comma_separated_serial_numbers_and_alternate_phrasing(
    agent_executor, toolkit, monkeypatch
):
    """Test comma-separated serial numbers and alternate phrasing variations."""
    variations = [
        {
            "input": "Authorize NFT allowance on 0.0.3333 for serials 5, 6, 7 to account 0.0.4444",
            "expected": {
                "token_id": "0.0.3333",
                "spender_account_id": "0.0.4444",
                "serial_numbers": [5, 6, 7],
            },
        },
        {
            "input": "Give spending approval of NFTs token 0.0.8888 serial 9 to 0.0.9999",
            "expected": {
                "token_id": "0.0.8888",
                "spender_account_id": "0.0.9999",
                "serial_numbers": [9],
            },
        },
        {
            "input": 'Approve allowance for NFT token 0.0.1234 serials 10 and 12 for spender 0.0.4321 with memo "ops"',
            "expected": {
                "token_id": "0.0.1234",
                "spender_account_id": "0.0.4321",
                "serial_numbers": [10, 12],
                "transaction_memo": "ops",
            },
        },
    ]

    hedera_api = toolkit.get_hedera_agentkit_api()
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    for v in variations:
        mock_run = AsyncMock(
            return_value=ToolResponse(human_message="mocked allowance response")
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": v["input"]}]}, config=config
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        payload = args[1]
        assert args[0] == APPROVE_NFT_ALLOWANCE_TOOL

        for key, value in v["expected"].items():
            assert payload.get(key) == value


@pytest.mark.asyncio
async def test_match_approve_all_serials_with_all_serials_true(
    agent_executor, toolkit, monkeypatch
):
    """Test matching requests to approve all serials with all_serials=true."""
    variations = [
        {
            "input": "Approve NFT allowance for all serials of token 0.0.5555 to spender 0.0.6666",
            "token_id": "0.0.5555",
            "spender_account_id": "0.0.6666",
        },
        {
            "input": "Grant approval for the entire collection token 0.0.1010 to account 0.0.2020",
            "token_id": "0.0.1010",
            "spender_account_id": "0.0.2020",
        },
        {
            "input": 'Give spending rights for all NFTs of token 0.0.3030 to 0.0.4040 with memo "bulk"',
            "token_id": "0.0.3030",
            "spender_account_id": "0.0.4040",
            "transaction_memo": "bulk",
        },
    ]

    hedera_api = toolkit.get_hedera_agentkit_api()
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    for v in variations:
        mock_run = AsyncMock(
            return_value=ToolResponse(human_message="mocked allowance response")
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": v["input"]}]}, config=config
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        payload = args[1]
        assert args[0] == APPROVE_NFT_ALLOWANCE_TOOL
        assert payload.get("token_id") == v["token_id"]
        assert payload.get("spender_account_id") == v["spender_account_id"]
        assert payload.get("all_serials") is True

        if "transaction_memo" in v:
            assert payload.get("transaction_memo") == v["transaction_memo"]

        # Ensure serial_numbers is not set when approving for all
        assert "serial_numbers" not in payload or payload.get("serial_numbers") is None


@pytest.mark.asyncio
async def test_match_approve_entire_nft_collection(
    agent_executor, toolkit, monkeypatch
):
    """Test understanding alternate phrasing like approve entire NFT collection."""
    input_text = "Approve the entire NFT collection 0.0.7777 to spender 0.0.8888"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(human_message="mocked allowance response")
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == APPROVE_NFT_ALLOWANCE_TOOL
    assert payload.get("all_serials") is True
    assert payload.get("token_id") == "0.0.7777"
    assert payload.get("spender_account_id") == "0.0.8888"
    assert "serial_numbers" not in payload or payload.get("serial_numbers") is None


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that approve NFT allowance tool is available in the toolkit."""
    tools = toolkit.get_tools()
    nft_allowance_tool = next(
        (tool for tool in tools if tool.name == APPROVE_NFT_ALLOWANCE_TOOL),
        None,
    )

    assert nft_allowance_tool is not None
    assert nft_allowance_tool.name == APPROVE_NFT_ALLOWANCE_TOOL
    assert "approves an NFT allowance" in nft_allowance_tool.description
