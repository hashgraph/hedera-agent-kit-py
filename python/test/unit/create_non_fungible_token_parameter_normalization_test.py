import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python import (
    Client,
    PrivateKey,
    Network,
    AccountId,
    SupplyType,
    TokenType,
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParameters,
    CreateNonFungibleTokenParametersNormalised,
    TokenParams,
)
from hedera_agent_kit.shared.parameter_schemas import SchedulingParams

# Test constants
TEST_OPERATOR_ID = "0.0.1001"
TEST_PRIVATE_KEY = PrivateKey.generate_ed25519()
TEST_PUBLIC_KEY = TEST_PRIVATE_KEY.public_key()
TEST_MIRROR_KEY_STR = PrivateKey.generate_ed25519().public_key().to_string_der()


@pytest.fixture
def mock_context():
    return Context(account_id=TEST_OPERATOR_ID)


@pytest.fixture
def mock_client():
    client = MagicMock(spec=Client)
    client.operator_account_id = AccountId.from_string(TEST_OPERATOR_ID)
    client.operator_private_key = TEST_PRIVATE_KEY
    client.network = Network(network="testnet")
    return client


@pytest.fixture
def mock_mirrornode():
    service = AsyncMock()
    # Default behavior: return empty account info (no key found)
    service.get_account = AsyncMock(return_value={})
    return service


@pytest.mark.asyncio
async def test_normalise_create_non_fungible_token_defaults(
    mock_context, mock_client, mock_mirrornode
):
    """Should use correct defaults: FINITE supply type by default, supply key always set."""
    params = CreateNonFungibleTokenParameters(
        token_name="NFT Token",
        token_symbol="NFT",
        # No max_supply or supply_type provided - should default to FINITE with max_supply=100
    )

    result = await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert isinstance(result, CreateNonFungibleTokenParametersNormalised)
    assert isinstance(result.token_params, TokenParams)

    # Check token params
    tp = result.token_params
    assert tp.token_name == "NFT Token"
    assert tp.token_symbol == "NFT"
    assert tp.token_type == TokenType.NON_FUNGIBLE_UNIQUE

    # Defaults to FINITE when supply_type is not explicitly set
    assert tp.supply_type == SupplyType.FINITE
    assert tp.max_supply == 100  # Default max supply for FINITE NFTs

    assert str(tp.treasury_account_id) == TEST_OPERATOR_ID
    assert str(tp.auto_renew_account_id) == TEST_OPERATOR_ID

    # Supply key is always set for NFTs (required for minting)
    assert result.keys is not None
    assert result.keys.supply_key.to_string_der() == TEST_PUBLIC_KEY.to_string_der()
    assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_normalise_explicit_finite_values(
    mock_context, mock_client, mock_mirrornode
):
    """Should set supply_type to FINITE and use provided max_supply."""
    params = CreateNonFungibleTokenParameters(
        token_name="My NFT",
        token_symbol="MNFT",
        supply_type=1,  # Explicitly FINITE
        max_supply=500,
        treasury_account_id=TEST_OPERATOR_ID,
    )

    result = await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    tp = result.token_params
    assert tp.token_name == "My NFT"
    assert tp.token_symbol == "MNFT"
    assert tp.supply_type == SupplyType.FINITE
    assert tp.max_supply == 500
    assert str(tp.treasury_account_id) == TEST_OPERATOR_ID


@pytest.mark.asyncio
async def test_normalise_explicit_infinite_supply(
    mock_context, mock_client, mock_mirrornode
):
    """Should set supply_type to INFINITE when explicitly requested."""
    params = CreateNonFungibleTokenParameters(
        token_name="Infinite NFT",
        token_symbol="INFT",
        supply_type=0,  # Explicitly INFINITE
    )

    result = await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    tp = result.token_params
    assert tp.token_name == "Infinite NFT"
    assert tp.token_symbol == "INFT"
    assert tp.supply_type == SupplyType.INFINITE
    assert tp.max_supply == 0


