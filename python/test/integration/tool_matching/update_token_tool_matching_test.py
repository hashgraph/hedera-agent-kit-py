from unittest.mock import AsyncMock
import pytest
from hiero_sdk_python import PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_token_plugin import (
    core_token_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

UPDATE_TOKEN_TOOL = core_token_plugin_tool_names["UPDATE_TOKEN_TOOL"]


@pytest.fixture(scope="module")
async def test_setup():
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
async def test_update_token_name(agent_executor, toolkit, monkeypatch):
    input_text = 'Update token 0.0.5678 name to "New Token Name"'
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.5678"
    assert params["token_name"] == "New Token Name"


@pytest.mark.asyncio
async def test_update_token_symbol(agent_executor, toolkit, monkeypatch):
    input_text = 'Update token 0.0.1234 symbol to "NEWTKN"'
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.1234"
    assert params["token_symbol"] == "NEWTKN"


@pytest.mark.asyncio
async def test_update_token_memo(agent_executor, toolkit, monkeypatch):
    input_text = 'Update token 0.0.9999 memo to "Updated token memo"'
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.9999"
    assert params["token_memo"] == "Updated token memo"


@pytest.mark.asyncio
async def test_update_token_admin_key_with_operator(agent_executor, toolkit, monkeypatch):
    input_text = "Update token 0.0.4444 admin key to my key"
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.4444"
    assert params["admin_key"] is True


@pytest.mark.asyncio
async def test_update_token_supply_key(agent_executor, toolkit, monkeypatch):
    key_pair = PrivateKey.generate_ed25519()
    input_text = f"Update token 0.0.5555 and set the supply key to key: {key_pair.public_key().to_string()}"
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.5555"
    assert params["supply_key"] == key_pair.public_key().to_string()


@pytest.mark.asyncio
async def test_update_token_multiple_fields(agent_executor, toolkit, monkeypatch):
    input_text = (
        'Update token 0.0.7777 name to "Multi Updated Token" and symbol to "MUT" '
        'and memo to "Multiple updates"'
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.7777"
    assert params["token_name"] == "Multi Updated Token"
    assert params["token_symbol"] == "MUT"
    assert params["token_memo"] == "Multiple updates"


@pytest.mark.asyncio
async def test_schedule_token_update(agent_executor, toolkit, monkeypatch):
    input_text = (
        'Update token 0.0.2222 name to "Scheduled Token Update" '
        "and schedule the transaction instead of executing it immediately"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Scheduled token update created successfully.",
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.2222"
    assert params.get("scheduling_params") is not None


@pytest.mark.asyncio
async def test_update_token_treasury_account(agent_executor, toolkit, monkeypatch):
    input_text = "Update token 0.0.3333 treasury account to 0.0.9876"
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.3333"
    assert params["treasury_account_id"] == "0.0.9876"


@pytest.mark.asyncio
async def test_update_token_with_metadata(agent_executor, toolkit, monkeypatch):
    input_text = 'Update token 0.0.8888 metadata to "https://example.com/new-metadata.json"'
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
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_TOKEN_TOOL
    params = args[1]
    assert params["token_id"] == "0.0.8888"
    assert params["metadata"] == "https://example.com/new-metadata.json"
