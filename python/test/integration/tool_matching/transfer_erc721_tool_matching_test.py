"""Tool matching integration tests for Transfer ERC721 tool."""

from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_evm_plugin import core_evm_plugin_tool_names
from hedera_agent_kit.shared.models import ToolResponse
from test import create_langchain_test_setup

TRANSFER_ERC721_TOOL = core_evm_plugin_tool_names["TRANSFER_ERC721_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
    # Setup before all tests
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_match_simple_transfer_erc721_command(
    agent_executor, toolkit, monkeypatch
):
    """Test matching a simple transfer ERC721 command."""
    input_text = "Transfer ERC721 token 1 from contract 0.0.5678 from 0.0.1234 to 0x1234567890123456789012345678901234567890"
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.5678"
    assert payload["from_address"] == "0.0.1234"
    assert payload["to_address"] == "0x1234567890123456789012345678901234567890"
    assert payload["token_id"] == 1


@pytest.mark.asyncio
async def test_match_command_with_hedera_addresses(
    agent_executor, toolkit, monkeypatch
):
    """Test matching a command with Hedera addresses."""
    input_text = (
        "Send ERC721 token 5 from contract 0.0.1234 from 0.0.5678 to account 0.0.9999"
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.1234"
    assert payload["from_address"] == "0.0.5678"
    assert payload["to_address"] == "0.0.9999"
    assert payload["token_id"] == 5


@pytest.mark.asyncio
async def test_handle_command_without_explicit_from_address(
    agent_executor, toolkit, monkeypatch
):
    """Test handling command without explicit fromAddress."""
    input_text = "Transfer ERC721 token 3 from contract 0.0.1111 to 0.0.2222"
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.1111"
    assert payload["to_address"] == "0.0.2222"
    assert payload["token_id"] == 3
    # from_address should be None or not present (defaults to operator)


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(
    agent_executor, toolkit, monkeypatch
):
    """Test handling various natural language variations."""
    variations = [
        {
            "input": "Move ERC721 token 2 from contract 0.0.1234 from 0.0.5678 to 0.0.9999",
            "expected": {
                "contract_id": "0.0.1234",
                "from_address": "0.0.5678",
                "to_address": "0.0.9999",
                "token_id": 2,
            },
        },
        {
            "input": "Send ERC721 token 0 of contract 0.0.3333 from address 0.0.4444 to address 0.0.5555",
            "expected": {
                "contract_id": "0.0.3333",
                "from_address": "0.0.4444",
                "to_address": "0.0.5555",
                "token_id": 0,
            },
        },
        {
            "input": "Transfer ERC721 collectible 10 at 0.0.5555 from 0.0.6666 to recipient 0.0.7777",
            "expected": {
                "contract_id": "0.0.5555",
                "from_address": "0.0.6666",
                "to_address": "0.0.7777",
                "token_id": 10,
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

        assert args[0] == TRANSFER_ERC721_TOOL
        for key, value in variation["expected"].items():
            assert payload[key] == value


@pytest.mark.asyncio
async def test_handle_mixed_address_formats(agent_executor, toolkit, monkeypatch):
    """Test handling mixed address formats (EVM and Hedera)."""
    variations = [
        {
            "input": (
                "Transfer ERC721 token 1 from EVM contract "
                "0x1111111111111111111111111111111111111111 from Hedera 0.0.5678 to EVM "
                "0x2222222222222222222222222222222222222222"
            ),
            "expected": {
                "contract_id": "0x1111111111111111111111111111111111111111",
                "from_address": "0.0.5678",
                "to_address": "0x2222222222222222222222222222222222222222",
                "token_id": 1,
            },
        },
        {
            "input": (
                "Send NFT 5 from Hedera contract 0.0.1234 from EVM address "
                "0x3333333333333333333333333333333333333333 to Hedera account 0.0.5678"
            ),
            "expected": {
                "contract_id": "0.0.1234",
                "from_address": "0x3333333333333333333333333333333333333333",
                "to_address": "0.0.5678",
                "token_id": 5,
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

        assert args[0] == TRANSFER_ERC721_TOOL
        for key, value in variation["expected"].items():
            assert payload[key] == value


@pytest.mark.asyncio
async def test_handle_large_token_ids(agent_executor, toolkit, monkeypatch):
    """Test handling large token IDs."""
    input_text = (
        "Transfer ERC721 token 999999 from contract 0.0.1234 from 0.0.5678 to 0.0.9999"
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.1234"
    assert payload["from_address"] == "0.0.5678"
    assert payload["to_address"] == "0.0.9999"
    assert payload["token_id"] == 999999


@pytest.mark.asyncio
async def test_handle_token_id_zero(agent_executor, toolkit, monkeypatch):
    """Test handling token ID 0."""
    input_text = "Transfer ERC721 token 0 from contract 0.0.1234 to 0.0.5678"
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.1234"
    assert payload["to_address"] == "0.0.5678"
    assert payload["token_id"] == 0


@pytest.mark.asyncio
async def test_match_scheduled_transaction(agent_executor, toolkit, monkeypatch):
    """Test matching a scheduled transaction."""
    input_text = (
        "Schedule transfer ERC721 token 1 from contract 0.0.5678 from 0.0.1234 to "
        "0x1234567890123456789012345678901234567890. Make it expire tomorrow and wait for its expiration time with executing it."
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

    assert args[0] == TRANSFER_ERC721_TOOL
    assert payload["contract_id"] == "0.0.5678"
    assert payload["from_address"] == "0.0.1234"
    assert payload["to_address"] == "0x1234567890123456789012345678901234567890"
    assert payload["token_id"] == 1
    assert "scheduling_params" in payload
    assert payload["scheduling_params"].is_scheduled is True
    assert payload["scheduling_params"].wait_for_expiry is True


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that the transfer ERC721 tool is available."""
    tools = toolkit.get_tools()
    transfer_erc721 = next(
        (tool for tool in tools if tool.name == TRANSFER_ERC721_TOOL),
        None,
    )

    assert transfer_erc721 is not None
    assert transfer_erc721.name == TRANSFER_ERC721_TOOL
    assert "transfer an existing erc721 token" in transfer_erc721.description.lower()


@pytest.mark.asyncio
async def test_missing_token_id(agent_executor, toolkit, monkeypatch):
    """Test handling missing token ID."""
    input_text = "Transfer ERC721 from contract 0.0.1234 to 0.0.5678"
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
    """Test handling missing recipient address."""
    input_text = "Transfer ERC721 token 123 from contract 0.0.2222"
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
async def test_missing_erc721_contract(agent_executor, toolkit, monkeypatch):
    """Test handling missing ERC721 contract address."""
    input_text = "Transfer ERC721 token 123 to account 0.0.5678"
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
