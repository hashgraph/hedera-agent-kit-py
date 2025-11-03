from decimal import Decimal

import pytest
from hiero_sdk_python import PrivateKey, Hbar

from hedera_agent_kit_py.plugins.core_account_plugin import TransferHbarTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferHbarParameters,
    TransferHbarEntry,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5, in_tinybars=False),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Create recipients
    recipient_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=0, key=operator_client.operator_private_key.public_key()
        )
    )
    recipient_account_id = recipient_resp.account_id

    recipient_resp2 = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=0, key=operator_client.operator_private_key.public_key()
        )
    )
    recipient_account_id2 = recipient_resp2.account_id

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "operator_wrapper": operator_wrapper,
        "recipient_account_id": recipient_account_id,
        "recipient_account_id2": recipient_account_id2,
        "context": context,
    }

    # Cleanup
    await return_hbars_and_delete_account(
        operator_wrapper, recipient_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        operator_wrapper, recipient_account_id2, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )

    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_single_hbar_transfer(setup_accounts):
    w = setup_accounts["executor_wrapper"]
    executor_client = setup_accounts["executor_client"]
    recipient = setup_accounts["recipient_account_id"]
    context = setup_accounts["context"]

    balance_before = w.get_account_hbar_balance(str(recipient))
    amount = 0.1

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transaction_memo="Integration test transfer",
        transfers=[
            TransferHbarEntry(account_id=str(recipient), amount=amount)
        ],  # passed in Hbars
    )
    await tool.execute(executor_client, context, params)

    balance_after = w.get_account_hbar_balance(str(recipient))
    assert balance_after - balance_before == to_tinybars(Decimal(amount))


@pytest.mark.asyncio
async def test_multiple_hbar_transfer(setup_accounts):
    w = setup_accounts["executor_wrapper"]
    executor_client = setup_accounts["executor_client"]
    recipient1 = setup_accounts["recipient_account_id"]
    recipient2 = setup_accounts["recipient_account_id2"]
    context = setup_accounts["context"]

    balance_before1 = w.get_account_hbar_balance(str(recipient1))
    balance_before2 = w.get_account_hbar_balance(str(recipient2))

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transaction_memo="Multi-recipient transfer",
        transfers=[
            TransferHbarEntry(account_id=str(recipient1), amount=0.05),
            TransferHbarEntry(account_id=str(recipient2), amount=0.05),
        ],
    )
    await tool.execute(executor_client, context, params)

    balance_after1 = w.get_account_hbar_balance(str(recipient1))
    balance_after2 = w.get_account_hbar_balance(str(recipient2))
    assert balance_after1 - balance_before1 == to_tinybars(Decimal(0.05))
    assert balance_after2 - balance_before2 == to_tinybars(Decimal(0.05))


@pytest.mark.asyncio
async def test_transfer_with_explicit_source(setup_accounts):
    w = setup_accounts["executor_wrapper"]
    executor_client = setup_accounts["executor_client"]
    recipient = setup_accounts["recipient_account_id"]
    context = setup_accounts["context"]

    balance_before = w.get_account_hbar_balance(str(recipient))
    amount = 0.1

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transaction_memo="Explicit source transfer",
        source_account_id=str(executor_client.operator_account_id),
        transfers=[TransferHbarEntry(account_id=str(recipient), amount=amount)],
    )
    await tool.execute(executor_client, context, params)

    balance_after = w.get_account_hbar_balance(str(recipient))
    assert balance_after - balance_before == to_tinybars(Decimal(amount))


@pytest.mark.asyncio
async def test_transfer_without_memo(setup_accounts):
    w = setup_accounts["executor_wrapper"]
    executor_client = setup_accounts["executor_client"]
    recipient = setup_accounts["recipient_account_id"]
    context = setup_accounts["context"]

    balance_before = w.get_account_hbar_balance(str(recipient))
    amount = 0.05

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[TransferHbarEntry(account_id=str(recipient), amount=amount)]
    )
    await tool.execute(executor_client, context, params)

    balance_after = w.get_account_hbar_balance(str(recipient))
    assert balance_after - balance_before == to_tinybars(Decimal(amount))


@pytest.mark.asyncio
async def test_invalid_transfer_zero_amount(setup_accounts):
    executor_client = setup_accounts["executor_client"]
    recipient = setup_accounts["recipient_account_id"]
    context = setup_accounts["context"]

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[TransferHbarEntry(account_id=str(recipient), amount=0)]
    )
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Failed to transfer HBAR" in result.error
