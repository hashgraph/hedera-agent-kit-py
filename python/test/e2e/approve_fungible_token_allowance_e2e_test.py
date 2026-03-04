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
from test.utils.setup.langchain_test_config import BALANCE_TIERS
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
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))
DEFAULT_SPENDER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))
TOOL_NAME = "approve_fungible_token_allowance_tool"


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Owner) and test token (Module Scoped)."""
    # 1. Create Executor (Owner)
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Create Test Fungible Token
    treasury_public_key = executor_key_pair.public_key()
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
        treasury_account_id=executor_account_id,
    )
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    token_resp = await executor_wrapper.create_fungible_token(create_params)
    token_id = token_resp.token_id

    # Wait for propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Setup LangChain
    setup = await create_langchain_test_setup(custom_client=executor_client)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key_pair": executor_key_pair,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "token_id": token_id,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
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
        res["executor_key_pair"],
        res["executor_client"],
        res["executor_wrapper"],
    )


@pytest.fixture(scope="module")
def test_token(setup_module_resources):
    return setup_module_resources["token_id"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "approve_fungible_allowance_e2e"})


# Function-scoped Spender to ensure isolation (association state etc.)
@pytest.fixture
async def spender_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary spender account for tests."""
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
