"""End-to-end tests for transfer fungible token with allowance tool.

This module tests the full lifecycle of a token allowance transfer:
1. Setup: Owner (Executor), Spender (Agent), and Receiver accounts.
2. Minting: Owner creates a token.
3. Allowance: Owner grants allowance to Spender.
4. Execution: Agent (acting as Spender) executes transfers via LLM.


"""

from typing import AsyncGenerator, Any, Dict

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    TokenAllowance,
    SupplyType,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    ApproveTokenAllowanceParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================

DEFAULT_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
OWNER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def allowance_test_setup(
    operator_wrapper, operator_client
) -> AsyncGenerator[Dict[str, Any], None]:
    """Sets up the complete environment for allowance tests (Module Scoped).

    Creates:
    - Executor (Token Owner/Treasury)
    - Spender (The Agent)
    - Receiver
    - A Fungible Token
    - An Allowance grant from Executor to Spender

    Yields:
        Dict containing all accounts, clients, token ID, and the initialized Agent.
    """
    # 1. Create Executor Account (Token Owner)
    executor_key = PrivateKey.generate_ed25519()
    executor_account = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=OWNER_BALANCE
        )
    )
    executor_id = executor_account.account_id
    executor_client = get_custom_client(executor_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Create Spender Account (The Agent)
    spender_key = PrivateKey.generate_ed25519()
    spender_account = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=spender_key.public_key(), initial_balance=DEFAULT_BALANCE
        )
    )
    spender_id = spender_account.account_id
    spender_client = get_custom_client(spender_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    # 3. Create Receiver Account
    receiver_key = PrivateKey.generate_ed25519()
    receiver_account = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=receiver_key.public_key(), initial_balance=DEFAULT_BALANCE
        )
    )
    receiver_id = receiver_account.account_id
    receiver_client = get_custom_client(receiver_id, receiver_key)
    receiver_wrapper = HederaOperationsWrapper(receiver_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Create Fungible Token (Treasury = Executor)
    ft_params = TokenParams(
        token_name="E2EAllowanceToken",
        token_symbol="E2EAT",
        memo="Token for E2E allowance transfer tests",
        initial_supply=1000,
        decimals=0,
        max_supply=10000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_id,
        auto_renew_account_id=executor_id,
    )

    token_keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )

    create_token_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=token_keys
    )

    token_create_resp = await executor_wrapper.create_fungible_token(
        create_token_params
    )
    token_id = token_create_resp.token_id

    # 5. Associate Token to Spender and Receiver
    await spender_wrapper.associate_token(
        {"accountId": str(spender_id), "tokenId": str(token_id)}
    )
    await receiver_wrapper.associate_token(
        {"accountId": str(receiver_id), "tokenId": str(token_id)}
    )

    # 6. Approve Allowance (Executor approves Spender)
    # Total allowance needed for tests: 50 + 100 + 50 + 300 = 500.
    # Note: Tests share state, so we need enough allowance for all tests combined.
    await executor_wrapper.approve_token_allowance(
        ApproveTokenAllowanceParametersNormalised(
            token_allowances=[
                TokenAllowance(
                    token_id=token_id,
                    owner_account_id=executor_id,
                    spender_account_id=spender_id,
                    amount=500,
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 7. Setup LangChain Agent using the SPENDER client
    # The agent acts as the Spender utilizing the allowance
    lc_setup = await create_langchain_test_setup(custom_client=spender_client)

    yield {
        "agent": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "executor_id": executor_id,
        "spender_id": spender_id,
        "receiver_id": receiver_id,
        "token_id": token_id,
        "spender_wrapper": spender_wrapper,
        "receiver_wrapper": receiver_wrapper,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": lc_setup,
        "clients_to_close": [executor_client, spender_client, receiver_client],
    }

    # Teardown
    lc_setup.cleanup()

    # cleanup accounts in reverse order of creation/dependency
    if spender_id:
        await return_hbars_and_delete_account(spender_wrapper, spender_id, executor_id)
    spender_client.close()

    if receiver_id:
        await return_hbars_and_delete_account(
            receiver_wrapper, receiver_id, executor_id
        )
    receiver_client.close()

    if executor_id:
        await return_hbars_and_delete_account(
            executor_wrapper, executor_id, operator_client.operator_account_id
        )
    executor_client.close()


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "allowance_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute a request via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def validate_success_response(
    result: dict, response_parser: ResponseParserService
) -> Any:
    """Parses tool messages and validates success status."""
    parsed_response = response_parser.parse_new_tool_messages(result)
    assert parsed_response, "No tool calls found in response"

    tool_data = parsed_response[0].parsedData
    assert (
        "Fungible tokens successfully transferred with allowance"
        in tool_data["humanMessage"]
    )
    assert tool_data["raw"]["status"] == "SUCCESS"

    return tool_data


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_agent_transfer_to_self_with_allowance(
    allowance_test_setup: Dict[str, Any], langchain_config: RunnableConfig
):
    """Test using allowance to transfer tokens to self (spender)."""
    agent = allowance_test_setup["agent"]
    response_parser = allowance_test_setup["response_parser"]

    executor_id = allowance_test_setup["executor_id"]
    spender_id = allowance_test_setup["spender_id"]
    token_id = allowance_test_setup["token_id"]
    spender_wrapper = allowance_test_setup["spender_wrapper"]

    input_text = (
        f"Use allowance from account {executor_id} to send 50 {token_id} "
        f"to account {spender_id}"
    )

    result = await execute_agent_request(agent, input_text, langchain_config)
    print(result)

    validate_success_response(result, response_parser)

    await wait(MIRROR_NODE_WAITING_TIME)

    spender_balance = await spender_wrapper.get_account_token_balance_from_mirrornode(
        str(spender_id), str(token_id)
    )
    assert spender_balance["balance"] == 50


@pytest.mark.asyncio
async def test_agent_transfer_to_multiple_recipients(
    allowance_test_setup: Dict[str, Any], langchain_config: RunnableConfig
):
    """Test using allowance to transfer to multiple recipients."""
    agent = allowance_test_setup["agent"]
    response_parser = allowance_test_setup["response_parser"]

    executor_id = allowance_test_setup["executor_id"]
    spender_id = allowance_test_setup["spender_id"]
    receiver_id = allowance_test_setup["receiver_id"]
    token_id = allowance_test_setup["token_id"]

    spender_wrapper = allowance_test_setup["spender_wrapper"]
    receiver_wrapper = allowance_test_setup["receiver_wrapper"]

    input_text = (
        f"Use allowance from account {executor_id} to send 30 {token_id} "
        f"to account {spender_id} and 70 {token_id} to account {receiver_id}"
    )

    result = await execute_agent_request(agent, input_text, langchain_config)

    validate_success_response(result, response_parser)

    await wait(MIRROR_NODE_WAITING_TIME)

    spender_balance = await spender_wrapper.get_account_token_balance_from_mirrornode(
        str(spender_id), str(token_id)
    )
    receiver_balance = await receiver_wrapper.get_account_token_balance_from_mirrornode(
        str(receiver_id), str(token_id)
    )

    # Previous test transferred 50 to spender, this test adds 30 more = 80 minimum
    # Receiver gets 70 in this test
    # Note: Using >= because pytest retries can accumulate additional transfers
    assert spender_balance["balance"] >= 80
    assert receiver_balance["balance"] >= 70


@pytest.mark.asyncio
async def test_agent_schedule_transfer_with_allowance(
    allowance_test_setup: Dict[str, Any], langchain_config: RunnableConfig
):
    """Test scheduling an allowance transfer."""
    agent = allowance_test_setup["agent"]
    response_parser = allowance_test_setup["response_parser"]

    executor_id = allowance_test_setup["executor_id"]
    spender_id = allowance_test_setup["spender_id"]
    token_id = allowance_test_setup["token_id"]

    input_text = (
        f"Use allowance from account {executor_id} to send 50 {token_id} "
        f"to account {spender_id}. Schedule the transaction instead of executing it immediately."
    )

    result = await execute_agent_request(agent, input_text, langchain_config)

    parsed_response = response_parser.parse_new_tool_messages(result)

    tool_data = parsed_response[0].parsedData
    assert (
        "Scheduled allowance transfer created successfully" in tool_data["humanMessage"]
    )


@pytest.mark.asyncio
async def test_agent_fail_exceed_allowance(
    allowance_test_setup: Dict[str, Any], langchain_config: RunnableConfig
):
    """Test that attempting to transfer more than the allowance fails gracefully."""
    agent = allowance_test_setup["agent"]
    response_parser = allowance_test_setup["response_parser"]

    executor_id = allowance_test_setup["executor_id"]
    spender_id = allowance_test_setup["spender_id"]
    token_id = allowance_test_setup["token_id"]

    # Allowance is set to 200 in setup
    input_text = (
        f"Use allowance from account {executor_id} to send 300 {token_id} "
        f"to account {spender_id}"
    )

    result = await execute_agent_request(agent, input_text, langchain_config)
    parsed_response = response_parser.parse_new_tool_messages(result)

    tool_data = parsed_response[0].parsedData
    assert (
        "Failed to transfer fungible token with allowance" in tool_data["humanMessage"]
    )
    # Accept either error - AMOUNT_EXCEEDS_ALLOWANCE when allowance exists but is insufficient,
    # or SPENDER_DOES_NOT_HAVE_ALLOWANCE when allowance is fully consumed by previous tests
    assert any(
        err in tool_data["humanMessage"]
        for err in ["AMOUNT_EXCEEDS_ALLOWANCE", "SPENDER_DOES_NOT_HAVE_ALLOWANCE"]
    )
