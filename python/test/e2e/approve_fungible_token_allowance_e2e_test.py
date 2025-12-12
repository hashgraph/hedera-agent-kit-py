"""End-to-end tests for approve fungible token allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution and verification of the allowance usage.
"""

from pprint import pprint
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
    TransferTransaction,
    SupplyType,
    TokenId,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
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
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))
DEFAULT_SPENDER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
TOOL_NAME = "approve_fungible_token_allowance_tool"


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
async def test_token(executor_account):
    """Create a test fungible token owned by executor."""
    executor_id, executor_key, executor_client, executor_wrapper = executor_account

    treasury_public_key = executor_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    ft_params = TokenParams(
        token_name="E2EAllowToken",
        token_symbol="E2EALW",
        initial_supply=50000,
        decimals=2,
        max_supply=100000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_id,
    )
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    token_resp = await executor_wrapper.create_fungible_token(create_params)

    await wait(MIRROR_NODE_WAITING_TIME)

    return token_resp.token_id


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

    # Check if raw status exists and is SUCCESS
    if tool_call.parsedData.get("error"):
        raise ValueError(
            f"Tool execution failed with error: {tool_call.parsedData['error']}"
        )

    raw_data = tool_call.parsedData.get("raw")
    if not raw_data or raw_data.get("status") != "SUCCESS":
        raise ValueError(
            f"Tool execution failed: {tool_call.parsedData.get('humanMessage', 'Unknown error')}"
        )


async def spend_token_via_allowance(
    owner_id: AccountId,
    spender_id: AccountId,
    token_id: str,
    amount: int,
    spender_client: Client,
):
    """
    Helper to execute a TransferTransaction using the approved token allowance.
    This simulates the Spender taking action.
    """
    print(
        f"spending {amount} tokens from {owner_id} to {spender_id}. The token id is {token_id}."
    )
    tx = (
        TransferTransaction()
        .add_approved_token_transfer(TokenId.from_string(token_id), owner_id, -amount)
        .add_token_transfer(TokenId.from_string(token_id), spender_id, amount)
    )

    # Execute and wait for a receipt to ensure it passed
    resp = tx.execute(spender_client)
    pprint(resp)


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_approve_token_allowance_and_allow_spender_to_use_it(
    agent_executor,
    executor_account,
    spender_account,
    test_token,
    langchain_config,
    response_parser,
):
    """Test authenticating a token allowance and subsequently spending it."""
    executor_id, _, _, executor_wrapper = executor_account
    spender_id, _, spender_client, spender_wrapper = spender_account
    token_id_str = str(test_token)

    allowance_amount = 50
    spend_amount = 25
    memo = "E2E token allow memo"

    # 1. Agent approves allowance
    input_text = f'Approve allowance of {allowance_amount} tokens for token {token_id_str} to {spender_id} with memo "{memo}"'
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    pprint(result)

    validate_tool_use(result, response_parser, TOOL_NAME)

    # Wait for Mirror Node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Spender utilizes the allowance
    # Note: Amount is in base units because we created token with 2 decimals
    # The tool takes amount in display units (e.g. 50.00) and converts to base units (5000).
    # The spend_token_via_allowance helper uses add_approved_token_transfer which takes base units (int).
    # So if I approve 50 (display), it becomes 5000 (base).
    # If I want to spend 25 (display), I should pass 2500 (base).

    spend_amount_base = int(spend_amount * 100)

    # Associate spender to token first (Spender pays for association)
    await spender_wrapper.associate_token(
        {"accountId": str(spender_id), "tokenId": token_id_str}
    )

    # Wait for association
    await wait(MIRROR_NODE_WAITING_TIME)

    await spend_token_via_allowance(
        executor_id,
        spender_id,
        token_id_str,
        spend_amount_base,
        spender_client,
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify Spender's balance increased
    balances = spender_wrapper.get_account_balances(str(spender_id))

    pprint(balances)

    # Handle potential dictionary key variations
    token_balance = 0
    if balances.token_balances:
        # Check TokenId object
        token_balance = balances.token_balances.get(test_token, 0)

    assert token_balance == spend_amount_base
