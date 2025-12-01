"""Tool matching integration tests for update token tool.
This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from pprint import pprint
from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_token_plugin import (
    core_token_plugin_tool_names,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

UPDATE_TOKEN_TOOL = core_token_plugin_tool_names["UPDATE_TOKEN_TOOL"]

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
async def test_match_update_token_tool_with_name_and_symbol(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with token name and symbol update."""
    input_text = 'Update token 0.0.1001 name to "NewName" and symbol to "NNT"'
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.1001"
    assert payload.get("token_name") == "NewName"
    assert payload.get("token_symbol") == "NNT"


@pytest.mark.asyncio
async def test_match_update_token_tool_with_treasury_account(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with treasury account update."""
    input_text = "Change the treasury account of token 0.0.2002 to 0.0.3003"
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.2002"
    assert payload.get("treasury_account_id") == "0.0.3003"


@pytest.mark.asyncio
async def test_match_update_token_tool_with_admin_key_true(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with adminKey set to true (operator key)."""
    input_text = "Set the admin key for token 0.0.4004 to my key"
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.4004"
    assert payload.get("admin_key") is True


@pytest.mark.asyncio
async def test_match_update_token_tool_with_specific_supply_key(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with supplyKey set to a specific public key string."""
    specific_key = "302a300506032b6570032100e470123c5359a60714ee8f6e917d52a78f219156dd0a997d4c82b0e6c8e3e4a2"
    input_text = f"Update the supply key for token 0.0.5005 to {specific_key}"
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.5005"
    assert payload.get("supply_key") == specific_key


@pytest.mark.asyncio
async def test_match_update_token_tool_with_multiple_keys_and_memo(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with multiple key updates including setting to false (removing a key)."""
    input_text = 'For token 0.0.6006, set kycKey to true, disable the freezeKey and update the token memo to "Test Token"'
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.6006"
    assert payload.get("kyc_key") is True
    assert payload.get("freeze_key") is False
    assert payload.get("token_memo") == "Test Token"


@pytest.mark.asyncio
async def test_match_update_token_tool_with_metadata(
    agent_executor, toolkit, monkeypatch
):
    """Test matching update token tool with metadata update."""
    metadata_value = '{"description":"new metadata"}'
    input_text = f"Update the metadata for token 0.0.7007 to '{metadata_value}'"
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
    assert args[0] == UPDATE_TOKEN_TOOL
    assert payload.get("token_id") == "0.0.7007"
    assert payload.get("metadata") == metadata_value


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that the update token tool is available in the toolkit."""
    tools = toolkit.get_tools()
    update_tool = next(
        (tool for tool in tools if tool.name == UPDATE_TOKEN_TOOL),
        None,
    )

    assert update_tool is not None
    assert update_tool.name == UPDATE_TOKEN_TOOL
    assert "update an existing Hedera HTS token" in update_tool.description
