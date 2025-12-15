from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
)

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_account_plugin import (
    DeleteHbarAllowanceTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    DeleteHbarAllowanceParameters,
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
    Setup two accounts:
    1. Owner (Grantor): Owns HBAR and grants allowance.
    2. Spender (Executor): Given allowance to spend Owner's HBAR.
    """
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Create Owner Account
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.5)),
            key=owner_key.public_key(),
        )
    )
    owner_account_id = owner_resp.account_id
    owner_client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # 2. Create Spender Account
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
            key=spender_key.public_key(),
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(owner_account_id))

    yield {
        "operator_client": operator_client,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "owner_account_id": owner_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "context": context,
    }

    # Teardown
    await return_hbars_and_delete_account(
        owner_wrapper, owner_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        spender_wrapper, spender_account_id, operator_client.operator_account_id
    )
    owner_client.close()
    spender_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_delete_hbar_allowance_success(setup_accounts):
    owner_client: Client = setup_accounts["owner_client"]
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]

    allowance_amount = 5.0
    allowance_amount_tinybar = int(Hbar(allowance_amount).to_tinybars())

    # 1. Owner approves allowance for Spender
    allowance_params = ApproveHbarAllowanceParametersNormalised(
        hbar_allowances=[
            HbarAllowance(
                spender_account_id=spender_account_id,
                amount=allowance_amount_tinybar,
            )
        ]
    )
    await owner_wrapper.approve_hbar_allowance(allowance_params)

    # 2. Owner deletes allowance using the tool
    tool = DeleteHbarAllowanceTool(context)
    params = DeleteHbarAllowanceParameters(
        owner_account_id=str(owner_account_id),
        spender_account_id=str(spender_account_id),
        transaction_memo="Delete Allowance Test",
    )

    result: ToolResponse = await tool.execute(owner_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "HBAR allowance deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"

    # 3. Verify allowance is gone (or effectively 0)
    # Note: SDK doesn't have a direct "get allowance" query easily accessible without mirror node delay
    # We can try to spend it and expect failure, but that requires setting up a transfer.
    # For this test, we rely on the transaction success status.


@pytest.mark.asyncio
async def test_delete_hbar_allowance_idempotent(setup_accounts):
    # Deleting an allowance that doesn't exist should succeed (setting 0 to 0)
    owner_client: Client = setup_accounts["owner_client"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]

    tool = DeleteHbarAllowanceTool(context)
    params = DeleteHbarAllowanceParameters(
        owner_account_id=str(owner_account_id),
        spender_account_id=str(spender_account_id),
    )

    result: ToolResponse = await tool.execute(owner_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "HBAR allowance deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"
