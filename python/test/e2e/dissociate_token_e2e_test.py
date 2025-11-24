"""
End-to-end tests for dissociate token tool using the HederaOperationsWrapper approach.
"""

from typing import cast, List

import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, TokenId
from hiero_sdk_python.account.account_balance import AccountBalance
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
)

from hedera_agent_kit_py.plugins.core_token_plugin import DissociateTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    DissociateTokenParameters,
    CreateFungibleTokenParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Executor account (the one dissociating tokens)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(40)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Token creator / treasury account
    token_executor_key = PrivateKey.generate_ed25519()
    token_executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=token_executor_key.public_key(), initial_balance=Hbar(40)
        )
    )
    token_executor_account_id = token_executor_resp.account_id
    token_executor_client = get_custom_client(
        token_executor_account_id, token_executor_key
    )
    token_executor_wrapper = HederaOperationsWrapper(token_executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    await wait(MIRROR_NODE_WAITING_TIME)

    FT_PARAMS = TokenParams(
        token_name="DissocToken",
        token_symbol="DISS",
        initial_supply=1,
        decimals=0,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=token_executor_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "token_executor_client": token_executor_client,
        "token_executor_wrapper": token_executor_wrapper,
        "token_executor_account_id": token_executor_account_id,
        "context": context,
        "FT_PARAMS": FT_PARAMS,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        token_executor_wrapper,
        token_executor_account_id,
        operator_client.operator_account_id,
    )
    token_executor_client.close()

    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client,
    ft_params: TokenParams,
):
    """Creates a token using the wrapper."""
    treasury_pubkey = executor_client.operator_private_key.public_key()
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


async def associate_token_to_account(
    wrapper: HederaOperationsWrapper, account_id: AccountId, token_ids: List[TokenId]
):
    """Helper to manually associate tokens before testing dissociation."""
    await wrapper.associate_token(
        {"accountId": str(account_id), "tokenId": str(token_ids[0])}
    )


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_dissociate_single_token(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id = setup_accounts["executor_account_id"]
    executor_key = setup_accounts["executor_key"]
    token_executor_client = setup_accounts["token_executor_client"]
    token_executor_wrapper: HederaOperationsWrapper = setup_accounts[
        "token_executor_wrapper"
    ]
    context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    # 1. Create token
    token_id = await create_test_token(
        token_executor_wrapper, token_executor_client, ft_params
    )

    # 2. Setup: Associate manually first
    await associate_token_to_account(executor_wrapper, executor_account_id, [token_id])
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify association exists before dissociation
    balances_pre: AccountBalance = executor_wrapper.get_account_balances(
        str(executor_account_id)
    )
    assert balances_pre.token_balances.get(token_id) is not None

    # 3. Execute Tool
    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Verify Dissociation
    balances_post: AccountBalance = executor_wrapper.get_account_balances(
        str(executor_account_id)
    )
    is_associated = balances_post.token_balances.get(token_id) is not None

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "successfully dissociated" in result.human_message
    assert is_associated is False


@pytest.mark.asyncio
async def test_dissociate_multiple_tokens(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id = setup_accounts["executor_account_id"]
    token_executor_client = setup_accounts["token_executor_client"]
    token_executor_wrapper: HederaOperationsWrapper = setup_accounts[
        "token_executor_wrapper"
    ]
    token_executor_account_id = setup_accounts["token_executor_account_id"]
    context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    # 1. Create two tokens
    token_id_1 = await create_test_token(
        token_executor_wrapper, token_executor_client, ft_params
    )

    ft_params2 = TokenParams(
        token_name="Dissoc2",
        token_symbol="DS2",
        initial_supply=1,
        decimals=0,
        max_supply=500,
        supply_type=SupplyType.FINITE,
        treasury_account_id=token_executor_account_id,
    )
    token_id_2 = await create_test_token(
        token_executor_wrapper, token_executor_client, ft_params2
    )

    # 2. Setup: Associate both
    await associate_token_to_account(
        executor_wrapper, executor_account_id, [token_id_2]
    )
    await associate_token_to_account(
        executor_wrapper, executor_account_id, [token_id_1]
    )
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Execute Tool
    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id_1), str(token_id_2)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Verify Dissociation
    balances: AccountBalance = executor_wrapper.get_account_balances(
        str(executor_account_id)
    )
    has_token_1 = balances.token_balances.get(token_id_1) is not None
    has_token_2 = balances.token_balances.get(token_id_2) is not None

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert has_token_1 is False
    assert has_token_2 is False


@pytest.mark.asyncio
async def test_fail_dissociate_not_associated_token(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    token_executor_client = setup_accounts["token_executor_client"]
    token_executor_wrapper: HederaOperationsWrapper = setup_accounts[
        "token_executor_wrapper"
    ]
    context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    # 1. Create token but DO NOT associate
    token_id = await create_test_token(
        token_executor_wrapper, token_executor_client, ft_params
    )

    # 2. Execute Tool (Should Fail)
    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id)])

    try:
        result: ToolResponse = await tool.execute(executor_client, context, params)
        exec_result = cast(ExecutedTransactionToolResponse, result)

        assert "Failed to dissociate" in result.human_message
        assert (
            "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in str(exec_result.raw.error)
            or "failed" in str(exec_result.raw.error).lower()
        )
    except Exception as e:
        # If the tool raises directly instead of returning a ToolResponse
        assert "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in str(e)


@pytest.mark.asyncio
async def test_fail_dissociate_non_existent_token(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    fake_token_id = "0.0.999999999"

    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[fake_token_id])

    try:
        result: ToolResponse = await tool.execute(executor_client, context, params)
        assert "Failed to dissociate" in result.human_message
    except Exception as e:
        # Fallback if tool raises
        assert "INVALID_TOKEN_ID" in str(e) or "failed" in str(e).lower()
