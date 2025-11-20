"""End-to-end tests for Get Account Query tool.

This module validates querying account information through the LangChain agent,
Hedera client interaction, and Mirror Node queries.
"""

from typing import Any
import pytest
from hiero_sdk_python import PrivateKey, Hbar
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import (
    create_langchain_test_setup,
)
from test.utils.setup import (
    get_operator_client_for_tests,
    MIRROR_NODE_WAITING_TIME,
)


DEFAULT_EXECUTOR_BALANCE = Hbar(5, in_tinybars=False)


# ============================================================================
# SESSION FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """Operator client for the session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Operator wrapper for account operations."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION FIXTURES
# ============================================================================


@pytest.fixture
async def langchain_test_setup():
    """Initialize LangChain agent and toolkit using an operator client as context."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
def langchain_config():
    """LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def hedera_ops(operator_client):
    """Provide Hedera operations wrapper."""
    return HederaOperationsWrapper(operator_client)


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_get_account_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute account query through the agent and return parsed tool data."""
    query_result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(query_result)

    if not parsed_tool_calls:
        raise ValueError("The get_account_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_account_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_account_query_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_get_account_query_for_newly_created_account(
    agent_executor,
    hedera_ops,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching account info for a newly created account via agent."""
    private_key = PrivateKey.generate_ed25519()
    create_resp = await hedera_ops.create_account(
        CreateAccountParametersNormalised(
            key=private_key.public_key(),
            initial_balance=Hbar(1, in_tinybars=False),
        )
    )
    account_id = create_resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"Get account info for {account_id}"
    parsed_data = await execute_get_account_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert raw_data.get("error") is None
    assert f"Details for {account_id}" in human_message
    assert "Balance:" in human_message
    assert "Public Key:" in human_message
    assert "EVM address:" in human_message

    assert str(raw_data.get("account_id")) == str(account_id)
    assert raw_data.get("account", {}).get("balance") is not None
    assert raw_data.get("account", {}).get("account_public_key") is not None

    # Direct validation against a client call
    info = hedera_ops.get_account_info(str(account_id))
    assert str(info.account_id) == str(account_id)
    assert info.balance is not None
    assert info.key is not None
    assert info.key.to_string_der() == private_key.public_key().to_string_der()


@pytest.mark.asyncio
async def test_get_account_query_for_operator_account(
    agent_executor,
    operator_client,
    hedera_ops,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching account info for the operator account via agent."""
    operator_id = str(operator_client.operator_account_id)

    input_text = f"Query details for account {operator_id}"
    parsed_data = await execute_get_account_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    assert f"Details for {operator_id}" in human_message
    assert "Balance:" in human_message
    assert "Public Key:" in human_message
    assert "EVM address:" in human_message

    # Direct validation using raw data
    assert str(raw_data.get("account_id")) == operator_id

    # Direct validation against client call
    info = hedera_ops.get_account_info(operator_id)
    assert str(info.account_id) == operator_id


@pytest.mark.asyncio
async def test_get_account_query_for_nonexistent_account(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test that querying a nonexistent account fails gracefully."""
    fake_account_id = "0.0.999999999"

    input_text = f"Get account info for {fake_account_id}"
    parsed_data = await execute_get_account_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]

    # Check for a failure message in the human message or error field
    assert "Failed" in human_message
    assert fake_account_id in human_message
    assert parsed_data["raw"].get("error") is not None
