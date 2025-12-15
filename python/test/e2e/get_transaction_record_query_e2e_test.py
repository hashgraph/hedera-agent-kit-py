"""End-to-end tests for get transaction record tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey, TransactionId

from test.utils.usd_to_hbar_service import UsdToHbarService
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferHbarParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))


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
    return RunnableConfig(configurable={"thread_id": "get_transaction_record_e2e"})


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


@pytest.fixture
async def pre_created_transaction(
    executor_wrapper: HederaOperationsWrapper, executor_account, operator_client
) -> AsyncGenerator[TransactionId, None]:
    """Creates a simple HBAR transfer and yields its ID"""
    _, _, executor_client, _ = executor_account
    executor_account_id = executor_client.operator_account_id
    operator_account_id = operator_client.operator_account_id

    # Perform a transfer from executor to operator to generate a valid transaction
    # Using 1 tinybar.
    resp = await executor_wrapper.transfer_hbar(
        TransferHbarParametersNormalised(
            hbar_transfers={
                executor_account_id: -1,
                operator_account_id: 1,
            }
        )
    )

    assert resp.transaction_id is not None
    # Wait for the record to propagate to the mirror node before yielding
    await wait(MIRROR_NODE_WAITING_TIME)

    yield resp.transaction_id


async def execute_get_transaction_record(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute transaction record query through the agent and return parsed tool data."""
    result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(result)

    if not parsed_tool_calls:
        raise ValueError("The get_transaction_record_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_transaction_record_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_transaction_record_query_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================


# Helper to convert SDK transaction ID string to expected Mirror Node hyphenated format
def to_mirror_node_format(tx_id: TransactionId) -> str:
    """Converts SDK TransactionId (0.0.X@S.N) to Mirror Node format (0.0.X-S-N)."""
    return str(tx_id).replace("@", "-").replace(".", "-")


@pytest.mark.asyncio
async def test_fetch_record_sdk_at_style(
    agent_executor,
    pre_created_transaction: TransactionId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test fetching a record using the SDK-style transaction ID (e.g., 0.0.X@SSS.NNN)."""
    tx_id = pre_created_transaction

    input_text = f"Get the transaction record for transaction ID {str(tx_id)}"
    parsed_data = await execute_get_transaction_record(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    assert parsed_data.get("error") is None
    # Use the hyphenated format for assertion
    assert f"Transaction Details for " in human_message


@pytest.mark.asyncio
async def test_fetch_record_mirror_node_style(
    agent_executor,
    pre_created_transaction: TransactionId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test fetching a record using the Mirror Node-style transaction ID (e.g., 0.0.X-SSS-NNN)."""
    tx_id = pre_created_transaction

    input_text = f"Get the transaction record for transaction {tx_id}"
    parsed_data = await execute_get_transaction_record(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    assert parsed_data.get("error") is None
    # Use the hyphenated format for assertion
    assert f"Transaction Details for " in human_message


@pytest.mark.asyncio
async def test_handle_non_existent_transaction(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test handling a query for a non-existent transaction ID."""
    invalid_tx_id = "0.0.1-1756968265-043000618"  # Valid format, likely non-existent

    input_text = f"Get the transaction record for transaction {invalid_tx_id}"
    parsed_data = await execute_get_transaction_record(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error_message = parsed_data.get("error")

    # Check for error in either the error field or the human message content
    assert (error_message and "Failed to get transaction record" in error_message) or (
        "Failed to get transaction record" in human_message
        and "Not found" in human_message
    )


@pytest.mark.asyncio
async def test_handle_invalid_format_transaction(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test handling a query for an invalidly formatted transaction ID."""
    invalid_tx_id = "invalid-tx-id"

    input_text = f"Get the transaction record for transaction {invalid_tx_id}"
    parsed_data = await execute_get_transaction_record(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error_message = parsed_data.get("error")

    # Check for error in either the error field or the human message content
    assert (error_message and "Failed to get transaction record" in error_message) or (
        "Failed to get transaction record" in human_message
        and "Invalid transactionId format" in human_message
    )
