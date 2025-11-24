import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python import Client, Network, TokenId
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    MintFungibleTokenParameters,
    MintFungibleTokenParametersNormalised,
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


@pytest.fixture
def mock_mirrornode():
    """Provide a mock Mirror Node service."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_normalise_mint_token_calculates_base_units(
    mock_context, mock_client, mock_mirrornode
):
    """Should correctly convert amount to base units using decimals from mirror node."""
    # Setup mirror node response
    mock_mirrornode.get_token_info.return_value = {"decimals": "3"}

    # Amount: 10.5, Decimals: 3 -> 10500
    params = MintFungibleTokenParameters(token_id="0.0.5678", amount=10.5)

    result = await HederaParameterNormaliser.normalise_mint_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert isinstance(result, MintFungibleTokenParametersNormalised)
    assert isinstance(result.token_id, TokenId)
    assert str(result.token_id) == "0.0.5678"
    assert result.amount == 10500

    mock_mirrornode.get_token_info.assert_called_once_with("0.0.5678")


@pytest.mark.asyncio
async def test_normalise_mint_token_zero_decimals(
    mock_context, mock_client, mock_mirrornode
):
    """Should handle tokens with 0 decimals correctly."""
    mock_mirrornode.get_token_info.return_value = {"decimals": "0"}

    params = MintFungibleTokenParameters(token_id="0.0.1234", amount=500.0)

    result = await HederaParameterNormaliser.normalise_mint_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert result.amount == 500


@pytest.mark.asyncio
async def test_raises_value_error_if_decimals_missing(
    mock_context, mock_client, mock_mirrornode
):
    """Should raise ValueError if mirror node response lacks decimals."""
    mock_mirrornode.get_token_info.return_value = {}  # No decimals field

    params = MintFungibleTokenParameters(token_id="0.0.9999", amount=10.0)

    with pytest.raises(ValueError, match="Unable to retrieve token decimals"):
        await HederaParameterNormaliser.normalise_mint_fungible_token_params(
            params, mock_context, mock_client, mock_mirrornode
        )


@pytest.mark.asyncio
async def test_processes_scheduling_params(mock_context, mock_client, mock_mirrornode):
    """Should normalize scheduling parameters if is_scheduled is True."""
    mock_mirrornode.get_token_info.return_value = {"decimals": "2"}
    mock_sched_return = ScheduleCreateParams(wait_for_expiry=True)

    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        new_callable=AsyncMock,
        return_value=mock_sched_return,
    ) as mock_sched_norm:
        scheduling_input = SchedulingParams(is_scheduled=True)
        params = MintFungibleTokenParameters(
            token_id="0.0.777", amount=100.0, scheduling_params=scheduling_input
        )

        result = await HederaParameterNormaliser.normalise_mint_fungible_token_params(
            params, mock_context, mock_client, mock_mirrornode
        )

        assert result.scheduling_params == mock_sched_return
        mock_sched_norm.assert_called_once_with(
            scheduling_input, mock_context, mock_client
        )
