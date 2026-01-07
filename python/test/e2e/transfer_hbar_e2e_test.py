"""End-to-end tests for submit topic message tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from decimal import Decimal
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
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
from test.utils.setup import get_custom_client
from test.utils.teardown import return_hbars_and_delete_account


# Constants
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))
DEFAULT_RECIPIENT_BALANCE = 0


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
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

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=executor_client)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
        "toolkit": setup.toolkit,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture(scope="module")
def executor_account(setup_module_resources):
    res = setup_module_resources
    # Accessor matching original yield: (id, key, client, wrapper)
    return (
        res["executor_account_id"],
        res["executor_key"],
        res["executor_client"],
        res["executor_wrapper"],
    )


@pytest.fixture(scope="module")
def executor_wrapper(setup_module_resources):
    return setup_module_resources["executor_wrapper"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def toolkit(setup_module_resources):
    return setup_module_resources["toolkit"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
async def recipient_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[str, None]:
    """
    Create a temporary recipient account for tests (Function Scoped).

    Yields:
        str: The recipient account ID
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
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "transfer_hbar_e2e"})


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
    # Using an intentionally invalid account ID that looks plausible but likely doesn't exist
    input_text = f"Can you move {amount} HBARs to account with ID 0.0.999999999?"

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
            "0.0.999999999",
        ]
    )