@pytest.mark.asyncio
async def test_validates_max_supply_with_infinite_type(
    mock_context, mock_client, mock_mirrornode
):
    """Should raise ValueError if max_supply is set with INFINITE supply type."""
    params = CreateNonFungibleTokenParameters(
        token_name="Invalid NFT",
        token_symbol="INV",
        supply_type=0,  # INFINITE
        max_supply=100,  # Conflicting with INFINITE
    )

    with pytest.raises(ValueError, match="Cannot set max supply and INFINITE supply type"):
        await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
            params, mock_context, mock_client, mock_mirrornode
        )


@pytest.mark.asyncio
async def test_raises_error_if_supply_key_cannot_be_resolved(
    mock_context, mock_mirrornode
):
    """Should raise ValueError if supply key cannot be resolved (no operator key)."""
    # Setup client without operator key
    client = MagicMock(spec=Client)
    client.operator_account_id = AccountId.from_string(TEST_OPERATOR_ID)
    client.operator_private_key = None  # No operator key
    client.network = Network(network="testnet")

    # Setup mirror node to fail
    mock_mirrornode.get_account.side_effect = Exception("Mirror node offline")

    params = CreateNonFungibleTokenParameters(
        token_name="No Key NFT",
        token_symbol="NKNFT",
    )

    with pytest.raises(ValueError, match="Could not resolve a Supply Key"):
        await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
            params, mock_context, client, mock_mirrornode
        )


@pytest.mark.asyncio
async def test_resolves_treasury_key_from_mirrornode(
    mock_context, mock_client, mock_mirrornode
):
    """Should fetch the treasury account's key from mirror node."""
    # Setup mirror node to return a specific key
    mock_mirrornode.get_account.return_value = {
        "account_public_key": TEST_MIRROR_KEY_STR
    }

    params = CreateNonFungibleTokenParameters(
        token_name="Key NFT",
        token_symbol="KNFT",
        treasury_account_id=TEST_OPERATOR_ID,
    )

    result = await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    mock_mirrornode.get_account.assert_called_once_with(TEST_OPERATOR_ID)
    assert result.keys is not None
    assert result.keys.supply_key.to_string_der() == TEST_MIRROR_KEY_STR


@pytest.mark.asyncio
async def test_falls_back_to_operator_key_if_mirror_fails(
    mock_context, mock_client, mock_mirrornode
):
    """Should fall back to client operator key if mirror node lookup fails."""
    # Setup mirror node to fail
    mock_mirrornode.get_account.side_effect = Exception("Mirror node offline")

    params = CreateNonFungibleTokenParameters(
        token_name="Fallback NFT",
        token_symbol="FNFT",
    )

    result = await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    # It tried the mirror node
    mock_mirrornode.get_account.assert_called()
    # It fell back to the client operator key
    assert result.keys is not None
    assert result.keys.supply_key.to_string_der() == TEST_PUBLIC_KEY.to_string_der()


@pytest.mark.asyncio
async def test_process_scheduling_params(mock_context, mock_client, mock_mirrornode):
    """Should process scheduling params if is_scheduled is True."""
    mock_sched_return = ScheduleCreateParams(wait_for_expiry=True)

    # Spy on the scheduling normalizer
    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        new_callable=AsyncMock,
        return_value=mock_sched_return,
    ) as mock_sched_norm:
        scheduling_input = SchedulingParams(is_scheduled=True)
        params = CreateNonFungibleTokenParameters(
            token_name="Sched NFT",
            token_symbol="SNFT",
            scheduling_params=scheduling_input,
        )

        result = (
            await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
                params, mock_context, mock_client, mock_mirrornode
            )
        )

        mock_sched_norm.assert_called_once_with(
            scheduling_input, mock_context, mock_client
        )
        assert result.scheduling_params == mock_sched_return
