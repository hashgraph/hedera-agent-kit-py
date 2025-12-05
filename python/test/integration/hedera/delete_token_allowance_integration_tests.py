from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    TokenAllowance,
    SupplyType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from hedera_agent_kit.plugins.core_token_plugin import DeleteTokenAllowanceTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteTokenAllowanceParameters,
    ApproveTokenAllowanceParametersNormalised,
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
    """
    Setup accounts and token:
    1. Executor (Owner): Owns the token and grants allowance.
    2. Spender: Given allowance to spend Owner's token.
    3. Token: A fungible token created by the Executor.
    """
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Create Executor Account (Token Owner)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(30), key=executor_key.public_key()
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Create Spender Account
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(10), key=spender_key.public_key()
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    # 3. Create Token
    token_params = TokenParams(
        token_name="DeletableToken",
        token_symbol="DEL",
        decimals=2,
        initial_supply=100,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
        auto_renew_account_id=executor_account_id,
    )

    # We need to pass keys explicitly for token creation wrapper
    token_keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )

    create_token_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params, keys=token_keys
    )

    token_resp = await executor_wrapper.create_fungible_token(create_token_params)
    token_id = token_resp.token_id

    await wait(MIRROR_NODE_WAITING_TIME)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "spender_client": spender_client,
        "spender_account_id": spender_account_id,
        "token_id": token_id,
        "context": context,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        spender_wrapper, spender_account_id, operator_client.operator_account_id
    )

    executor_client.close()
    spender_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_deletes_allowance_with_explicit_owner(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    token_id = setup_accounts["token_id"]
    context: Context = setup_accounts["context"]

    # 1. Approve allowance first
    await executor_wrapper.approve_token_allowance(
        ApproveTokenAllowanceParametersNormalised(
            token_allowances=[
                TokenAllowance(
                    token_id=token_id,
                    owner_account_id=executor_account_id,
                    spender_account_id=spender_account_id,
                    amount=10,
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Delete allowance explicitly
    params = DeleteTokenAllowanceParameters(
        owner_account_id=str(executor_account_id),
        spender_account_id=str(spender_account_id),
        token_ids=[str(token_id)],
    )

    tool = DeleteTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Token allowance(s) deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_deletes_allowance_with_default_owner(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    token_id = setup_accounts["token_id"]
    context: Context = setup_accounts["context"]

    # 1. Re-approve allowance (since previous test might have deleted it)
    await executor_wrapper.approve_token_allowance(
        ApproveTokenAllowanceParametersNormalised(
            token_allowances=[
                TokenAllowance(
                    token_id=token_id,
                    owner_account_id=executor_account_id,
                    spender_account_id=spender_account_id,
                    amount=10,
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Delete allowance relying on context owner ID
    params = DeleteTokenAllowanceParameters(
        spender_account_id=str(spender_account_id),
        token_ids=[str(token_id)],
    )

    tool = DeleteTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Token allowance(s) deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"
    assert exec_result.raw.transaction_id is not None
