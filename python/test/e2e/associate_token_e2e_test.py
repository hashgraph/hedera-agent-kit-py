"""
End-to-end tests for associate token tool using the HederaOperationsWrapper approach.
"""

from typing import cast

import pytest
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
)

from hedera_agent_kit.plugins.core_token_plugin import AssociateTokenTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    AssociateTokenParameters,
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
async def setup_environment():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Executor account (The Agent who associates tokens)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(UsdToHbarService.usd_to_hbar(2.5))
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Token creator / treasury account (Mints the tokens)
    creator_key = PrivateKey.generate_ed25519()
    creator_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=creator_key.public_key(), initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75))
        )
    )
    creator_account_id = creator_resp.account_id
    creator_client = get_custom_client(creator_account_id, creator_key)
    creator_wrapper = HederaOperationsWrapper(creator_client)

    # Context for the tool
    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    await wait(MIRROR_NODE_WAITING_TIME)

    # Base Token Params
    FT_PARAMS = TokenParams(
        token_name="AssocToken",
        token_symbol="ASSOC",
        initial_supply=1,
        decimals=0,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=creator_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "creator_client": creator_client,
        "creator_wrapper": creator_wrapper,
        "creator_account_id": creator_account_id,
        "context": context,
        "FT_PARAMS": FT_PARAMS,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        creator_wrapper,
        creator_account_id,
        operator_client.operator_account_id,
    )
    creator_client.close()

    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_token(
    creator_wrapper: HederaOperationsWrapper,
    creator_client,
    ft_params: TokenParams,
):
    """Helper to create a token using the Creator account."""
    treasury_pubkey = creator_client.operator_private_key.public_key()
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    resp = await creator_wrapper.create_fungible_token(create_params)
    return resp.token_id


async def check_token_is_associated(
    wrapper: HederaOperationsWrapper, account_id: str, token_id_str: str
) -> bool:
    """Checks if a specific token ID is present in the account's balances."""
    balances = wrapper.get_account_balances(account_id)
    if balances.token_balances:
        # Check if the token ID string exists in the token_balances dictionary keys
        for t_id in balances.token_balances.keys():
            if str(t_id) == token_id_str:
                return True
    return False


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_associate_token_to_executor_account(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    creator_client = setup_environment["creator_client"]
    creator_wrapper = setup_environment["creator_wrapper"]

    context = setup_environment["context"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Create token via treasury client
    token_id = await create_test_token(
        creator_wrapper,
        creator_client,
        ft_params,
    )
    token_id_str = str(token_id)

    # 2. Execute Tool
    tool = AssociateTokenTool(context)
    params = AssociateTokenParameters(token_ids=[token_id_str])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify
    associated = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str
    )

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "Tokens successfully associated" in result.human_message
    assert associated is True


@pytest.mark.asyncio
async def test_associate_two_tokens_to_executor_account(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    creator_client = setup_environment["creator_client"]
    creator_wrapper = setup_environment["creator_wrapper"]
    creator_account_id = setup_environment["creator_account_id"]

    context = setup_environment["context"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Create first token
    token_id_1 = await create_test_token(
        creator_wrapper,
        creator_client,
        ft_params,
    )

    # 2. Create second token
    ft_params2 = TokenParams(
        token_name="token2",
        token_symbol="TKN2",
        initial_supply=1,
        decimals=0,
        max_supply=500,
        supply_type=SupplyType.FINITE,
        treasury_account_id=creator_account_id,
    )
    token_id_2 = await create_test_token(
        creator_wrapper,
        creator_client,
        ft_params2,
    )

    token_id_str_1 = str(token_id_1)
    token_id_str_2 = str(token_id_2)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Execute Tool
    tool = AssociateTokenTool(context)
    params = AssociateTokenParameters(token_ids=[token_id_str_1, token_id_str_2])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Verify
    associated_first = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str_1
    )
    associated_second = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str_2
    )

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert associated_first is True
    assert associated_second is True
