from typing import cast

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar, AccountId

from hedera_agent_kit_py.plugins.core_account_plugin import (
    TransferHbarWithAllowanceTool,
)
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    TransferHbarWithAllowanceParameters,
    TransferHbarEntry,
    ApproveHbarAllowanceParametersNormalised,
    HbarAllowance,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    """
    Setup three accounts:
    1. Owner (Grantor): Owns HBAR and grants allowance.
    2. Spender (Executor): Given allowance to spend Owner's HBAR.
    3. Receiver: Receives the HBAR.
    """
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Create Owner Account
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(50), key=owner_key.public_key()
        )
    )
    owner_account_id = owner_resp.account_id
    owner_client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

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

    # 3. Create Receiver Account
    receiver_key = PrivateKey.generate_ed25519()
    receiver_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(0), key=receiver_key.public_key()
        )
    )
    receiver_account_id = receiver_resp.account_id
    receiver_client = get_custom_client(receiver_account_id, receiver_key)
    receiver_wrapper = HederaOperationsWrapper(receiver_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(spender_account_id))

    yield {
        "operator_client": operator_client,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "owner_account_id": owner_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "receiver_wrapper": receiver_wrapper,
        "receiver_account_id": receiver_account_id,
        "context": context,
    }

    # Teardown
    await return_hbars_and_delete_account(
        owner_wrapper, owner_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        spender_wrapper, spender_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        receiver_wrapper, receiver_account_id, operator_client.operator_account_id
    )
    owner_client.close()
    spender_client.close()
    receiver_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_transfer_hbar_without_allowance_should_fail(setup_accounts):
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_client: Client = setup_accounts["spender_client"]
    receiver_account_id: AccountId = setup_accounts["receiver_account_id"]
    context: Context = setup_accounts["context"]

    # No approval step

    tool = TransferHbarWithAllowanceTool(context)
    params = TransferHbarWithAllowanceParameters(
        source_account_id=str(owner_account_id),
        transfers=[TransferHbarEntry(account_id=str(receiver_account_id), amount=1.0)],
    )

    result: ToolResponse = await tool.execute(spender_client, context, params)

    assert result.error is not None
    assert (
        "SPENDER_DOES_NOT_HAVE_ALLOWANCE" in result.human_message
        or "AMOUNT_EXCEEDS_ALLOWANCE" in result.human_message
    )


@pytest.mark.asyncio
async def test_transfer_hbar_with_allowance_success(setup_accounts):
    owner_client: Client = setup_accounts["owner_client"]
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_client: Client = setup_accounts["spender_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    receiver_wrapper: HederaOperationsWrapper = setup_accounts["receiver_wrapper"]
    receiver_account_id: AccountId = setup_accounts["receiver_account_id"]
    context: Context = setup_accounts["context"]

    transfer_amount = 5.0
    transfer_amount_tinybar = int(Hbar(transfer_amount).to_tinybars())

    # 1. Owner approves allowance for Spender
    allowance_params = ApproveHbarAllowanceParametersNormalised(
        hbar_allowances=[
            HbarAllowance(
                spender_account_id=spender_account_id,
                amount=transfer_amount_tinybar,
            )
        ]
    )
    await owner_wrapper.approve_hbar_allowance(allowance_params)

    # 2. Spender executes transfer using allowance tool
    tool = TransferHbarWithAllowanceTool(context)
    params = TransferHbarWithAllowanceParameters(
        source_account_id=str(owner_account_id),
        transfers=[
            TransferHbarEntry(
                account_id=str(receiver_account_id), amount=transfer_amount
            )
        ],
        transaction_memo="Test Allowance Transfer",
    )

    # Note: Spender client executes the transaction
    result: ToolResponse = await tool.execute(spender_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "HBAR successfully transferred with allowance" in result.human_message
    assert exec_result.raw.status == "SUCCESS"

    # 3. Verify Balances
    # Receiver should have received funds
    receiver_balance = receiver_wrapper.get_account_hbar_balance(
        str(receiver_account_id)
    )
    assert receiver_balance == transfer_amount_tinybar


@pytest.mark.asyncio
async def test_transfer_hbar_with_insufficient_allowance_should_fail(setup_accounts):
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_client: Client = setup_accounts["spender_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    receiver_account_id: AccountId = setup_accounts["receiver_account_id"]
    context: Context = setup_accounts["context"]

    approved_amount = 1.0
    transfer_amount = 10.0

    # 1. Owner approves small allowance
    allowance_params = ApproveHbarAllowanceParametersNormalised(
        hbar_allowances=[
            HbarAllowance(
                spender_account_id=spender_account_id,
                amount=int(Hbar(approved_amount).to_tinybars()),
            )
        ]
    )
    await owner_wrapper.approve_hbar_allowance(allowance_params)

    # 2. Spender tries to transfer larger amount
    tool = TransferHbarWithAllowanceTool(context)
    params = TransferHbarWithAllowanceParameters(
        source_account_id=str(owner_account_id),
        transfers=[
            TransferHbarEntry(
                account_id=str(receiver_account_id), amount=transfer_amount
            )
        ],
    )

    result: ToolResponse = await tool.execute(spender_client, context, params)

    # 3. Expect failure
    assert result.error is not None
    assert (
        "AMOUNT_EXCEEDS_ALLOWANCE" in result.human_message
        or "SPENDER_DOES_NOT_HAVE_ALLOWANCE" in result.human_message
        or "INVALID_TRANSACTION" in (result.error or "")
    )
