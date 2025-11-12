"""End-to-end tests for get transaction record tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import asyncio
from typing import AsyncGenerator
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client, TransactionId, HbarTransfer
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised, TransferHbarParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client, MIRROR_NODE_WAITING_TIME
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(5, in_tinybars=False)


# ============================================================================
# SESSION-LEVEL FIXTURES
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
# FUNCTION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary executor account for tests.
    Yields:
        tuple: (account_id, private_key, client, wrapper)
    Teardown:
        Returns funds and deletes the account.
    """
    executor_key: PrivateKey = PrivateKey.generate_ecdsa()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=executor_key.public_key()
        )
    )
    executor_account_id = resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Wait for account creation to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Set up LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(
        configurable={"thread_id": "get_transaction_record_e2e"}
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


@pytest.fixture
async def pre_created_transaction(
    executor_wrapper: HederaOperationsWrapper, executor_account
):
    """Creates a simple HBAR self-transfer and yields its ID in SDK and Mirror Node formats."""
    _, _, executor_client, _ = executor_account
    executor_account_id = str(executor_client.operator_account_id)

    # Perform a self-transfer to generate a transaction
    # Using 1 tinybar.
    resp = await executor_wrapper.transfer_hbar(
        TransferHbarParametersNormalised(
            transfers=[
                HbarTransfer(
                    account_id=executor_account_id,
                    amount=Hbar(1, "tinybar"),
                    is_approval=False,
                ),
                HbarTransfer(
                    account_id=executor_account_id,
                    amount=Hbar(-1, "tinybar"),
                    is_approval=False,
                ),
            ]
        )
    )

    assert resp.transaction_id is not None

    # Get ID in SDK format (e.g., 0.0.X@SSS.NNN)
    tx_id_sdk_obj = TransactionId.from_string(resp.transaction_id)
    tx_id_sdk_style_str = str(tx_id_sdk_obj)  # This is the @ format

    # Get ID in Mirror Node format (e.g., 0.0.X-SSS-NNN)
    tx_id_mirror_style_str = _format_tx_id_to_mirror_node(tx_id_sdk_obj)

    # Wait for mirror node ingestion
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME)

    yield tx_id_sdk_style_str, tx_id_mirror_style_str


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_record_sdk_at_style(
    agent_executor, pre_created_transaction, langchain_config: RunnableConfig
):
    """Test fetching a record using the SDK-style transaction ID (e.g., 0.0.X@SSS.NNN)."""
    tx_id_sdk_style, tx_id_mirror_style = pre_created_transaction

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Get the transaction record for transaction ID {tx_id_sdk_style}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "get_transaction_record_query_tool")

    assert isinstance(observation, ToolResponse)
    assert observation.error is None
    # The normalizer converts the @ format to the - format, which is used in the query and post_process
    assert (
        f"Transaction Details for {tx_id_mirror_style}" in observation.human_message
    )


@pytest.mark.asyncio
async def test_fetch_record_mirror_node_style(
    agent_executor, pre_created_transaction, langchain_config: RunnableConfig
):
    """Test fetching a record using the Mirror Node-style transaction ID (e.g., 0.0.X-SSS-NNN)."""
    _, tx_id_mirror_style = pre_created_transaction

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Get the transaction record for transaction {tx_id_mirror_style}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "get_transaction_record_query_tool")

    assert isinstance(observation, ToolResponse)
    assert observation.error is None
    assert f"Transaction Details for {tx_id_mirror_style}" in observation.human_message


@pytest.mark.asyncio
async def test_handle_non_existent_transaction(
    agent_executor, langchain_config: RunnableConfig
):
    """Test handling a query for a non-existent transaction ID."""
    invalid_tx_id = "0.0.1-1756968265-043000618"  # Valid format, likely non-existent

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Get the transaction record for transaction {invalid_tx_id}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "get_transaction_record_query_tool")

    assert isinstance(observation, ToolResponse)
    assert observation.error is not None
    assert "Failed to get transaction record" in observation.error
    assert "Not Found" in observation.error


@pytest.mark.asyncio
async def test_handle_invalid_format_transaction(
    agent_executor, langchain_config: RunnableConfig
):
    """Test handling a query for an invalidly formatted transaction ID."""
    invalid_tx_id = "invalid-tx-id"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Get the transaction record for transaction {invalid_tx_id}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "get_transaction_record_query_tool")

    assert isinstance(observation, ToolResponse)
    assert observation.error is not None
    assert "Failed to get transaction record" in observation.error
    assert "Invalid transactionId format" in observation.error