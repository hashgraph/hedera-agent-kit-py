"""Tool matching integration tests for get contract info query tool.
This module verifies whether the LLM extracts parameters and selects the
correct tool when given various natural language inputs related to contract info.
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.shared.models import ToolResponse
from test.utils import create_langchain_test_setup

GET_CONTRACT_INFO_QUERY_TOOL = "get_contract_info_query_tool"
GET_TOPIC_INFO_QUERY_TOOL = "get_topic_info_query_tool"


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


@pytest.mark.asyncio
async def test_match_get_contract_info_verified_contract(
    agent_executor, toolkit, monkeypatch
):
    """Tool should match and extract a verified contract id."""
    contract_id = "0.0.7350754"  # provided verified contract id
    input_text = f"Get contract info for {contract_id}"
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
    assert args[0] == GET_CONTRACT_INFO_QUERY_TOOL
    payload = args[1]
    assert payload.get("contract_id") == contract_id


@pytest.mark.asyncio
async def test_match_get_contract_info_unverified_contract(
    agent_executor, toolkit, monkeypatch
):
    """Tool should match and extract an unverified contract id."""
    contract_id = "0.0.7351705"  # provided unverified contract id
    input_text = f"Please show contract details for {contract_id}"
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
    assert args[0] == GET_CONTRACT_INFO_QUERY_TOOL
    payload = args[1]
    assert payload.get("contract_id") == contract_id


@pytest.mark.asyncio
async def test_topic_id_is_not_a_contract_choose_topic_tool(
    agent_executor, toolkit, monkeypatch
):
    """If the user clearly refers to a Topic ID, the agent should not choose the contract info tool.

    We expect the topic info tool to be selected instead.
    """
    topic_id = "0.0.7350754"  # provided topic id (not a contract)
    input_text = f"Get topic info for {topic_id}"
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
    tool_name = args[0]
    payload = args[1]
    # Ensure the contract tool is NOT chosen; topic tool should be
    assert tool_name != GET_CONTRACT_INFO_QUERY_TOOL
    assert tool_name == GET_TOPIC_INFO_QUERY_TOOL
    assert payload.get("topic_id") == topic_id


@pytest.mark.asyncio
async def test_invalid_addresses_are_handled_and_error_bubbled(
    agent_executor, toolkit, monkeypatch
):
    """Provide invalid identifiers and ensure the contract tool is selected with the raw id,
    and that an error from execution is possible to bubble up (simulated).
    """
    invalid_cases = [
        ("Get contract info for abcdef", "abcdef"),
        ("Check contract 0.0.-1", "0.0.-1"),
        ("Contract info for 1.2.3.4", "1.2.3.4"),
        ("Show contract at 0xZZZ123", "0xZZZ123"),
    ]

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    hedera_api = toolkit.get_hedera_agentkit_api()

    for input_text, expected_id in invalid_cases:
        mock_run = AsyncMock(
            return_value=ToolResponse(
                human_message="Failed to get contract info: INVALID_CONTRACT_ID",
                error="Failed to get contract info: INVALID_CONTRACT_ID",
            )
        )
        monkeypatch.setattr(hedera_api, "run", mock_run)

        await agent_executor.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]}, config=config
        )

        mock_run.assert_awaited_once()
        args, kwargs = mock_run.call_args
        tool_name = args[0]
        payload = args[1]
        # For malformed inputs that still imply "contract", the agent should attempt the contract tool
        assert tool_name == GET_CONTRACT_INFO_QUERY_TOOL
        assert payload.get("contract_id") == expected_id


@pytest.mark.asyncio
async def test_tool_available(toolkit):
    """Ensure the get contract info tool is available in the toolkit."""
    tools = toolkit.get_tools()
    tool = next((t for t in tools if t.name == GET_CONTRACT_INFO_QUERY_TOOL), None)

    assert tool is not None
    assert tool.name == GET_CONTRACT_INFO_QUERY_TOOL
    assert (
        "This tool will return the information for a given Hedera EVM contract"
        in tool.description
    )
