"""End-to-end tests for delete Token allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.

The flow tested is:
1. Owner creates a Token.
2. Owner grants an allowance to a Spender for that Token.
3. Agent (acting as Owner) revokes/deletes that allowance via natural language.
"""

import asyncio
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
    TokenId,
    TokenAllowance,
    SupplyType,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    ApproveTokenAllowanceParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_custom_client
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))
MIRROR_NODE_WAITING_TIME_SEC = 10


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_module_resources(operator_client, operator_wrapper):
    """
    Module-scoped setup that creates the Executor account, Fungible Token,
    and LangChain agent ONCE for the entire test module.
    """
    # 1. Create Executor Account
    executor_key_pair: PrivateKey = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper_instance = HederaOperationsWrapper(executor_client)

    # 2. Create Fungible Token
    ft_params = TokenParams(
        token_name="E2EDeleteToken",
        token_symbol="DEL",
        memo="Token for E2E allowance delete tests",
        initial_supply=1000,
        decimals=2,
        max_supply=10000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
        auto_renew_account_id=executor_account_id,
    )

    token_keys = TokenKeys(
        supply_key=executor_key_pair.public_key(),
        admin_key=executor_key_pair.public_key(),
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=token_keys
    )

    token_resp = await executor_wrapper_instance.create_fungible_token(create_params)
    token_id = token_resp.token_id

    # Wait for mirror node ingestion
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    # 3. Setup LangChain
    langchain_setup = await create_langchain_test_setup(custom_client=executor_client)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key_pair": executor_key_pair,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper_instance,
        "token_id": token_id,
        "langchain_setup": langchain_setup,
        "agent_executor": langchain_setup.agent,
        "response_parser": langchain_setup.response_parser,
    }

    yield resources

    # Teardown
    langchain_setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
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
def fungible_token(setup_module_resources):
    return setup_module_resources["token_id"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


# ============================================================================
# FUNCTION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture
async def spender_account(
    executor_account, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a separate spender account (Function Scoped)."""
    _, _, _, executor_wrapper = executor_account
    spender_key: PrivateKey = PrivateKey.generate_ed25519()

    # Executor creates spender funded with a small balance
    spender_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])),
            key=spender_key.public_key(),
        )
    )

    spender_id = spender_resp.account_id
    spender_client = get_custom_client(spender_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    yield spender_id, spender_key, spender_client, spender_wrapper

    # Cleanup
    await return_hbars_and_delete_account(
        spender_wrapper,
        spender_id,
        operator_client.operator_account_id,
    )
    spender_client.close()


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "delete_token_allowance_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def approve_token_allowance(
    owner_wrapper: HederaOperationsWrapper,
    owner_id: AccountId,
    spender_id: AccountId,
    token_id: TokenId,
    amount: int,
):
    """Helper to approve Token allowance from Owner to Spender."""
    allowance = TokenAllowance(
        token_id=token_id,
        owner_account_id=owner_id,
        spender_account_id=spender_id,
        amount=amount,
    )
    approve_params = ApproveTokenAllowanceParametersNormalised(
        token_allowances=[allowance]
    )
    await owner_wrapper.approve_token_allowance(approve_params)
    # Wait for mirror node to index allowance
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute a request via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    """Helper to extract tool data from response."""
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    if not tool_calls:
        return None
    return tool_calls[0]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_delete_existing_token_allowance(
    agent_executor,
    executor_account,
    fungible_token,
    spender_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test deleting an existing token allowance via natural language."""
    # 1. Setup
    owner_id, _, _, executor_wrapper = executor_account
    spender_id, _, _, _ = spender_account
    token_id = fungible_token

    # Grant allowance first
    await approve_token_allowance(executor_wrapper, owner_id, spender_id, token_id, 10)

    # 2. Execute Deletion via Agent
    input_text = (
        f"Delete token allowance given from {owner_id} "
        f"to account {spender_id} for token {token_id}"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Validate Response
    assert tool_call is not None
    assert (
        "Token allowance(s) deleted successfully"
        in tool_call.parsedData["humanMessage"]
    )
    assert tool_call.parsedData["raw"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_handle_deleting_non_existent_token_allowance(
    agent_executor,
    executor_account,
    fungible_token,
    spender_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test deleting a non-existent token allowance (should succeed gracefully)."""
    # 1. Setup (No prior allowance granted)
    owner_id, _, _, _ = executor_account
    spender_id, _, _, _ = spender_account
    token_id = fungible_token

    # 2. Execute Deletion via Agent
    input_text = (
        f"Delete token allowance given from {owner_id} "
        f"to account {spender_id} for token {token_id}"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Validate Response
    # Setting allowance to 0 for an account with no allowance is a valid transaction
    assert tool_call is not None
    assert (
        "Token allowance(s) deleted successfully"
        in tool_call.parsedData["humanMessage"]
    )
    assert tool_call.parsedData["raw"]["status"] == "SUCCESS"
