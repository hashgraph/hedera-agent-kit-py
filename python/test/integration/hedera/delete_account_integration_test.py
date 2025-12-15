from typing import cast

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_account_plugin import DeleteAccountTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteAccountParameters,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(5)),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "context": context,
    }

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


async def create_temp_account(
    executor_wrapper: HederaOperationsWrapper, executor_client: Client
):
    resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1)),
            key=executor_client.operator_private_key.public_key(),
        )
    )
    return resp.account_id


@pytest.mark.asyncio
async def test_delete_account_transfers_balance_to_executor(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    account_id = await create_temp_account(executor_wrapper, executor_client)

    tool = DeleteAccountTool(context)
    params = DeleteAccountParameters(account_id=str(account_id))
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Account successfully deleted." in result.human_message
    assert "Transaction ID:" in result.human_message
    assert exec_result.raw.status == "SUCCESS"


@pytest.mark.asyncio
async def test_delete_account_transfers_to_specified_account(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    operator_client: Client = setup_accounts["operator_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    account_id = await create_temp_account(executor_wrapper, executor_client)
    transfer_to = str(operator_client.operator_account_id)

    tool = DeleteAccountTool(context)
    params = DeleteAccountParameters(
        account_id=str(account_id), transfer_account_id=transfer_to
    )
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.status == "SUCCESS"


@pytest.mark.asyncio
async def test_delete_nonexistent_account_should_fail(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = DeleteAccountTool(context)
    params = DeleteAccountParameters(account_id="0.0.999999999")

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "INVALID_ACCOUNT_ID" in result.human_message or result.error is not None
    assert result.error is not None
    assert "Failed to delete account" in result.human_message
