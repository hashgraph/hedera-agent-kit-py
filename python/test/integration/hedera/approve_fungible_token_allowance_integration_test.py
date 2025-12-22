from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    SupplyType,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit.plugins.core_account_plugin.approve_fungible_token_allowance import (
    ApproveFungibleTokenAllowanceTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    ApproveTokenAllowanceParameters,
    CreateAccountParametersNormalised,
    TokenApproval,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Setup executor account (the one granting allowance)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)

    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup spender account (the one receiving allowance)
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=spender_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Create a fungible token where executor is treasury
    treasury_public_key = executor_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    ft_params = TokenParams(
        token_name="AllowToken",
        token_symbol="ALW",
        initial_supply=1000,
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

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "context": context,
        "token_id": token_id,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        spender_wrapper,
        spender_account_id,
        operator_client.operator_account_id,
    )
    spender_client.close()


@pytest.mark.asyncio
async def test_approves_token_allowance_with_explicit_owner_and_memo(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]
    token_id: str = str(setup_accounts["token_id"])

    params = ApproveTokenAllowanceParameters(
        owner_account_id=str(executor_account_id),
        spender_account_id=str(spender_account_id),
        token_approvals=[TokenApproval(token_id=token_id, amount=25)],
        transaction_memo="Integration token approve",
    )

    tool = ApproveFungibleTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "Fungible token allowance(s) approved successfully" in result.human_message
    assert "Transaction ID:" in result.human_message


@pytest.mark.asyncio
async def test_approves_multiple_token_allowances_with_default_owner(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]
    token_id: str = str(setup_accounts["token_id"])

    # Using the same token twice just to test list handling
    params = ApproveTokenAllowanceParameters(
        spender_account_id=str(spender_account_id),
        token_approvals=[
            TokenApproval(token_id=token_id, amount=1),
            TokenApproval(token_id=token_id, amount=2),
        ],
    )

    tool = ApproveFungibleTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "Fungible token allowance(s) approved successfully" in result.human_message
