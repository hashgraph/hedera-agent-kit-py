from pprint import pprint
from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
)

from hedera_agent_kit_py.plugins.core_account_plugin.approve_hbar_allowance import (
    ApproveHbarAllowanceTool,
)
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    ApproveHbarAllowanceParameters,
    CreateAccountParametersNormalised,
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

    # Setup executor account (the one granting allowance)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(10)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup spender account (the one receiving allowance)
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=spender_key.public_key(), initial_balance=Hbar(5)
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

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

    operator_client.close()


@pytest.mark.asyncio
async def test_approves_allowance_with_explicit_owner_and_memo(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]

    params = ApproveHbarAllowanceParameters(
        owner_account_id=str(executor_account_id),
        spender_account_id=str(spender_account_id),
        amount=1.25,
        transaction_memo="Integration approve test",
    )

    tool = ApproveHbarAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    pprint(result)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "HBAR allowance approved successfully" in result.human_message
    assert "Transaction ID:" in result.human_message


@pytest.mark.asyncio
async def test_approves_allowance_with_default_owner_and_sub_1_hbar_amount(
    setup_accounts,
):
    executor_client: Client = setup_accounts["executor_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]

    params = ApproveHbarAllowanceParameters(
        spender_account_id=str(spender_account_id),
        amount=0.00000001,  # 1 tinybar
    )

    tool = ApproveHbarAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "HBAR allowance approved successfully" in result.human_message
    assert "Transaction ID:" in result.human_message
