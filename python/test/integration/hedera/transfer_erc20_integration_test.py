"""Integration tests for transfer_erc20 tool with Hedera network."""

import pytest
from typing import cast
from hiero_sdk_python import PrivateKey, Hbar

from hedera_agent_kit_py.plugins.core_evm_plugin import TransferERC20Tool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import AccountResponse
from hedera_agent_kit_py.shared.models import ToolResponse, ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferERC20Parameters,
    CreateERC20Parameters, SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils import wait
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_transfer_erc20():
    """Setup test environment with ERC20 token and accounts."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account (token creator and sender)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Create test ERC20 token with initial supply
    create_params = CreateERC20Parameters(
        token_name="TestTransferToken",
        token_symbol="TTT",
        decimals=18,
        initial_supply=1000,
    )

    create_result = await executor_wrapper.create_erc20(create_params)

    if not create_result.get("erc20_address"):
        raise Exception("Failed to create test ERC20 token")

    test_token_address = create_result["erc20_address"]

    print(f"Test ERC20 token address: {test_token_address}")

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "context": context,
        "test_token_address": test_token_address,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


async def create_recipient_account(wrapper: HederaOperationsWrapper):
    """Helper to create a recipient account."""
    resp = await wrapper.create_account(
        CreateAccountParametersNormalised(key=wrapper.client.operator_private_key.public_key(), initial_balance=Hbar(5))
    )
    return resp.account_id


@pytest.mark.asyncio
async def test_transfer_tokens_to_hedera_address(setup_transfer_erc20):
    """Test transferring ERC20 tokens to a Hedera address."""
    executor_client = setup_transfer_erc20["executor_client"]
    executor_wrapper = setup_transfer_erc20["executor_wrapper"]
    context = setup_transfer_erc20["context"]
    test_token_address = setup_transfer_erc20["test_token_address"]

    # Create recipient account
    recipient_account_id = await create_recipient_account(executor_wrapper)

    await wait(MIRROR_NODE_WAITING_TIME)

    params = TransferERC20Parameters(
        contract_id=test_token_address,
        recipient_address=str(recipient_account_id),
        amount=10,
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert exec_result.raw.transaction_id is not None
    assert "successfully" in exec_result.human_message.lower()

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_transfer_tokens_using_evm_addresses(setup_transfer_erc20):
    """Test transferring ERC20 tokens using EVM addresses."""
    executor_client = setup_transfer_erc20["executor_client"]
    executor_wrapper = setup_transfer_erc20["executor_wrapper"]
    context = setup_transfer_erc20["context"]
    test_token_address = setup_transfer_erc20["test_token_address"]

    # Create recipient account and get its EVM address
    recipient_account_id = await create_recipient_account(executor_wrapper)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Get EVM address for the recipient
    recipient_info: AccountResponse = await executor_wrapper.get_account_info_mirrornode(str(recipient_account_id))
    recipient_evm_address = recipient_info.get("evm_address", None)
    assert (
        recipient_evm_address is not None
    ), f"Failed to get EVM address for recipient account {recipient_account_id}"

    params = TransferERC20Parameters(
        contract_id=test_token_address,
        recipient_address=recipient_evm_address,
        amount=5,
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert exec_result.raw.transaction_id is not None

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_schedule_transfer_erc20_tokens(setup_transfer_erc20):
    """Test scheduling a transfer of ERC20 tokens."""
    executor_client = setup_transfer_erc20["executor_client"]
    executor_wrapper = setup_transfer_erc20["executor_wrapper"]
    context = setup_transfer_erc20["context"]
    test_token_address = setup_transfer_erc20["test_token_address"]

    # Create a recipient account
    recipient_account_id = await create_recipient_account(executor_wrapper)

    await wait(MIRROR_NODE_WAITING_TIME)

    params = TransferERC20Parameters(
        contract_id=test_token_address,
        recipient_address=str(recipient_account_id),
        amount=10,
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert "scheduled transfer of erc20 successfully" in exec_result.human_message.lower()
    assert exec_result.raw.schedule_id is not None

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )

@pytest.mark.asyncio
async def test_fail_when_contract_id_invalid(setup_transfer_erc20):
    """Test that transfer fails when contractId is invalid."""
    executor_client = setup_transfer_erc20["executor_client"]
    executor_wrapper = setup_transfer_erc20["executor_wrapper"]
    context = setup_transfer_erc20["context"]

    recipient_account_id = await create_recipient_account(executor_wrapper)

    params = TransferERC20Parameters(
        contract_id="invalid-contract-id",
        recipient_address=str(recipient_account_id),
        amount=10,
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed to transfer erc20" in result.human_message.lower()

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_fail_when_amount_negative(setup_transfer_erc20):
    """Test that transfer fails when amount is negative."""
    executor_client = setup_transfer_erc20["executor_client"]
    executor_wrapper = setup_transfer_erc20["executor_wrapper"]
    context = setup_transfer_erc20["context"]
    test_token_address = setup_transfer_erc20["test_token_address"]

    recipient_account_id = await create_recipient_account(executor_wrapper)

    params = TransferERC20Parameters(
        contract_id=test_token_address,
        recipient_address=str(recipient_account_id),
        amount=-10,
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed to transfer erc20" in result.human_message.lower()

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_fail_when_recipient_address_invalid(setup_transfer_erc20):
    """Test that transfer fails when recipientAddress is invalid."""
    executor_client = setup_transfer_erc20["executor_client"]
    context = setup_transfer_erc20["context"]
    test_token_address = setup_transfer_erc20["test_token_address"]

    params = TransferERC20Parameters(
        contract_id=test_token_address,
        recipient_address="invalid-address",
        amount=10,
    )

    tool = TransferERC20Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed to transfer erc20" in result.human_message.lower()
