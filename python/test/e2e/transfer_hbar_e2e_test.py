from decimal import Decimal
from pprint import pprint
from typing import AsyncGenerator

import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

# Constants
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
DEFAULT_EXECUTOR_BALANCE = Hbar(10, in_tinybars=False)
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
            initial_balance=DEFAULT_RECIPIENT_BALANCE,
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_transfer(agent_executor, input_text: str, config: RunnableConfig):
    """Execute a transfer via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


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
    agent_executor, recipient_account, executor_wrapper, langchain_config
):
    """Test a basic HBAR transfer without memo."""
    amount = Decimal("0.1")
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))

    input_text = f"Transfer {amount} HBAR to {recipient_account}"
    await execute_transfer(agent_executor, input_text, langchain_config)

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert_balance_changed(balance_before, balance_after, amount)


@pytest.mark.asyncio
async def test_transfer_with_memo(
    agent_executor, recipient_account, executor_wrapper, langchain_config
):
    """Test HBAR transfer with a memo field."""
    amount = Decimal("0.05")
    memo = "Payment for services"
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))

    input_text = f'Transfer {amount} HBAR to {recipient_account} with memo "{memo}"'
    await execute_transfer(agent_executor, input_text, langchain_config)

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert_balance_changed(balance_before, balance_after, amount)


## This test happens to fail The LLM hallucinates some account after trying to crate an invalid transfer instead showing that to the user
# @pytest.mark.skip(
#     reason="Skipping this test temporarily due to LLM hallucinations. The LLM hallucinates some account after trying to crate an invalid transfer instead showing that to the user")
@pytest.mark.asyncio
async def test_invalid_params(
    agent_executor, executor_wrapper, recipient_account, langchain_config
):
    """Test that invalid parameters result in proper error handling."""
    amount = Decimal("0.05")
    input_text = f"Can you move {amount} HBARs to account with ID 0.0.0?"
    response = await execute_transfer(agent_executor, input_text, langchain_config)

    tool_response_obj: ExecutedTransactionToolResponse = extract_tool_response(
        response, "transfer_hbar_tool"
    )
    pprint(tool_response_obj)

    assert isinstance(tool_response_obj.error, str), "Error should be a string"
    assert tool_response_obj.error.strip() != "", "Error message should not be empty"
