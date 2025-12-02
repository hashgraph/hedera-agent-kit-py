import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python import Client, Network, TokenId
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    MintNonFungibleTokenParameters,
    MintNonFungibleTokenParametersNormalised,
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
async def test_normalise_mint_nft_encodes_uris(mock_context, mock_client):
    """Should correctly encode URIs into bytes."""
    params = MintNonFungibleTokenParameters(
        token_id="0.0.1234", uris=["ipfs://abc123", "https://example.com/meta.json"]
    )

    result = await HederaParameterNormaliser.normalise_mint_non_fungible_token_params(
        params, mock_context, mock_client
    )

    assert isinstance(result, MintNonFungibleTokenParametersNormalised)
    assert isinstance(result.token_id, TokenId)
    assert str(result.token_id) == "0.0.1234"
    assert len(result.metadata) == 2
    assert result.metadata[0].decode() == "ipfs://abc123"
    assert result.metadata[1].decode() == "https://example.com/meta.json"


@pytest.mark.asyncio
async def test_normalise_mint_nft_empty_uris(mock_context, mock_client):
    """Should handle empty URIs list."""
    params = MintNonFungibleTokenParameters(token_id="0.0.5678", uris=[])

    result = await HederaParameterNormaliser.normalise_mint_non_fungible_token_params(
        params, mock_context, mock_client
    )

    assert str(result.token_id) == "0.0.5678"
    assert result.metadata == []


@pytest.mark.asyncio
async def test_processes_scheduling_params(mock_context, mock_client):
    """Should normalize scheduling parameters if is_scheduled is True."""
    mock_sched_return = ScheduleCreateParams(wait_for_expiry=True)

    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        new_callable=AsyncMock,
        return_value=mock_sched_return,
    ) as mock_sched_norm:
        scheduling_input = SchedulingParams(is_scheduled=True)
        params = MintNonFungibleTokenParameters(
            token_id="0.0.9999",
            uris=["ipfs://scheduled"],
            scheduling_params=scheduling_input,
        )

        result = (
            await HederaParameterNormaliser.normalise_mint_non_fungible_token_params(
                params, mock_context, mock_client
            )
        )

        assert result.scheduling_params == mock_sched_return
        mock_sched_norm.assert_called_once_with(
            scheduling_input, mock_context, mock_client
        )
