import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from hiero_sdk_python import AccountId, Client, Network, TokenId, PublicKey
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import (
    SchedulingParams,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    UpdateTokenParameters,
    UpdateTokenParametersNormalised,
)


@pytest.fixture
def mock_context():
    return Context(account_id="0.0.5005")


@pytest.fixture
def mock_client():
    client = MagicMock(spec=Client)
    client.network = Network(network="testnet")
    # Mock operator private key for key resolution
    mock_private_key = MagicMock()
    mock_public_key = MagicMock(spec=PublicKey)
    mock_public_key.to_string_der.return_value = (
        "302a300506032b6570032100abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234"
    )
    mock_private_key.public_key.return_value = mock_public_key
    client.operator_private_key = mock_private_key
    return client


@pytest.mark.asyncio
async def test_resolves_token_id_and_includes_token_name(mock_context, mock_client):
    """Should resolve token_id and include token_name in token_params."""
    params = UpdateTokenParameters(
        token_id="0.0.1001",
        token_name="Updated Token Name",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert isinstance(result, UpdateTokenParametersNormalised)
    assert result.token_id == TokenId.from_string("0.0.1001")
    assert result.token_params is not None
    assert result.token_params.token_name == "Updated Token Name"
    assert result.token_keys is None


@pytest.mark.asyncio
async def test_resolves_token_symbol(mock_context, mock_client):
    """Should include token_symbol in token_params."""
    params = UpdateTokenParameters(
        token_id="0.0.2002",
        token_symbol="NEWSYM",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_id == TokenId.from_string("0.0.2002")
    assert result.token_params is not None
    assert result.token_params.token_symbol == "NEWSYM"


@pytest.mark.asyncio
async def test_resolves_token_memo(mock_context, mock_client):
    """Should include token_memo in token_params."""
    params = UpdateTokenParameters(
        token_id="0.0.3003",
        token_memo="Updated memo text",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_params is not None
    assert result.token_params.token_memo == "Updated memo text"


@pytest.mark.asyncio
async def test_resolves_admin_key_with_boolean_true(mock_context, mock_client):
    """Should resolve admin_key=True to operator's public key."""
    params = UpdateTokenParameters(
        token_id="0.0.4004",
        admin_key=True,
    )

    mock_public_key = MagicMock(spec=PublicKey)
    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_keys is not None
    assert result.token_keys.admin_key is not None


@pytest.mark.asyncio
async def test_resolves_supply_key_with_string(mock_context, mock_client):
    """Should resolve supply_key provided as a public key string."""
    public_key_str = "302a300506032b6570032100dead1234567890dead1234567890dead1234567890dead1234567890dead1234"
    params = UpdateTokenParameters(
        token_id="0.0.5005",
        supply_key=public_key_str,
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_keys is not None
    assert result.token_keys.supply_key is not None


@pytest.mark.asyncio
async def test_resolves_treasury_account_id(mock_context, mock_client):
    """Should resolve treasury_account_id to AccountId."""
    params = UpdateTokenParameters(
        token_id="0.0.6006",
        treasury_account_id="0.0.9999",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_params is not None
    assert result.token_params.treasury_account_id == AccountId.from_string("0.0.9999")


@pytest.mark.asyncio
async def test_resolves_auto_renew_account_id(mock_context, mock_client):
    """Should resolve auto_renew_account_id to AccountId."""
    params = UpdateTokenParameters(
        token_id="0.0.7007",
        auto_renew_account_id="0.0.8888",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_params is not None
    assert result.token_params.auto_renew_account_id == AccountId.from_string("0.0.8888")


@pytest.mark.asyncio
async def test_resolves_metadata_string_to_bytes(mock_context, mock_client):
    """Should encode metadata string to UTF-8 bytes."""
    params = UpdateTokenParameters(
        token_id="0.0.8008",
        metadata="https://example.com/metadata.json",
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_params is not None
    assert result.token_params.metadata == b"https://example.com/metadata.json"


@pytest.mark.asyncio
async def test_omits_token_params_when_no_optional_fields(mock_context, mock_client):
    """Should not set token_params when only token_id is provided."""
    params = UpdateTokenParameters(token_id="0.0.9009")

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_id == TokenId.from_string("0.0.9009")
    assert result.token_params is None
    assert result.token_keys is None


@pytest.mark.asyncio
async def test_resolves_multiple_keys(mock_context, mock_client):
    """Should resolve multiple keys when provided."""
    params = UpdateTokenParameters(
        token_id="0.0.1111",
        admin_key=True,
        freeze_key=True,
        wipe_key=True,
    )

    mock_public_key = MagicMock(spec=PublicKey)
    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_keys is not None
    assert result.token_keys.admin_key is not None
    assert result.token_keys.freeze_key is not None
    assert result.token_keys.wipe_key is not None


@pytest.mark.asyncio
async def test_supports_scheduling_params_when_provided(mock_context, mock_client):
    """Should normalize scheduling parameters when provided."""
    params = UpdateTokenParameters(
        token_id="0.0.2222",
        token_name="Scheduled Update",
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_public_key = MagicMock(spec=PublicKey)
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        with patch.object(
            HederaParameterNormaliser,
            "normalise_scheduled_transaction_params",
            AsyncMock(return_value={"is_scheduled": True}),
        ) as mock_schedule_normaliser:
            result = await HederaParameterNormaliser.normalise_update_token(
                params, mock_context, mock_client
            )

    assert result.token_id == TokenId.from_string("0.0.2222")
    assert result.token_params.token_name == "Scheduled Update"
    assert result.scheduling_params is not None
    mock_schedule_normaliser.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolves_multiple_params_and_keys_together(mock_context, mock_client):
    """Should handle both token_params and token_keys in a single update."""
    params = UpdateTokenParameters(
        token_id="0.0.3333",
        token_name="Complete Update",
        token_symbol="COMP",
        token_memo="Full update test",
        admin_key=True,
        supply_key=True,
    )

    mock_public_key = MagicMock(spec=PublicKey)
    with patch(
        "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_resolver:
        mock_resolver.get_default_public_key = AsyncMock(return_value=mock_public_key)
        
        result = await HederaParameterNormaliser.normalise_update_token(
            params, mock_context, mock_client
        )

    assert result.token_id == TokenId.from_string("0.0.3333")
    assert result.token_params is not None
    assert result.token_params.token_name == "Complete Update"
    assert result.token_params.token_symbol == "COMP"
    assert result.token_params.token_memo == "Full update test"
    assert result.token_keys is not None
    assert result.token_keys.admin_key is not None
    assert result.token_keys.supply_key is not None
