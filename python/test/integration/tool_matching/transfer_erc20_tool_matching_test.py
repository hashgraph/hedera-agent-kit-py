"""Tool matching integration tests for Transfer ERC20 tool."""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_evm_plugin import core_evm_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

TRANSFER_ERC20_TOOL = core_evm_plugin_tool_names["TRANSFER_ERC20_TOOL"]


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
async def test_match_simple_transfer_erc20_command(
    agent_executor, toolkit, monkeypatch
):
    """Test matching a simple transfer ERC20 command."""
    input_text = "Transfer 100 0.0.5678 ERC20 tokens from contract to 0x1234567890123456789012345678901234567890"
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

    assert args[0] == TRANSFER_ERC20_TOOL
    assert payload["contract_id"] == "0.0.5678"
    assert payload["recipient_address"] == "0x1234567890123456789012345678901234567890"
    assert payload["amount"] == 100


@pytest.mark.asyncio
async def test_match_command_with_hedera_addresses(
    agent_executor, toolkit, monkeypatch
):
    """Test matching a command with Hedera addresses."""
    input_text = "Send 50 tokens from ERC20 contract 0.0.1234 to account 0.0.5678"
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

    assert args[0] == TRANSFER_ERC20_TOOL
    assert payload["contract_id"] == "0.0.1234"
    assert payload["recipient_address"] == "0.0.5678"
    assert payload["amount"] == 50


@pytest.mark.asyncio
async def test_handle_decimal_amounts(agent_executor, toolkit, monkeypatch):
    """Test handling decimal amounts."""
    input_text = "Transfer 12 ERC20 tokens 0.0.1111 to 0.0.2222"
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

    assert args[0] == TRANSFER_ERC20_TOOL
    assert payload["contract_id"] == "0.0.1111"
    assert payload["recipient_address"] == "0.0.2222"
    assert payload["amount"] == 12


@pytest.mark.asyncio
async def test_match_scheduled_transaction(agent_executor, toolkit, monkeypatch):
    """Test matching a scheduled transaction."""
    input_text = (
        "Schedule transfer 100 0.0.5678 ERC20 tokens from contract to "
        "0x1234567890123456789012345678901234567890. Make it expire tomorrow "
        "and wait for its expiration time with executing it."
    )
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
    print(payload)

    assert args[0] == TRANSFER_ERC20_TOOL
    assert payload["contract_id"] == "0.0.5678"
    assert payload["recipient_address"] == "0x1234567890123456789012345678901234567890"
    assert payload["amount"] == 100
    assert "scheduling_params" in payload
    assert payload["scheduling_params"].is_scheduled is True
    assert payload["scheduling_params"].wait_for_expiry is True


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch
):
    """Test handling various natural language variations."""
    variations = [
        {
            "input": "Send 25 erc20 tokens from contract 0.0.1234 to 0.0.5678",
            "expected": {
                "contract_id": "0.0.1234",
                "recipient_address": "0.0.5678",
                "amount": 25,
            },
        },
        {
            "input": "Transfer 75 ERC20 tokens from contract 0.0.1111 to 0.0.2222",
            "expected": {
                "contract_id": "0.0.1111",
                "recipient_address": "0.0.2222",
                "amount": 75,
            },
        },
        {
            "input": "Move 200 erc20 tokens of contract 0.0.3333 to address 0.0.4444",
            "expected": {
                "contract_id": "0.0.3333",
                "recipient_address": "0.0.4444",
                "amount": 200,
            },
        },
        {
            "input": "Send 1000 ERC20 tokens (contract address: 0.0.5555) to recipient 0.0.6666",
            "expected": {
                "contract_id": "0.0.5555",
                "recipient_address": "0.0.6666",
                "amount": 1000,
            },
        },
    ]

    hedera_api = toolkit.get_hedera_agentkit_api()

    for variation in variations:
        config: RunnableConfig = {"configurable": {"thread_id": "1"}}
        mock_run = AsyncMock(
            return_value=ToolResponse(
                human_message="Operation Mocked - this is a test call and can be ended here"
            )
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": variation["input"]}]},
            config=config,
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        payload = args[1]

        assert args[0] == TRANSFER_ERC20_TOOL
        for key, value in variation["expected"].items():
            assert payload[key] == value


@pytest.mark.asyncio
async def test_handle_mixed_address_formats(agent_executor, toolkit, monkeypatch):
    """Test handling mixed address formats (EVM and Hedera)."""
    variations = [
        {
            "input": (
                "Transfer 10 tokens from EVM contract "
                "0x1111111111111111111111111111111111111111 to Hedera account 0.0.5678"
            ),
            "expected": {
                "contract_id": "0x1111111111111111111111111111111111111111",
                "recipient_address": "0.0.5678",
                "amount": 10,
            },
        },
        {
            "input": (
                "Send 5 ERC20 from Hedera 0.0.1234 to EVM address "
                "0x2222222222222222222222222222222222222222"
            ),
            "expected": {
                "contract_id": "0.0.1234",
                "recipient_address": "0x2222222222222222222222222222222222222222",
                "amount": 5,
            },
        },
    ]

    hedera_api = toolkit.get_hedera_agentkit_api()

    for variation in variations:
        config: RunnableConfig = {"configurable": {"thread_id": "1"}}
        mock_run = AsyncMock(
            return_value=ToolResponse(
                human_message="Operation Mocked - this is a test call and can be ended here"
            )
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": variation["input"]}]},
            config=config,
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        payload = args[1]

        assert args[0] == TRANSFER_ERC20_TOOL
        for key, value in variation["expected"].items():
            assert payload[key] == value


@pytest.mark.asyncio
async def test_handle_large_amounts(agent_executor, toolkit, monkeypatch):
    """Test handling large amounts."""
    input_text = "Transfer 1000000 ERC20 tokens from contract 0.0.1234 to 0.0.5678"
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

    assert args[0] == TRANSFER_ERC20_TOOL
    assert payload["contract_id"] == "0.0.1234"
    assert payload["recipient_address"] == "0.0.5678"
    assert payload["amount"] == 1000000


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that the transfer ERC20 tool is available."""
    tools = toolkit.get_tools()
    transfer_erc20 = next(
        (tool for tool in tools if tool.name == TRANSFER_ERC20_TOOL),
        None,
    )

    assert transfer_erc20 is not None
    assert transfer_erc20.name == TRANSFER_ERC20_TOOL
    assert "transfer of **erc20 tokens**" in transfer_erc20.description.lower()


@pytest.mark.asyncio
async def test_missing_amount(agent_executor, toolkit, monkeypatch):
    """Test handling missing amounts."""
    input_text = "Transfer ERC20 tokens from contract 0.0.1234 to 0.0.5678"
    config: RunnableConfig = {"configurable": {"thread_id": "2"}}

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
    mock_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_recipient(agent_executor, toolkit, monkeypatch):
    """Test handling missing amounts."""
    input_text = "Transfer 1243 ERC20 tokens from contract 0.0.1234"
    config: RunnableConfig = {"configurable": {"thread_id": "3"}}

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
    mock_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_erc20_address(agent_executor, toolkit, monkeypatch):
    """Test handling missing amounts."""
    input_text = "Transfer 1243 ERC20 tokens to account 0.0.5678"
    config: RunnableConfig = {"configurable": {"thread_id": "4"}}

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
    mock_run.assert_not_awaited()
