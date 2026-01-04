"""End-to-end tests for creation account tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey, PublicKey, AccountId, Client

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_custom_client
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))


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
    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key)
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
        "toolkit": setup.toolkit,
        "response_parser": setup.response_parser,
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
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "create_account_e2e"})


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
