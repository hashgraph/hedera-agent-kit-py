"""End-to-end tests for GetContractInfoQueryTool via the full LLM → tool flow.

This module validates querying contract information through the agent executor
and verifies error handling for invalid identifiers.
"""

from typing import Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import (
    ResponseParserService,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
)
from test.utils.teardown import return_hbars_and_delete_account


@pytest.fixture(scope="session")
def operator_client():
    """Initialize operator client for test session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Provide a HederaOperationsWrapper for the operator."""
    return HederaOperationsWrapper(operator_client)


@pytest.fixture
async def executor_account(operator_wrapper, operator_client):
    """Create a funded executor account and yield its client + wrapper."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20, in_tinybars=False)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    # Cleanup: return balance and delete executor account
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def langchain_setup(executor_account):
    """Initialize LangChain with executor client."""
    _, _, executor_client, _ = executor_account
    from test import create_langchain_test_setup

    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_setup):
    """Provide LangChain agent executor."""
    return langchain_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide executor wrapper (not directly used by tests, but kept for parity)."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide standard RunnableConfig."""
    return RunnableConfig(configurable={"thread_id": "contract_info_e2e"})


@pytest.fixture
async def response_parser(langchain_setup):
    """Provide the LangChain response parser."""
    return langchain_setup.response_parser


async def execute_get_contract_info_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute contract info query through the agent and return parsed tool data."""
    query_result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    parsed_tool_calls = response_parser.parse_new_tool_messages(query_result)

    if not parsed_tool_calls:
        raise ValueError("The get_contract_info_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_contract_info_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_contract_info_query_tool"
        )

    return tool_call.parsedData


@pytest.mark.asyncio
async def test_get_contract_info_via_agent_success(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Fetch info for a known public contract id and verify success content."""
    # Known publicly available contract on testnet (used elsewhere in tests)
    contract_id = "0.0.7350754"

    input_text = f"Get contract info for {contract_id}"
    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    assert parsed_data.get("error") in (None, "", False)
    assert "Contract Info Query Result:" in human_message
    assert f"- Contract ID: {contract_id}" in human_message


@pytest.mark.asyncio
async def test_get_contract_info_with_topic_id_should_error(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Using a Topic ID instead of Contract ID should yield an error from the tool."""
    topic_id = "0.0.7352574"  # Provided Topic ID; not a contract ID
    input_text = f"Get contract info for {topic_id}"

    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error = parsed_data.get("raw").get("error")
    assert error is not None
    assert "Failed to get contract info" in human_message


@pytest.mark.asyncio
async def test_get_contract_info_with_invalid_id_should_error(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Malformed or incorrect contract ID should trigger error handling."""
    invalid_id = "1.2.3.4"  # Deliberately invalid format
    input_text = f"Get contract info for {invalid_id}"

    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error = parsed_data.get("raw").get("error")
    assert error is not None
    assert "Failed to get contract info" in human_message
