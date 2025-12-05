"""Integration tests for GetHbarBalanceTool.

This test verifies on-chain balance querying via Hedera mirror node using
the Hedera Agent Kit. It covers successful balance retrieval, default account
fallback, and error handling for non-existent accounts.
"""

import pytest
from decimal import Decimal

from hiero_sdk_python import Client, PrivateKey, Hbar

from hedera_agent_kit.plugins.core_account_query_plugin import GetHbarBalanceTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    AccountBalanceQueryParameters,
    CreateAccountParametersNormalised,
    DeleteAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)


@pytest.fixture(scope="module")
async def setup_environment():
    """Setup operator and executor clients for balance query tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(5, in_tinybars=False)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Create recipient account via executor
    recipient_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(1, in_tinybars=False)
        )
    )
    recipient_account_id = recipient_resp.account_id

    await wait(MIRROR_NODE_WAITING_TIME)

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

    # Cleanup: delete recipient and executor
    await executor_wrapper.delete_account(
        DeleteAccountParametersNormalised(
            account_id=recipient_account_id, transfer_account_id=executor_account_id
        )
    )
    await executor_wrapper.delete_account(
        DeleteAccountParametersNormalised(
            account_id=executor_account_id,
            transfer_account_id=operator_client.operator_account_id,
        )
    )

    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_get_balance_for_recipient_account(setup_environment):
    """Test retrieving HBAR balance for a specific account."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    recipient_account_id = setup_environment["recipient_account_id"]

    params = AccountBalanceQueryParameters(account_id=str(recipient_account_id))
    tool = GetHbarBalanceTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)
    assert "HBAR Balance" in result.human_message
    assert "tinybars" in result.human_message
    assert not result.error

    # Balance should match 1 HBAR
    assert Decimal(result.extra["balance"]) == Decimal("100000000")


@pytest.mark.asyncio
async def test_get_balance_default_executor_account(setup_environment):
    """Test querying balance with no account_id provided (uses default from context)."""
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    context: Context = setup_environment["context"]

    params = AccountBalanceQueryParameters()
    expected_balance = executor_wrapper.get_account_hbar_balance(
        str(executor_account_id)
    )

    tool = GetHbarBalanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "HBAR Balance" in result.human_message
    assert str(executor_account_id) in result.human_message
    assert Decimal(result.extra["balance"]) == expected_balance


@pytest.mark.asyncio
async def test_get_balance_non_existent_account(setup_environment):
    """Test querying a non-existent account and expecting a failure response."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    non_existent_account_id = "0.0.999999999999"
    params = AccountBalanceQueryParameters(account_id=non_existent_account_id)
    tool = GetHbarBalanceTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Failed to get HBAR balance" in result.human_message
    assert result.error is not None
