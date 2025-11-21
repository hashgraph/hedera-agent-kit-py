import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from hiero_sdk_python import Client, Hbar, Network
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransferHbarWithAllowanceParameters,
    TransferHbarWithAllowanceParametersNormalised,
    TransferHbarEntry,
    SchedulingParams,
)


@pytest.fixture
def mock_context():
    """Provide a mock Context."""
    return Context(account_id="0.0.1001")


@pytest.fixture
def mock_client():
    """Provide a mock Client instance."""
    mock = MagicMock(spec=Client)
    mock.network = Network(network="testnet")
    return mock


@pytest.mark.asyncio
async def test_normalise_single_transfer_with_allowance(mock_context, mock_client):
    """Should normalize a single HBAR transfer with allowance correctly."""
    source_id = "0.0.1001"
    recipient_id = "0.0.1002"
    amount = 10.0

    params = TransferHbarWithAllowanceParameters(
        source_account_id=source_id,
        transfers=[TransferHbarEntry(account_id=recipient_id, amount=amount)],
        transaction_memo="Test transfer",
    )

    result = await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
        params, mock_context, mock_client
    )

    assert isinstance(result, TransferHbarWithAllowanceParametersNormalised)
    assert result.transaction_memo == "Test transfer"
    assert result.scheduling_params is None

    # Convert keys to strings for easier assertion (keys are AccountId objects)
    transfers_map = {str(k): v for k, v in result.hbar_approved_transfers.items()}

    # Check recipient receives positive tinybars
    assert transfers_map[recipient_id] == Hbar(amount).to_tinybars()
    # Check owner has negative total tinybars deducted
    assert transfers_map[source_id] == -Hbar(amount).to_tinybars()


@pytest.mark.asyncio
async def test_normalise_multiple_recipients_with_allowance(mock_context, mock_client):
    """Should handle multiple recipient transfers correctly."""
    source_id = "0.0.1001"
    recip1 = "0.0.2002"
    recip2 = "0.0.3003"
    amt1 = 5.0
    amt2 = 7.0

    params = TransferHbarWithAllowanceParameters(
        source_account_id=source_id,
        transfers=[
            TransferHbarEntry(account_id=recip1, amount=amt1),
            TransferHbarEntry(account_id=recip2, amount=amt2),
        ],
    )

    result = await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
        params, mock_context, mock_client
    )

    transfers_map = {str(k): v for k, v in result.hbar_approved_transfers.items()}

    # Check recipients
    assert transfers_map[recip1] == Hbar(amt1).to_tinybars()
    assert transfers_map[recip2] == Hbar(amt2).to_tinybars()

    # Check owner deduction (sum of amounts, negative)
    total_deduction = Hbar(amt1).to_tinybars() + Hbar(amt2).to_tinybars()
    assert transfers_map[source_id] == -total_deduction


@pytest.mark.asyncio
async def test_raises_value_error_if_source_account_missing(mock_context, mock_client):
    """Should raise ValueError if source_account_id is missing."""
    params = TransferHbarWithAllowanceParameters(
        source_account_id=None,
        transfers=[TransferHbarEntry(account_id="0.0.1002", amount=10)],
    )

    with pytest.raises(
        ValueError, match="source_account_id is required for allowance transfers"
    ):
        await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
            params, mock_context, mock_client
        )


@pytest.mark.asyncio
async def test_raises_value_error_on_invalid_amounts(mock_context, mock_client):
    """Should throw on zero or negative amount."""
    source_id = "0.0.1001"
    recipient = "0.0.1002"

    # Case 1: Zero amount
    params_zero = TransferHbarWithAllowanceParameters(
        source_account_id=source_id,
        transfers=[TransferHbarEntry(account_id=recipient, amount=0)],
    )
    with pytest.raises(ValueError, match="Invalid transfer amount"):
        await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
            params_zero, mock_context, mock_client
        )

    # Case 2: Negative amount
    params_neg = TransferHbarWithAllowanceParameters(
        source_account_id=source_id,
        transfers=[TransferHbarEntry(account_id=recipient, amount=-5)],
    )
    with pytest.raises(ValueError, match="Invalid transfer amount"):
        await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
            params_neg, mock_context, mock_client
        )


@pytest.mark.asyncio
async def test_processes_scheduling_params(mock_context, mock_client):
    """Should normalize scheduling parameters if is_scheduled is True."""
    mock_sched_return = ScheduleCreateParams(wait_for_expiry=True)

    # Spy on the scheduling normalizer
    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        new_callable=AsyncMock,
        return_value=mock_sched_return,
    ) as mock_sched_norm:
        scheduling_input = SchedulingParams(is_scheduled=True)

        params = TransferHbarWithAllowanceParameters(
            source_account_id="0.0.1001",
            transfers=[TransferHbarEntry(account_id="0.0.1002", amount=10)],
            scheduling_params=scheduling_input,
        )

        result = await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
            params, mock_context, mock_client
        )

        mock_sched_norm.assert_called_once_with(
            scheduling_input, mock_context, mock_client
        )
        assert result.scheduling_params == mock_sched_return
