"""Hedera integration tests for create account tool.

This module tests the account creation tool by calling it directly with parameters,
omitting the LLM and focusing on testing logic and on-chain execution.
"""

from typing import cast

import pytest
from hiero_sdk_python import PrivateKey, Hbar, PublicKey, Client

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_account_plugin import CreateAccountTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParameters,
    CreateAccountParametersNormalised,
    SchedulingParams,
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
    """Setup operator and executor accounts for tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "operator_wrapper": operator_wrapper,
        "context": context,
    }

    # Cleanup
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )

    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_create_account_with_executor_public_key_by_default(setup_accounts):
    """Test creating an account with an executor public key by default."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters()

    tool = CreateAccountTool(context)
    result = await tool.execute(executor_client, context, params)
    assert result.error is None  # check that the response is not an error
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Account created successfully." in result.human_message
    assert "Transaction ID:" in result.human_message
    assert "New Account ID:" in result.human_message

    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.account_id is not None

    # Verify account exists
    info = executor_wrapper.get_account_info(str(exec_result.raw.account_id))
    assert str(info.account_id) == str(exec_result.raw.account_id)

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        exec_result.raw.account_id,
        setup_accounts["operator_client"].operator_account_id,
    )


@pytest.mark.asyncio
async def test_create_account_with_initial_balance_and_memo(setup_accounts):
    """Test creating an account with initial balance and memo."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(
        initial_balance=0.05,
        account_memo="Integration test account",
    )

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert result.error is None  # check that the response is not an error
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Account created successfully." in result.human_message
    assert exec_result.raw.account_id is not None

    assert result.error is None
    new_account_id = str(exec_result.raw.account_id)

    # Verify balance
    balance = executor_wrapper.get_account_hbar_balance(new_account_id)
    assert balance >= int(0.05 * 1e8)  # tinybars

    # Verify memo
    info = executor_wrapper.get_account_info(new_account_id)
    assert info.account_memo == "Integration test account"

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        exec_result.raw.account_id,
        setup_accounts["operator_client"].operator_account_id,
    )


@pytest.mark.asyncio
async def test_create_account_with_explicit_public_key(setup_accounts):
    """Test creating an account with an explicit public key."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    public_key: PublicKey = executor_client.operator_private_key.public_key()
    params = CreateAccountParameters(
        public_key=public_key.to_string_der(),
    )

    tool: CreateAccountTool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert result.error is None  # check that the response is not an error
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.account_id is not None

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        exec_result.raw.account_id,
        setup_accounts["operator_client"].operator_account_id,
    )


@pytest.mark.asynciosetup_accounts
async def test_create_account_with_unlimited_token_associations(setup_accounts):
    """Test creating an account with unlimited automatic token associations."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(max_automatic_token_associations=-1)  # unlimited

    tool: CreateAccountTool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert result.error is None  # check that the response is not an error
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.account_id is not None

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify max automatic token associations
    info = executor_wrapper.get_account_info(str(exec_result.raw.account_id))
    assert info.max_automatic_token_associations == -1  # unlimited is represented as

    # Cleanup created an account
    await return_hbars_and_delete_account(
        executor_wrapper,
        exec_result.raw.account_id,
        setup_accounts["operator_client"].operator_account_id,
    )


@pytest.mark.asyncio
async def test_schedule_create_account_transaction(setup_accounts):
    """Test scheduling a create account transaction with explicit public key."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    public_key: PublicKey = executor_client.operator_private_key.public_key()
    params = CreateAccountParameters(
        public_key=public_key.to_string_der(),
        scheduling_params=SchedulingParams(is_scheduled=True, wait_for_expiry=False),
    )

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert result.error is None  # check that the response is not an error
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.raw.schedule_id is not None
    assert "Scheduled transaction created successfully" in result.human_message


@pytest.mark.asyncio
async def test_fail_with_invalid_public_key(setup_accounts):
    """Test that creation fails with an invalid public key."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(
        public_key="not-a-valid-public-key",
    )

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to create account" in result.human_message


@pytest.mark.asyncio
async def test_fail_with_negative_initial_balance(setup_accounts):
    """Test that creation fails with a negative initial balance."""
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(
        initial_balance=-1,
    )

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to create account" in result.human_message
