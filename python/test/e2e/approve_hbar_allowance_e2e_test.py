"""End-to-end tests for approve HBAR allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution and verification of the allowance usage.
"""

from decimal import Decimal
from pprint import pprint
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    HbarUnit,
    PrivateKey,
    AccountId,
    Client,
    TransferTransaction,
)
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
from test.utils.verification import verify_hbar_balance_change

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(15)
DEFAULT_SPENDER_BALANCE = Hbar(5)
TOOL_NAME = "approve_hbar_allowance_tool"


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
    """Create a temporary executor account (the Owner) for tests.

    Yields:
        tuple: (account_id, private_key, client, wrapper)
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
    executor_client.close()


@pytest.fixture
async def spender_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary spender account for tests.

    Yields:
        tuple: (account_id, private_key, client, wrapper)
    """
    spender_key_pair: PrivateKey = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_SPENDER_BALANCE,
            key=spender_key_pair.public_key(),
        )
    )

    spender_account_id: AccountId = spender_resp.account_id
    spender_client: Client = get_custom_client(spender_account_id, spender_key_pair)
    spender_wrapper_instance: HederaOperationsWrapper = HederaOperationsWrapper(
        spender_client
    )

    yield spender_account_id, spender_key_pair, spender_client, spender_wrapper_instance

    await return_hbars_and_delete_account(
        spender_wrapper_instance,
        spender_account_id,
        operator_client.operator_account_id,
    )
    spender_client.close()


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Set up LangChain agent and toolkit with the executor (Owner) account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
) -> dict[str, Any]:
    """Execute the agent invocation and return the result."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def validate_tool_use(
    agent_result: dict[str, Any], response_parser: ResponseParserService, tool_name: str
):
    """Validates that the specific tool was called successfully."""
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")

    # We filter specifically for our tool in case other chain-of-thought tools were used
    target_tool_calls = [
        call for call in parsed_tool_calls if call.toolName == tool_name
    ]

    if not target_tool_calls:
        raise ValueError(f"Tool {tool_name} was not among the called tools.")

    tool_call = target_tool_calls[0]

    if tool_call.parsedData["raw"]["status"] != "SUCCESS":
        raise ValueError(
            f"Tool execution failed: {tool_call.parsedData['humanMessage']}"
        )


async def spend_via_allowance(
    owner_id: AccountId,
    spender_id: AccountId,
    amount_hbar: float,
    spender_client: Client,
):
    """
    Helper to execute a TransferTransaction using the approved allowance.
    This simulates the Spender taking action.
    """
    tinybars = Hbar(amount_hbar, HbarUnit.HBAR).to_tinybars()
    tx = (
        TransferTransaction()
        .add_approved_hbar_transfer(AccountId.from_string(str(owner_id)), -tinybars)
        .add_hbar_transfer(AccountId.from_string(str(spender_id)), tinybars)
    )

    tx.execute(spender_client)


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_approve_hbar_allowance_and_allow_spender_to_use_part_of_it(
    agent_executor,
    executor_account,
    spender_account,
    operator_client,
    langchain_config,
    response_parser,
):
    """Test authenticating an allowance and subsequently spending part of it."""
    executor_id, _, _, _ = executor_account
    spender_id, _, spender_client, spender_wrapper = spender_account

    allowance_amount = 1.5
    spend_amount = 1.01
    memo = "E2E approve allowance memo"

    balance_before = spender_wrapper.get_account_hbar_balance(str(spender_id))

    # 1. Agent approves allowance
    input_text = (
        f'Approve {allowance_amount} HBAR allowance to {spender_id} with memo "{memo}"'
    )
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    pprint(result)

    validate_tool_use(result, response_parser, TOOL_NAME)

    # Wait for Mirror Node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Spender utilizes the allowance
    await spend_via_allowance(
        executor_id,
        spender_id,
        spend_amount,
        spender_client,
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify Spender's balance increased
    await verify_hbar_balance_change(
        str(spender_id),
        Decimal(balance_before),
        Decimal(spend_amount),
        spender_wrapper,
    )


@pytest.mark.asyncio
async def test_should_approve_and_spend_very_small_amount_via_allowance(
    agent_executor,
    executor_account,
    spender_account,
    langchain_config,
    response_parser,
):
    """Test authenticating a micro-allowance and spending it."""
    executor_id, _, _, _ = executor_account
    spender_id, _, spender_client, spender_wrapper = spender_account

    allowance_amount = 0.11
    spend_amount = 0.1

    balance_before = spender_wrapper.get_account_hbar_balance(str(spender_id))

    # 1. Agent approves allowance
    input_text = f"Approve {allowance_amount} HBAR allowance to {spender_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    validate_tool_use(result, response_parser, TOOL_NAME)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Spender utilizes the allowance
    await spend_via_allowance(
        executor_id,
        spender_id,
        spend_amount,
        spender_client,
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify Spender's balance increased
    await verify_hbar_balance_change(
        str(spender_id),
        Decimal(balance_before),
        Decimal(spend_amount),
        spender_wrapper,
    )
