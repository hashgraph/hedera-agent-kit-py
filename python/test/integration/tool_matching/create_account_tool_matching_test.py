"""Tool matching integration tests for create account tool.

This module tests whether the LLM correctly extracts parameters and matches
the correct tool when given various natural language inputs.
"""

from unittest.mock import AsyncMock

import pytest
from hiero_sdk_python import PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins import core_account_plugin_tool_names
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import SchedulingParams
from test.utils import create_langchain_test_setup


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


CREATE_ACCOUNT_TOOL = core_account_plugin_tool_names["CREATE_ACCOUNT_TOOL"]


@pytest.mark.asyncio
async def test_match_create_account_tool_with_default_params(
        agent_executor, toolkit, monkeypatch
):
    """Test that the tool matches with default params."""
    input_text = "Create a new Hedera account"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == CREATE_ACCOUNT_TOOL


@pytest.mark.asyncio
async def test_match_create_account_with_memo_and_initial_balance(
        agent_executor, toolkit, monkeypatch
):
    """Test tool matching with memo and initial balance."""
    input_text = (
        'Create an account with memo "Payment account" and initial balance 1.5 HBAR'
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_ACCOUNT_TOOL
    assert payload.get("account_memo") == "Payment account"
    assert payload.get("initial_balance") == 1.5


@pytest.mark.asyncio
async def test_match_create_account_with_explicit_public_key(
        agent_executor, toolkit, monkeypatch
):
    """Test tool matching with explicit public key."""
    public_key = PrivateKey.generate_ed25519().public_key().to_string_der()
    input_text = f"Create a new account with public key {public_key}"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_ACCOUNT_TOOL
    assert "public_key" in payload
    assert "302a" in payload.get("public_key", "")


@pytest.mark.asyncio
async def test_parse_max_automatic_token_associations(
        agent_executor, toolkit, monkeypatch
):
    """Test parsing of max automatic token associations."""
    input_text = "Create an account with max automatic token associations 10"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_ACCOUNT_TOOL
    assert payload.get("max_automatic_token_associations") == 10


@pytest.mark.asyncio
async def test_match_and_extract_params_for_scheduled_create_account(
        agent_executor, toolkit, monkeypatch
):
    """Test matching and parameter extraction for scheduled create account transaction."""
    input_text = (
        "Schedule creation of an account with max automatic token associations 10. "
        "Make it expire tomorrow and wait for its expiration time with executing it."
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_ACCOUNT_TOOL
    assert payload.get("max_automatic_token_associations") == 10

    scheduling_params: SchedulingParams = payload.get("scheduling_params", {})
    assert scheduling_params.is_scheduled is True
    assert scheduling_params.wait_for_expiry is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, expected_memo",
    [
        ("Create a new Hedera account", None),
        ("Create account with memo 'My memo'", "My memo"),
        ("Create account funded with 0.01 HBAR", None),
    ],
)
async def test_handle_various_natural_language_variations(
        agent_executor, toolkit, monkeypatch, input_text, expected_memo
):
    """Test various natural language variations."""
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(return_value=ToolResponse(human_message="mocked response"))
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    payload = args[1]
    assert args[0] == CREATE_ACCOUNT_TOOL
    if expected_memo:
        assert payload.get("account_memo") == expected_memo


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Test that create account tool is available in the toolkit."""
    tools = toolkit.get_tools()
    create_account_tool = next(
        (tool for tool in tools if tool.name == CREATE_ACCOUNT_TOOL), None
    )

    assert create_account_tool is not None
    assert create_account_tool.name == CREATE_ACCOUNT_TOOL
    assert "create a new Hedera account" in create_account_tool.description
