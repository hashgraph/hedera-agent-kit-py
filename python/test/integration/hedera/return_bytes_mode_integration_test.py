"""Hedera integration tests for return bytes mode.

This module tests the return bytes mode by creating transactions that return
serialized bytes instead of executing on-chain. Tests use account creation as
the primary use case.
"""

from typing import cast

import pytest
from hiero_sdk_python import (
    PrivateKey,
    Hbar,
    PublicKey,
    Client,
    Transaction,
    TransactionReceipt,
    ResponseCode,
    Network,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS

from hedera_agent_kit.plugins.core_account_plugin import CreateAccountTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ReturnBytesToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParameters,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    """Setup operator and executor accounts for tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])
            ),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.RETURN_BYTES, account_id=str(executor_account_id))

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


@pytest.mark.asyncio
async def test_create_account_returns_bytes(setup_accounts):
    """Test that creating an account in RETURN_BYTES mode returns serialized bytes."""
    executor_client: Client = setup_accounts["executor_client"]
    non_key_executor_client: Client = Client(Network(network="testnet"))
    non_key_executor_client.operator_account_id = setup_accounts[
        "executor_client"
    ].operator_account_id  # set just the account id
    context: Context = setup_accounts["context"]

    assert context.account_id == str(non_key_executor_client.operator_account_id)

    params = CreateAccountParameters()

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Should return ReturnBytesToolResponse, not an error
    assert result.error is None
    bytes_result = cast(ReturnBytesToolResponse, result)

    # Verify we got bytes back
    assert bytes_result.bytes_data is not None
    assert isinstance(bytes_result.bytes_data, bytes)
    assert len(bytes_result.bytes_data) > 0

    # Verify human message contains byte representation
    assert "Transaction bytes:" in bytes_result.human_message

    unsigned_bytes = bytes_result.bytes_data

    # Reconstruct a transaction object from bytes
    tx = Transaction.from_bytes(unsigned_bytes)

    # Sign the transaction with the operator's private key
    tx = tx.sign(executor_client.operator_private_key)

    # Execute the transaction
    receipt: TransactionReceipt = tx.execute(executor_client)
    assert receipt.status == ResponseCode.SUCCESS
    assert receipt.account_id is not None
    assert receipt.transaction_id is not None


@pytest.mark.asyncio
async def test_returned_bytes_can_be_deserialized_and_executed(setup_accounts):
    """Test that returned bytes can be deserialized and executed on-chain."""
    executor_client: Client = setup_accounts["executor_client"]
    non_key_executor_client: Client = Client(Network(network="testnet"))
    non_key_executor_client.operator_account_id = setup_accounts[
        "executor_client"
    ].operator_account_id
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(
        initial_balance=0.05,
        account_memo="Return bytes test account",
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(non_key_executor_client, context, params)

    assert result.error is None
    bytes_result = cast(ReturnBytesToolResponse, result)

    # Deserialize the bytes back into a transaction
    tx = Transaction.from_bytes(bytes_result.bytes_data)

    # Sign the transaction with the operator's private key
    tx = tx.sign(executor_client.operator_private_key)

    # Execute the transaction
    receipt: TransactionReceipt = tx.execute(executor_client)

    # Verify the account was created successfully
    assert receipt.status == ResponseCode.SUCCESS
    assert receipt.account_id is not None
    new_account_id = str(receipt.account_id)

    # Verify balance
    balance = executor_wrapper.get_account_hbar_balance(new_account_id)
    assert balance >= int(0.05 * 1e8)  # tinybars

    # Verify memo
    info = executor_wrapper.get_account_info(new_account_id)
    assert info.account_memo == "Return bytes test account"

    # Cleanup
    await return_hbars_and_delete_account(
        executor_wrapper,
        receipt.account_id,
        setup_accounts["operator_client"].operator_account_id,
    )


@pytest.mark.asyncio
async def test_return_bytes_with_explicit_public_key(setup_accounts):
    """Test return bytes mode with an explicit public key."""
    executor_client: Client = setup_accounts["executor_client"]
    non_key_executor_client: Client = Client(Network(network="testnet"))
    non_key_executor_client.operator_account_id = setup_accounts[
        "executor_client"
    ].operator_account_id
    context: Context = setup_accounts["context"]

    public_key: PublicKey = executor_client.operator_private_key.public_key()
    params = CreateAccountParameters(
        public_key=public_key.to_string_der(),
    )

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(non_key_executor_client, context, params)

    assert result.error is None
    bytes_result = cast(ReturnBytesToolResponse, result)

    # Verify we got bytes back
    assert bytes_result.bytes_data is not None
    assert isinstance(bytes_result.bytes_data, bytes)
    assert len(bytes_result.bytes_data) > 0


@pytest.mark.asyncio
async def test_return_bytes_requires_account_id_in_context(operator_client):
    """Test that RETURN_BYTES mode fails without account_id in context."""
    # Create context without account_id
    context = Context(mode=AgentMode.RETURN_BYTES, account_id=None)

    params = CreateAccountParameters()

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(operator_client, context, params)

    # Should contain error message
    assert result.error is not None
    assert "Context account_id is required" in result.error


@pytest.mark.asyncio
async def test_return_bytes_with_unlimited_token_associations(setup_accounts):
    """Test return bytes mode with unlimited automatic token associations."""
    non_key_executor_client: Client = Client(Network(network="testnet"))
    non_key_executor_client.operator_account_id = setup_accounts[
        "executor_client"
    ].operator_account_id
    context: Context = setup_accounts["context"]

    params = CreateAccountParameters(max_automatic_token_associations=-1)

    tool = CreateAccountTool(context)
    result: ToolResponse = await tool.execute(non_key_executor_client, context, params)

    assert result.error is None
    bytes_result = cast(ReturnBytesToolResponse, result)

    # Verify we got bytes back
    assert bytes_result.bytes_data is not None
    assert isinstance(bytes_result.bytes_data, bytes)

    # Deserialize and verify the transaction contains the correct settings
    deserialized_tx = Transaction.from_bytes(bytes_result.bytes_data)
    assert deserialized_tx is not None
