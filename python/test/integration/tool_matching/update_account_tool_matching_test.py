from unittest.mock import AsyncMock
import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

UPDATE_ACCOUNT_TOOL = core_account_plugin_tool_names["UPDATE_ACCOUNT_TOOL"]


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
async def test_update_account_memo(agent_executor, toolkit, monkeypatch):
    input_text = 'Update account 0.0.1234 memo to "updated via agent"'
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
    assert args[0] == UPDATE_ACCOUNT_TOOL
    params = args[1]
    assert params["account_id"] == "0.0.1234"
    assert params["account_memo"] == "updated via agent"


@pytest.mark.asyncio
async def test_update_max_automatic_token_associations(
    agent_executor, toolkit, monkeypatch
):
    input_text = "Set max automatic token associations for account 0.0.3333 to 10"
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
    assert args[0] == UPDATE_ACCOUNT_TOOL
    params = args[1]
    assert params["account_id"] == "0.0.3333"
    assert params["max_automatic_token_associations"] == 10


@pytest.mark.asyncio
async def test_update_decline_staking_reward(agent_executor, toolkit, monkeypatch):
    input_text = "Update account 0.0.7777 to decline staking rewards"
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
    assert args[0] == UPDATE_ACCOUNT_TOOL
    params = args[1]
    assert params["account_id"] == "0.0.7777"
    assert params["decline_staking_reward"] is True


@pytest.mark.asyncio
async def test_schedule_account_update(agent_executor, toolkit, monkeypatch):
    input_text = (
        'Update account 0.0.2222 memo to "scheduled update" '
        "and schedule the transaction instead of executing it immediately"
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Scheduled account update created successfully.",
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_ACCOUNT_TOOL
    params = args[1]
    assert params["account_id"] == "0.0.2222"
    assert params.get("scheduling_params") is not None


@pytest.mark.asyncio
async def test_update_non_existent_account(agent_executor, toolkit, monkeypatch):
    input_text = 'Update account 0.0.999999999 memo to "x"'
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    hedera_api = toolkit.get_hedera_agentkit_api()
    mock_run = AsyncMock(
        return_value=ToolResponse(
            human_message="Failed to update account: INVALID_ACCOUNT_ID"
        )
    )
    monkeypatch.setattr(hedera_api, "run", mock_run)

    await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    mock_run.assert_awaited_once()
    args, kwargs = mock_run.call_args
    assert args[0] == UPDATE_ACCOUNT_TOOL
    params = args[1]
    assert params["account_id"] == "0.0.999999999"
    assert params["account_memo"] == "x"
