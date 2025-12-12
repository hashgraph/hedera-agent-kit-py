"""End-to-end tests for submit topic message tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from decimal import Decimal
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit.shared.hedera_utils import to_tinybars
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account


# Constants
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
DEFAULT_RECIPIENT_BALANCE = 0


# ============================================================================
# SESSION-LEVEL FIXTURES (Run once per test session)
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """Initialize operator client once per test session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Create a wrapper for operator client operations."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION-LEVEL FIXTURES (Run once per test function)
# ============================================================================


@pytest.fixture
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """
    Create a temporary executor account for tests.

    Yields:
        tuple: (account_id, private_key, client, wrapper)

    Teardown:
        Returns funds and deletes the account.
    """
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper_instance = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key_pair, executor_client, executor_wrapper_instance

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
async def recipient_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[str, None]:
    """
    Create a temporary recipient account for tests.

    Yields:
        str: The recipient account ID

    Teardown:
        Returns funds and deletes the account.
    """
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(DEFAULT_RECIPIENT_BALANCE),
            key=operator_client.operator_private_key.public_key(),
        )
    )
    account_id = recipient_resp.account_id

    yield str(account_id)

    await return_hbars_and_delete_account(
        operator_wrapper, account_id, operator_client.operator_account_id
    )


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Setup LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def toolkit(langchain_test_setup):
    """Provide the LangChain toolkit."""
    return langchain_test_setup.toolkit


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_transfer(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute a transfer via the agent and return the parsed tool data."""
    result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(result)

    if not parsed_tool_calls:
        raise ValueError("The transfer_hbar_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != TRANSFER_HBAR_TOOL:
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of {TRANSFER_HBAR_TOOL}"
        )

    return tool_call.parsedData


def assert_balance_changed(
    balance_before: int, balance_after: int, expected_amount: Decimal
):
    """Assert that the balance changed by the expected amount."""
    actual_change = balance_after - balance_before
    expected_change = to_tinybars(expected_amount)
    assert (
        actual_change == expected_change
    ), f"Balance change mismatch: expected {expected_change}, got {actual_change}"


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_simple_transfer(
    agent_executor,
    recipient_account,
    executor_wrapper,
    langchain_config,
    response_parser,
):
    """Test a basic HBAR transfer without memo."""
    amount = Decimal("0.1")
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))

    input_text = f"Transfer {amount} HBAR to {recipient_account}"
    parsed_data = await execute_transfer(
        agent_executor, input_text, langchain_config, response_parser
    )

    assert parsed_data.get("error") is None
    assert "hbar successfully transferred" in parsed_data["humanMessage"].lower()

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert_balance_changed(balance_before, balance_after, amount)


@pytest.mark.asyncio
async def test_transfer_with_memo(
    agent_executor,
    recipient_account,
    executor_wrapper,
    langchain_config,
    response_parser,
):
    """Test HBAR transfer with a memo field."""
    amount = Decimal("0.05")
    memo = "Payment for services"
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))

    input_text = f'Transfer {amount} HBAR to {recipient_account} with memo "{memo}"'
    parsed_data = await execute_transfer(
        agent_executor, input_text, langchain_config, response_parser
    )

    assert parsed_data.get("error") is None
    assert "hbar successfully transferred" in parsed_data["humanMessage"].lower()

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert_balance_changed(balance_before, balance_after, amount)


# @pytest.mark.skip(
#     reason="Skipping this test temporarily due to LLM hallucinations. The LLM hallucinates some account after trying to crate an invalid transfer instead showing that to the user")
@pytest.mark.asyncio
async def test_invalid_params(
    agent_executor,
    executor_wrapper,
    recipient_account,
    langchain_config,
    response_parser,
):
    """Test that invalid parameters result in proper error handling."""
    amount = Decimal("0.05")
    # Using an intentionally invalid account ID (0.0.0)
    input_text = f"Can you move {amount} HBARs to account with ID 0.0.0?"

    # We don't assert execution success, only that the agent attempts to call the tool
    parsed_data = await execute_transfer(
        agent_executor, input_text, langchain_config, response_parser
    )

    # If the tool call itself failed due to invalid input (which is expected here),
    # the parsed_data should contain an error field.
    error_message = parsed_data["raw"].get("error")

    assert isinstance(error_message, str), "Error should be a string"
    assert error_message.strip() != "", "Error message should not be empty"
    # Checking for common Hedera SDK error message components related to invalid account ID
    assert any(
        err in error_message
        for err in [
            "INVALID_ACCOUNT_ID",
            "Account ID",
            "0.0.0",
        ]
    )
