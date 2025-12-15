"""Integration tests for sign schedule transaction tool.

This module tests the SignScheduleTransactionTool directly against the Hedera network,
verifying that scheduled transactions can be signed correctly.
"""

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

from hedera_agent_kit.plugins.core_account_plugin.sign_schedule_transaction import (
    SignScheduleTransactionTool,
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
    SignScheduleTransactionToolParameters,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    """Setup operator, executor and recipient accounts for tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create executor account (who will sign scheduled transactions)
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

    # Create recipient account (for the underlying transfer in the schedule)
    recipient_key_pair = PrivateKey.generate_ed25519()
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.1)),
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
    # Cleanup Executor
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )

    # Cleanup Recipient
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


async def create_signable_scheduled_transaction(
    operator_wrapper: HederaOperationsWrapper,
    executor_account_id: AccountId,
    recipient_id: AccountId,
) -> str:
    """
    Creates a scheduled transaction that requires signature from executor.
    
    The OPERATOR creates the schedule, but the EXECUTOR is the one whose
    account is being debited. This ensures the executor's signature is
    required and not already present.
    
    The schedule is created with wait_for_expiry=True so it won't auto-execute
    when signed.
    """
    # Calculate expiration time (1 hour from now)
    future_seconds = int(time.time() + 60 * 60)
    expiration = Timestamp(seconds=future_seconds, nanos=0)

    scheduling_params: ScheduleCreateParams = ScheduleCreateParams(
        expiration_time=expiration,
        wait_for_expiry=True,  # Won't execute immediately after signing
    )

    # The scheduled transfer debits the EXECUTOR (not the operator who creates it)
    # This means the executor's signature is required
    params = TransferHbarParametersNormalised(
        transaction_memo=f"Test Schedule Sign {time.time()}",
        scheduling_params=scheduling_params,
        hbar_transfers={
            executor_account_id: -1,  # Executor is being debited - needs to sign
            recipient_id: 1,
        },
    )

    result = await operator_wrapper.transfer_hbar(params)

    if not result.schedule_id:
        raise ValueError(
            "Failed to create scheduled transaction: No Schedule ID returned"
        )

    return str(result.schedule_id)


async def create_signable_scheduled_transaction_no_wait(
    operator_wrapper: HederaOperationsWrapper,
    executor_account_id: AccountId,
    recipient_id: AccountId,
) -> str:
    """
    Creates a scheduled transaction that will execute immediately after all required
    signatures are collected (wait_for_expiry=False).
    
    The OPERATOR creates the schedule, but the EXECUTOR is debited.
    """
    # Calculate expiration time (1 hour from now)
    future_seconds = int(time.time() + 60 * 60)
    expiration = Timestamp(seconds=future_seconds, nanos=0)

    scheduling_params: ScheduleCreateParams = ScheduleCreateParams(
        expiration_time=expiration,
        wait_for_expiry=False,  # Execute immediately when signed
    )

    params = TransferHbarParametersNormalised(
        transaction_memo=f"Test Schedule Auto-Execute {time.time()}",
        scheduling_params=scheduling_params,
        hbar_transfers={
            executor_account_id: -1,  # Executor is being debited - needs to sign
            recipient_id: 1,
        },
    )

    result = await operator_wrapper.transfer_hbar(params)

    if not result.schedule_id:
        raise ValueError(
            "Failed to create scheduled transaction: No Schedule ID returned"
        )

    return str(result.schedule_id)


@pytest.mark.asyncio
async def test_successfully_signs_scheduled_transaction(setup_accounts):
    """Test successfully signing a scheduled transaction."""
    operator_wrapper: HederaOperationsWrapper = setup_accounts["operator_wrapper"]
    executor_client: Client = setup_accounts["executor_client"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    recipient_account_id: AccountId = setup_accounts["recipient_account_id"]
    context: Context = setup_accounts["context"]

    # Create a scheduled transaction (operator creates, executor needs to sign)
    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper,
        executor_account_id,
        recipient_account_id,
    )

    # Use the tool to sign it
    tool = SignScheduleTransactionTool(context)
    params = SignScheduleTransactionToolParameters(schedule_id=schedule_id)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "successfully signed" in result.human_message
    assert "Transaction ID" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.status == "SUCCESS"


@pytest.mark.asyncio
async def test_sign_fails_with_invalid_schedule_id(setup_accounts):
    """Test that signing fails with an invalid schedule ID."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = SignScheduleTransactionToolParameters(schedule_id="0.0.999999")
    tool = SignScheduleTransactionTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to sign scheduled transaction" in result.human_message


@pytest.mark.asyncio
async def test_sign_fails_with_malformed_schedule_id(setup_accounts):
    """Test that signing fails with a malformed schedule ID."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = SignScheduleTransactionToolParameters(schedule_id="invalid-schedule-id")
    tool = SignScheduleTransactionTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to sign scheduled transaction" in result.human_message


@pytest.mark.asyncio
async def test_sign_fails_with_empty_schedule_id(setup_accounts):
    """Test that signing fails with an empty schedule ID."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = SignScheduleTransactionToolParameters(schedule_id="")
    tool = SignScheduleTransactionTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to sign scheduled transaction" in result.human_message


@pytest.mark.asyncio
async def test_sign_fails_when_schedule_already_executed(setup_accounts):
    """Test that signing fails when the schedule has already been executed."""
    operator_wrapper: HederaOperationsWrapper = setup_accounts["operator_wrapper"]
    executor_client: Client = setup_accounts["executor_client"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    recipient_account_id: AccountId = setup_accounts["recipient_account_id"]
    context: Context = setup_accounts["context"]

    # Create a scheduled transaction that executes immediately after signing
    # Operator creates, executor needs to sign
    schedule_id = await create_signable_scheduled_transaction_no_wait(
        operator_wrapper,
        executor_account_id,
        recipient_account_id,
    )

    # First sign should succeed and execute the transaction
    tool = SignScheduleTransactionTool(context)
    params = SignScheduleTransactionToolParameters(schedule_id=schedule_id)
    first_result: ToolResponse = await tool.execute(executor_client, context, params)

    # This may succeed or fail depending on whether the schedule auto-executes
    # Try to sign again - this should fail as the schedule is already executed
    second_result: ToolResponse = await tool.execute(executor_client, context, params)

    # The second signing attempt should fail as the schedule is already executed
    assert second_result.error is not None or "Failed" in second_result.human_message


@pytest.mark.asyncio
async def test_sign_with_special_characters_in_schedule_id(setup_accounts):
    """Test that signing fails with special characters in schedule ID."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = SignScheduleTransactionToolParameters(schedule_id="0.0.123@#$%")
    tool = SignScheduleTransactionTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to sign scheduled transaction" in result.human_message


@pytest.mark.asyncio
async def test_sign_with_very_long_schedule_id(setup_accounts):
    """Test that signing fails with an overly long schedule ID."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    long_schedule_id = "0.0.123456789012345678901234567890"
    params = SignScheduleTransactionToolParameters(schedule_id=long_schedule_id)
    tool = SignScheduleTransactionTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to sign scheduled transaction" in result.human_message
