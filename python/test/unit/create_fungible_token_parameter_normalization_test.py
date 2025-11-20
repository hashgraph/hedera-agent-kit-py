import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python import (
    Client,
    PrivateKey,
    Network,
    AccountId,
    SupplyType,
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    CreateFungibleTokenParameters,
    CreateFungibleTokenParametersNormalised,
    TokenParams,
)
from hedera_agent_kit_py.shared.parameter_schemas import SchedulingParams

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
async def test_normalise_create_fungible_token_defaults(
    mock_context, mock_client, mock_mirrornode
):
    """Should use correct defaults for minimal input (Infinite supply, operator treasury)."""
    params = CreateFungibleTokenParameters(
        token_name="Test Token",
        token_symbol="TEST",
        decimals=2,
        initial_supply=100,
    )

    result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert isinstance(result, CreateFungibleTokenParametersNormalised)
    assert isinstance(result.token_params, TokenParams)

    # Check token params
    tp = result.token_params
    assert tp.token_name == "Test Token"
    assert tp.token_symbol == "TEST"
    assert tp.decimals == 2
    assert tp.initial_supply == 10000
    assert str(tp.treasury_account_id) == TEST_OPERATOR_ID
    assert str(tp.auto_renew_account_id) == TEST_OPERATOR_ID
    assert tp.supply_type == SupplyType.FINITE
    assert (
        tp.max_supply == 100000000
    )  # 10^6 * 10^decimals = default max supply for finite

    # Keys should be None by default for Infinite supply if is_supply_key not set
    assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_normalise_finite_supply_logic_and_math(
    mock_context, mock_client, mock_mirrornode
):
    """
    Should enforce FINITE supply if max_supply is provided,
    calculate decimals correctly, and apply the 'initial supply 0 -> 1' fix.
    """
    params = CreateFungibleTokenParameters(
        token_name="Finite Token",
        token_symbol="FIN",
        decimals=3,
        initial_supply=0,  # Should be bumped to 1
        max_supply=500,  # Triggers FINITE type
    )

    result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    tp = result.token_params
    assert tp.supply_type == SupplyType.FINITE

    # Max supply: 500 * 10^3 = 500000
    assert tp.max_supply == 500000

    # Initial supply: Input was 0, but logic forces 1 * 10^decimals for Finite
    # 1 * 10^3 = 1000
    assert tp.initial_supply == 1000

    # Finite supply implies a supply key is needed (defaulting to operator here)
    assert result.keys is not None
    assert result.keys.supply_key.to_string_der() == TEST_PUBLIC_KEY.to_string_der()


@pytest.mark.asyncio
async def test_normalise_explicit_finite_supply_defaults(
    mock_context, mock_client, mock_mirrornode
):
    """
    Should default max_supply to 1,000,000 if supply_type is explicitly FINITE
    but max_supply is missing.
    """
    params = CreateFungibleTokenParameters(
        token_name="Explicit Finite",
        token_symbol="EXP",
        decimals=0,
        supply_type=1,  # 1 = FINITE (or use TokenSupplyType.FINITE)
        initial_supply=50,
    )

    result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    tp = result.token_params
    assert tp.supply_type == SupplyType.FINITE
    # Default max is 1,000,000 * 10^0
    assert tp.max_supply == 1_000_000
    assert tp.initial_supply == 50


@pytest.mark.asyncio
async def test_validates_initial_vs_max_supply(
    mock_context, mock_client, mock_mirrornode
):
    """Should raise ValueError if initial_supply > max_supply."""
    params = CreateFungibleTokenParameters(
        token_name="Invalid Token",
        token_symbol="INV",
        decimals=0,
        initial_supply=200,
        max_supply=100,
    )

    with pytest.raises(ValueError, match="Initial supply .* cannot exceed max supply"):
        await HederaParameterNormaliser.normalise_create_fungible_token_params(
            params, mock_context, mock_client, mock_mirrornode
        )


@pytest.mark.asyncio
async def test_resolves_supply_key_from_mirrornode(
    mock_context, mock_client, mock_mirrornode
):
    """Should fetch the treasury account's key from mirror node if is_supply_key is True."""
    # Setup mirror node to return a specific key
    mock_mirrornode.get_account.return_value = {
        "account_public_key": TEST_MIRROR_KEY_STR
    }

    params = CreateFungibleTokenParameters(
        token_name="Key Token",
        token_symbol="KEY",
        is_supply_key=True,
        treasury_account_id=TEST_OPERATOR_ID,
    )

    result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
        params, mock_context, mock_client, mock_mirrornode
    )

    mock_mirrornode.get_account.assert_called_once_with(TEST_OPERATOR_ID)
    assert result.keys is not None
    assert result.keys.supply_key.to_string_der() == TEST_MIRROR_KEY_STR


@pytest.mark.asyncio
async def test_falls_back_to_operator_key_if_mirror_fails(
    mock_context, mock_client, mock_mirrornode
):
    """Should fall back to client operator key if mirror node lookup fails or returns no key."""
    # Setup mirror node to fail
    mock_mirrornode.get_account.side_effect = Exception("Mirror node offline")

    params = CreateFungibleTokenParameters(
        token_name="Fallback Token",
        token_symbol="FB",
        is_supply_key=True,
    )

    result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
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
        params = CreateFungibleTokenParameters(
            token_name="Sched Token",
            token_symbol="SCH",
            scheduling_params=scheduling_input,
        )

        result = await HederaParameterNormaliser.normalise_create_fungible_token_params(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_sched_norm.assert_called_once_with(
            scheduling_input, mock_context, mock_client
        )
        assert result.scheduling_params == mock_sched_return
