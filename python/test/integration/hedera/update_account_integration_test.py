"""Integration tests for UpdateAccountTool.

This test verifies on-chain account update functionality using the Hedera Agent Kit.
It includes updates to memo, token associations, staking flags, invalid inputs,
and scheduled transaction execution.
"""

from typing import cast
import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS

from hedera_agent_kit.plugins.core_account_plugin import UpdateAccountTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    UpdateAccountParameters,
    CreateAccountParametersNormalised,
    DeleteAccountParametersNormalised,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_custom_client


@pytest.fixture(scope="module")
async def setup_operator(operator_client, operator_wrapper):
    """Create an operator client and wrapper for account update tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)
    yield {"operator_client": operator_client, "operator_wrapper": operator_wrapper}


@pytest.fixture
async def setup_executor(setup_operator):
    """Create an executor account for each test."""
    operator_client: Client = setup_operator["operator_client"]
    operator_wrapper: HederaOperationsWrapper = setup_operator["operator_wrapper"]

    executor_key = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])
            ),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)
    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "operator_client": operator_client,
        "executor_account_id": executor_account_id,
        "context": context,
    }

    await executor_wrapper.delete_account(
        DeleteAccountParametersNormalised(
            account_id=executor_account_id,
            transfer_account_id=operator_client.operator_account_id,
        )
    )
    executor_client.close()


@pytest.mark.asyncio
async def test_update_account_memo_and_token_associations(setup_executor):
    """Test updating memo and max automatic token associations."""
    executor_client: Client = setup_executor["executor_client"]
    operator_wrapper: HederaOperationsWrapper = setup_executor["executor_wrapper"]
    context: Context = setup_executor["context"]
    account_id = str(executor_client.operator_account_id)

    tool = UpdateAccountTool(context)
    params = UpdateAccountParameters(
        account_id=account_id,
        account_memo="updated via integration test",
        max_automatic_token_associations=4,  # FIXME: not supported by the SDK - implemented for future use
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Account successfully updated." in result.human_message
    assert exec_result.raw.transaction_id is not None

    info = operator_wrapper.get_account_info(account_id)
    assert info is not None
    assert info.account_memo == "updated via integration test"
    # assert info.max_automatic_token_associations == 4  # FIXME: not supported by the SDK - implemented for future use


@pytest.mark.asyncio
async def test_update_account_decline_staking_reward(setup_executor):
    """Test updating declineStakingReward flag."""
    executor_client: Client = setup_executor["executor_client"]
    operator_wrapper: HederaOperationsWrapper = setup_executor["executor_wrapper"]
    context: Context = setup_executor["context"]
    account_id = str(executor_client.operator_account_id)

    tool = UpdateAccountTool(context)
    params = UpdateAccountParameters(
        account_id=account_id,
        decline_staking_reward=True,  # FIXME: not supported by the SDK - implemented for future use
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)
    assert exec_result.raw.transaction_id is not None

    info = operator_wrapper.get_account_info(account_id)
    assert info is not None
    # assert info.staking_info.decline_staking_reward is True  # FIXME: not supported by the SDK - implemented for future use


@pytest.mark.asyncio
async def test_update_account_invalid_account_id(setup_executor):
    """Test that invalid account ID results in a failure message."""
    executor_client: Client = setup_executor["executor_client"]
    context: Context = setup_executor["context"]

    tool = UpdateAccountTool(context)
    params = UpdateAccountParameters(
        account_id="0.0.999999999",
        account_memo="x",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert "Failed to update account" in result.human_message
    assert result.error is not None


@pytest.mark.asyncio
async def test_scheduled_account_update(setup_executor):
    """Test successful creation of a scheduled account update transaction."""
    executor_client: Client = setup_executor["executor_client"]
    context: Context = setup_executor["context"]
    account_id = str(setup_executor["executor_account_id"])

    tool = UpdateAccountTool(context)
    params = UpdateAccountParameters(
        account_id=account_id,
        account_memo="updated via integration test",
        max_automatic_token_associations=4,  # FIXME: not supported by the SDK - implemented for future use
        scheduling_params=SchedulingParams(is_scheduled=True, wait_for_expiry=False),
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Scheduled account update created successfully." in result.human_message
    assert "Transaction ID:" in result.human_message
    assert "Schedule ID:" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert getattr(exec_result.raw, "schedule_id", None) is not None
