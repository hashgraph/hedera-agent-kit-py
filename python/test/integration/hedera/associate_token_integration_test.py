from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    SupplyType,
)
from hiero_sdk_python.account.account_balance import AccountBalance
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_plugin import AssociateTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    AssociateTokenParameters,
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Setup executor account (the one associating tokens)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup token executor account (the one creating/treasuring tokens)
    token_executor_key = PrivateKey.generate_ed25519()
    token_executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=token_executor_key.public_key(), initial_balance=Hbar(20)
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
        token_name="AssocToken",
        token_symbol="ASSOC",
        initial_supply=1,  # SDK forces non-zero initial supply for tokens with finite supply
        decimals=0,
        max_supply=1000,
        supply_type=SupplyType.FINITE,  # SupplyType.FINITE = 1
        treasury_account_id=token_executor_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "token_executor_client": token_executor_client,
        "token_executor_wrapper": token_executor_wrapper,
        "token_executor_account_id": token_executor_account_id,
        "context": context,
        "FT_PARAMS": FT_PARAMS,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        token_executor_wrapper,
        token_executor_account_id,
        operator_client.operator_account_id,
    )
    token_executor_client.close()

    operator_client.close()


async def create_test_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client: Client,
    treasury_account_id: AccountId,
    ft_params: TokenParams,
):
    # Keys can be the treasury's key
    treasury_public_key = executor_client.operator_private_key.public_key()

    keys: TokenKeys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )

    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


@pytest.mark.asyncio
async def test_associate_token_to_executor_account(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    token_executor_client: Client = setup_accounts["token_executor_client"]
    token_executor_wrapper: HederaOperationsWrapper = setup_accounts[
        "token_executor_wrapper"
    ]
    token_executor_account_id: AccountId = setup_accounts["token_executor_account_id"]
    context: Context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    token_id_ft = await create_test_token(
        token_executor_wrapper,
        token_executor_client,
        token_executor_account_id,
        ft_params,
    )

    tool = AssociateTokenTool(context)
    params = AssociateTokenParameters(token_ids=[str(token_id_ft)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    balances: AccountBalance = executor_wrapper.get_account_balances(
        str(executor_account_id)
    )
    associated = balances.token_balances.get(token_id_ft) is not None

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "Tokens successfully associated" in result.human_message
    assert associated is True


@pytest.mark.asyncio
async def test_associate_two_tokens_to_executor_account(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    token_executor_client: Client = setup_accounts["token_executor_client"]
    token_executor_wrapper: HederaOperationsWrapper = setup_accounts[
        "token_executor_wrapper"
    ]
    token_executor_account_id: AccountId = setup_accounts["token_executor_account_id"]
    context: Context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    # Create first token
    token_id_ft1 = await create_test_token(
        token_executor_wrapper,
        token_executor_client,
        token_executor_account_id,
        ft_params,
    )

    ft_params_2 = TokenParams(
        token_name="token2",
        supply_type=SupplyType.FINITE,
        initial_supply=1,
        decimals=0,
        max_supply=500,
        token_symbol="TKN2",
        treasury_account_id=token_executor_account_id,
    )

    # Create a second token
    token_id_ft2 = await create_test_token(
        token_executor_wrapper,
        token_executor_client,
        token_executor_account_id,
        ft_params_2,
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = AssociateTokenTool(context)
    params = AssociateTokenParameters(token_ids=[str(token_id_ft1), str(token_id_ft2)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    await wait(MIRROR_NODE_WAITING_TIME)

    balances: AccountBalance = executor_wrapper.get_account_balances(
        str(executor_account_id)
    )
    associated_first = balances.token_balances.get(token_id_ft1) is not None
    associated_second = balances.token_balances.get(token_id_ft2) is not None

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert associated_first is True
    assert associated_second is True
