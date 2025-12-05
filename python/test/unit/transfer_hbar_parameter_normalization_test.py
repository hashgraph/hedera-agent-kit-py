from decimal import Decimal
from unittest.mock import AsyncMock, patch
import pytest
from hiero_sdk_python import AccountId

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit.shared.hedera_utils import to_tinybars
from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarEntry,
)


# Helper to create TransferHbarParameters instances
def make_params(transfers, memo=None, source_account_id="0.0.1001", is_scheduled=False):
    entries = [
        TransferHbarEntry(account_id=t["account_id"], amount=t["amount"])
        for t in transfers
    ]
    scheduling_params = {"isScheduled": is_scheduled} if is_scheduled else None
    return TransferHbarParameters(
        source_account_id=source_account_id,
        transfers=entries,
        transaction_memo=memo,
        scheduling_params=scheduling_params,
    )


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_single_transfer(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    params = make_params([{"account_id": "0.0.1002", "amount": 10}], "Test transfer")
    result = await HederaParameterNormaliser.normalise_transfer_hbar(
        params, mock_context, mock_client
    )

    assert len(result.hbar_transfers) == 2

    recipient_transfer = result.hbar_transfers[AccountId.from_string("0.0.1002")]
    source_transfer = result.hbar_transfers[AccountId.from_string(source_account_id)]

    assert recipient_transfer == to_tinybars(Decimal(10))
    assert source_transfer == -to_tinybars(Decimal(10))
    assert result.transaction_memo == "Test transfer"

    mock_resolve.assert_called_once_with(source_account_id, mock_context, mock_client)


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_multiple_transfers(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    transfers = [
        {"account_id": "0.0.1002", "amount": 5},
        {"account_id": "0.0.1003", "amount": 15},
        {"account_id": "0.0.1004", "amount": 2.5},
    ]
    params = make_params(transfers, "Multiple transfers")
    result = await HederaParameterNormaliser.normalise_transfer_hbar(
        params, mock_context, mock_client
    )

    assert len(result.hbar_transfers) == 4

    for t, expected in zip(transfers, [5, 15, 2.5]):
        amt = result.hbar_transfers[AccountId.from_string(t["account_id"])]
        assert amt == to_tinybars(Decimal(expected))

    total = sum(to_tinybars(Decimal(t["amount"])) for t in transfers)
    source_amt = result.hbar_transfers[AccountId.from_string(source_account_id)]
    assert source_amt == -total


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_fractional_and_small_amount(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    small_amount = Decimal("0.00000001")
    params = make_params([{"account_id": "0.0.1002", "amount": small_amount}])
    result = await HederaParameterNormaliser.normalise_transfer_hbar(
        params, mock_context, mock_client
    )

    recipient_transfer = result.hbar_transfers[AccountId.from_string("0.0.1002")]
    source_transfer = result.hbar_transfers[AccountId.from_string(source_account_id)]

    assert recipient_transfer == 1
    assert source_transfer == -1


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_invalid_transfer_amounts(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    for invalid_amount in [-5, 0]:
        params = make_params([{"account_id": "0.0.1002", "amount": invalid_amount}])
        with pytest.raises(
            ValueError, match=f"Invalid transfer amount: {invalid_amount}"
        ):
            await HederaParameterNormaliser.normalise_transfer_hbar(
                params, mock_context, mock_client
            )

    params = make_params(
        [
            {"account_id": "0.0.1002", "amount": 5},
            {"account_id": "0.0.1003", "amount": -2},
            {"account_id": "0.0.1004", "amount": 3},
        ]
    )
    with pytest.raises(ValueError, match="Invalid transfer amount: -2"):
        await HederaParameterNormaliser.normalise_transfer_hbar(
            params, mock_context, mock_client
        )


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_transfer_without_memo(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    params = make_params([{"account_id": "0.0.1002", "amount": 1}])
    result = await HederaParameterNormaliser.normalise_transfer_hbar(
        params, mock_context, mock_client
    )

    assert result.transaction_memo is None


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
async def test_total_transfers_sum_to_zero(mock_resolve):
    mock_context = Context()
    mock_client = AsyncMock()
    source_account_id = "0.0.1001"
    mock_resolve.return_value = source_account_id

    transfers = [
        {"account_id": "0.0.1002", "amount": 10},
        {"account_id": "0.0.1003", "amount": 5},
        {"account_id": "0.0.1004", "amount": 15},
    ]
    params = make_params(transfers)
    result = await HederaParameterNormaliser.normalise_transfer_hbar(
        params, mock_context, mock_client
    )

    total = sum(result.hbar_transfers.values())
    assert total == 0
