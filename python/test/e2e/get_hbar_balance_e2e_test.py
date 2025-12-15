"""End-to-end tests for Get HBAR Balance tool.

This module provides full E2E testing from simulated user input through the
LangChain agent, Hedera client interaction, to on-chain balance queries.
"""

from typing import AsyncGenerator, Any
import pytest

from hiero_sdk_python import PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1))

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
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary executor account used as agent operator."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    yield executor_account_id, executor_key, executor_client, executor_wrapper, operator_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Initialize LangChain agent and toolkit using executor client as operator."""
    _, _, executor_client, _, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
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
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_get_hbar_balance(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute balance query through the agent and return parsed tool data."""
    result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(result)

    if not parsed_tool_calls:
        raise ValueError("The get_hbar_balance_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_hbar_balance_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_hbar_balance_query_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
async def test_get_hbar_balance_for_specific_account_nonzero(
    agent_executor,
    executor_account,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching HBAR balance for a specific account with nonzero balance."""
    _, _, _, executor_wrapper, _ = executor_account

    resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.5)),
            key=executor_wrapper.client.operator_private_key.public_key(),
        )
    )
    account_id = resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"What is the HBAR balance of {account_id}?"
    parsed_data = await execute_get_hbar_balance(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]

    assert str(account_id) in human_message
    assert parsed_data.get("error") is None

    await return_hbars_and_delete_account(
        executor_wrapper,
        account_id,
        executor_wrapper.client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_get_hbar_balance_for_specific_account_zero_balance(
    agent_executor,
    executor_account,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching HBAR balance for an account with zero HBAR."""
    _, _, executor_client, executor_wrapper, _ = executor_account

    resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.1)),
            key=executor_wrapper.client.operator_private_key.public_key(),
        )
    )
    account_id = resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"What is the HBAR balance of {account_id}?"
    result = await execute_get_hbar_balance(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = result["humanMessage"]
    raw_data = result["raw"]

    assert str(account_id) in human_message
    assert "0" in human_message
    assert raw_data.get("balance") == "0"
    assert result.get("error") is None

    await return_hbars_and_delete_account(
        executor_wrapper,
        account_id,
        executor_wrapper.client.operator_account_id,
    )
