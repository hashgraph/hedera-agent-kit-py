"""End-to-end tests for creation account tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey, PublicKey, AccountId, Client
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(10, in_tinybars=False)


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
    executor_key_pair: PrivateKey = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper_instance: HederaOperationsWrapper = HederaOperationsWrapper(
        executor_client
    )

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
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


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


def extract_account_id(
    agent_result: dict[str, Any], response_parser: ResponseParserService, tool_name: str
) -> str:
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")
    else:
        if len(parsed_tool_calls) > 1:
            raise ValueError("Multiple tool calls were found")
        if parsed_tool_calls[0].toolName != tool_name:
            raise ValueError(
                f"Incorrect tool name. Called {parsed_tool_calls[0].toolName} instead of {tool_name}"
            )
    return parsed_tool_calls[0].parsedData["raw"]["account_id"]


async def execute_create_account(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute account creation via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_account_with_default_operator_public_key(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    operator_wrapper: HederaOperationsWrapper,
    operator_client: Client,
    langchain_config: RunnableConfig,
    executor_account,
    response_parser,
):
    """Test creating an account with a default operator public key."""
    _, _, executor_client, _ = executor_account
    public_key: PublicKey = executor_client.operator_private_key.public_key()

    input_text = "Create a new Hedera account"

    result = await execute_create_account(agent_executor, input_text, langchain_config)
    new_account_id = extract_account_id(result, response_parser, "create_account_tool")

    info = executor_wrapper.get_account_info(new_account_id)
    assert info.key.to_string_raw() == public_key.to_string_raw()

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        AccountId.from_string(new_account_id),
        operator_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_create_account_with_initial_balance_and_memo(
    agent_executor,
    executor_wrapper,
    operator_wrapper,
    operator_client,
    langchain_config,
    response_parser,
):
    """Test creating an account with initial balance and memo."""
    input_text = (
        'Create an account with initial balance 0.05 HBAR and memo "E2E test account"'
    )

    result = await execute_create_account(agent_executor, input_text, langchain_config)
    new_account_id = extract_account_id(result, response_parser, "create_account_tool")

    info = executor_wrapper.get_account_info(new_account_id)
    assert info.account_memo == "E2E test account"

    balance = executor_wrapper.get_account_hbar_balance(new_account_id)
    assert balance >= int(0.05 * 1e8)

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        AccountId.from_string(new_account_id),
        operator_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_create_account_with_explicit_public_key(
    agent_executor,
    executor_wrapper,
    operator_wrapper,
    operator_client,
    langchain_config,
    response_parser,
):
    """Test creating an account with an explicit public key."""
    public_key = PrivateKey.generate_ed25519().public_key()
    input_text = f"Create a new account with public key {public_key.to_string_der()}"

    result = await execute_create_account(agent_executor, input_text, langchain_config)
    new_account_id = extract_account_id(result, response_parser, "create_account_tool")

    info = executor_wrapper.get_account_info(new_account_id)
    assert info.key.to_string_der() == public_key.to_string_der()


@pytest.mark.asyncio
async def test_schedule_create_account_transaction(
    agent_executor, langchain_config, response_parser
):
    """Test scheduling a creation account transaction with an explicit public key."""
    public_key = PrivateKey.generate_ed25519().public_key()
    input_text = f"Schedule creating a new Hedera account using public key {public_key.to_string_der()}"

    result = await execute_create_account(agent_executor, input_text, langchain_config)
    tool_call = response_parser.parse_new_tool_messages(result)[0]

    # Validate response structure
    assert tool_call.parsedData["raw"] is not None
    assert tool_call.parsedData["raw"]["transaction_id"] is not None
    assert tool_call.parsedData["raw"]["schedule_id"] is not None
    assert (
        "Scheduled transaction created successfully"
        in tool_call.parsedData["humanMessage"]
    )

    # We don't expect account_id yet since it's not executed immediately
    assert tool_call.parsedData["raw"]["account_id"] is None


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_account_with_very_small_initial_balance(
    agent_executor,
    executor_wrapper,
    operator_wrapper,
    operator_client,
    langchain_config,
    response_parser,
):
    """Test creating an account with very small initial balance."""
    input_text = "Create an account with initial balance 0.0001 HBAR"

    result = await execute_create_account(agent_executor, input_text, langchain_config)
    new_account_id = extract_account_id(result, response_parser, "create_account_tool")

    balance = executor_wrapper.get_account_hbar_balance(new_account_id)
    assert balance >= int(0.0001 * 1e8)

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        AccountId.from_string(new_account_id),
        operator_client.operator_account_id,
    )
