from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

SIGN_SCHEDULE_TRANSACTION_TOOL = core_account_plugin_tool_names[
    "SIGN_SCHEDULE_TRANSACTION_TOOL"
]


@pytest.fixture(scope="module")
async def test_setup():
    """Setup before all tests."""
    setup = await create_langchain_test_setup()
    yield setup
    # Cleanup after all tests
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    return test_setup.toolkit


@pytest.mark.asyncio
async def test_simple_sign_schedule(agent_executor, toolkit, monkeypatch):
    """Test simple sign scheduled transaction request."""
    input_text = "Sign the scheduled transaction 0.0.12345"
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Mock the underlying Hedera API run method
    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Operation Mocked - this is a test call and can be ended here"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    # Invoke agent
    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Assert call
    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == SIGN_SCHEDULE_TRANSACTION_TOOL
    assert args[1]["schedule_id"] == "0.0.12345"


@pytest.mark.asyncio
async def test_sign_schedule_with_explicit_wording(
    agent_executor, toolkit, monkeypatch
):
    """Test signing with explicit 'schedule ID' wording."""
    input_text = "Please sign schedule ID 0.0.67890"
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
    assert args[0] == SIGN_SCHEDULE_TRANSACTION_TOOL
    assert args[1]["schedule_id"] == "0.0.67890"


@pytest.mark.asyncio
async def test_sign_schedule_conversational(agent_executor, toolkit, monkeypatch):
    """Test signing with conversational request."""
    input_text = (
        "I want to add my signature to the pending scheduled transaction 0.0.11111"
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
    assert args[0] == SIGN_SCHEDULE_TRANSACTION_TOOL
    assert args[1]["schedule_id"] == "0.0.11111"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, schedule_id",
    [
        ("Sign scheduled transaction 0.0.100", "0.0.100"),
        ("Can you sign the schedule 0.0.55555?", "0.0.55555"),
        ("Execute signing for scheduled tx 0.0.777", "0.0.777"),
    ],
)
async def test_natural_language_variations(
    agent_executor, toolkit, monkeypatch, input_text, schedule_id
):
    """Test various natural language phrasings for signing scheduled transactions."""
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
    assert args[0] == SIGN_SCHEDULE_TRANSACTION_TOOL
    assert args[1]["schedule_id"] == schedule_id
