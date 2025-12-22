import time
from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    Timestamp,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit.plugins.core_account_plugin.schedule_delete import (
    ScheduleDeleteTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferHbarParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    ScheduleDeleteTransactionParameters,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Setup Executor (who will act as the Schedule Admin)
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup Recipient (for the underlying transfer in the schedule)
    recipient_key_pair = PrivateKey.generate_ed25519()
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
            key=recipient_key_pair.public_key(),
        )
    )
    recipient_account_id = recipient_resp.account_id

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_account_id": recipient_account_id,
        "context": context,
    }

    # Teardown

    # 1. Cleanup Executor
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )

    # 2. Cleanup Recipient
    # We must use a client authenticated with the recipient's key to delete it/transfer funds out.
    recipient_client = get_custom_client(recipient_account_id, recipient_key_pair)
    recipient_cleanup_wrapper = HederaOperationsWrapper(recipient_client)

    await return_hbars_and_delete_account(
        recipient_cleanup_wrapper,
        recipient_account_id,
        operator_client.operator_account_id,
    )

    recipient_client.close()
    executor_client.close()
    operator_client.close()


async def create_deletable_scheduled_transaction(
    wrapper: HederaOperationsWrapper,
    client: Client,
    payer_id: AccountId,
    recipient_id: AccountId,
) -> str:
    """
    Creates a scheduled transaction where the 'client' operator is the admin,
    allowing it to be deleted later.
    """

    # Calculate expiration time (1 hour from now)
    future_seconds = int(time.time() + 60 * 60)
    expiration = Timestamp(seconds=future_seconds, nanos=0)

    # Explicitly set admin_key to the operator's key to allow deletion
    scheduling_params: ScheduleCreateParams = ScheduleCreateParams(
        admin_key=client.operator_private_key.public_key(),
        expiration_time=expiration,
        wait_for_expiry=True,
    )

    params = TransferHbarParametersNormalised(
        transaction_memo=f"Test Schedule {time.time()}",
        scheduling_params=scheduling_params,
        hbar_transfers={
            payer_id: -1,
            recipient_id: 1,
        },
    )

    result = await wrapper.transfer_hbar(params)

    if not result.schedule_id:
        raise ValueError(
            "Failed to create scheduled transaction: No Schedule ID returned"
        )

    return str(result.schedule_id)


@pytest.mark.asyncio
async def test_successfully_deletes_scheduled_transaction_before_execution(
    setup_accounts,
):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    recipient_account_id: AccountId = setup_accounts["recipient_account_id"]
    context: Context = setup_accounts["context"]

    # 1. Create a scheduled transaction that allows deletion
    schedule_id = await create_deletable_scheduled_transaction(
        executor_wrapper,
        executor_client,
        executor_account_id,
        recipient_account_id,
    )

    # 2. Use the tool to delete it
    tool = ScheduleDeleteTool(context)
    params = ScheduleDeleteTransactionParameters(schedule_id=schedule_id)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "successfully deleted" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.status == "SUCCESS"


@pytest.mark.asyncio
async def test_delete_fails_with_invalid_schedule_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = ScheduleDeleteTransactionParameters(schedule_id="0.0.999999")
    tool = ScheduleDeleteTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to delete a schedule" in result.human_message


@pytest.mark.asyncio
async def test_delete_fails_with_malformed_schedule_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = ScheduleDeleteTransactionParameters(schedule_id="invalid-schedule-id")
    tool = ScheduleDeleteTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to delete a schedule" in result.human_message
