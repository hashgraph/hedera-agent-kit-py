import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from hiero_sdk_python import Client, PrivateKey, PublicKey, Network
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateTopicParameters,
    CreateTopicParametersNormalised,
)


@pytest.mark.asyncio
async def test_applies_defaults_when_values_not_provided():
    """Should apply defaults when no values are provided (no submit key)."""
    mock_context = Context(account_id="0.0.1001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")
    mock_mirror_node = AsyncMock()
    mock_mirror_node.get_account = AsyncMock(
        return_value=SimpleNamespace(account_public_key=None)
    )

    with patch.object(AccountResolver, "get_default_account", return_value="0.0.1001"):
        params = CreateTopicParameters()

        result = await HederaParameterNormaliser.normalise_create_topic_params(
            params, mock_context, mock_client, mock_mirror_node
        )

        assert isinstance(result, CreateTopicParametersNormalised)
        assert result.is_submit_key is False or result.is_submit_key is None
        assert result.submit_key is None
        assert result.topic_memo is None
        assert result.memo == result.topic_memo


@pytest.mark.asyncio
async def test_sets_submit_key_from_mirror_node():
    """Should set submit_key using public key from mirror node when is_submit_key is True."""
    mock_context = Context(account_id="0.0.1001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")
    mock_mirror_node = AsyncMock()

    keypair = PrivateKey.generate_ed25519()
    mock_mirror_node.get_account = AsyncMock(
        return_value=SimpleNamespace(
            account_public_key=keypair.public_key().to_string_der()
        )
    )

    with patch.object(AccountResolver, "get_default_account", return_value="0.0.1001"):
        params = CreateTopicParameters(is_submit_key=True, topic_memo="hello")

        result = await HederaParameterNormaliser.normalise_create_topic_params(
            params, mock_context, mock_client, mock_mirror_node
        )

        assert result.is_submit_key is True
        assert isinstance(result.submit_key, PublicKey)
        assert result.submit_key.to_string_der() == keypair.public_key().to_string_der()
        assert result.topic_memo == "hello"
        assert result.memo == result.topic_memo


@pytest.mark.asyncio
async def test_falls_back_to_client_operator_key_when_mirror_has_no_key():
    """Should use client.operator_private_key.public_key() if mirror node returns no key."""
    mock_context = Context(account_id="0.0.1001")
    mock_mirror_node = AsyncMock()
    mock_mirror_node.get_account = AsyncMock(
        return_value=SimpleNamespace(account_public_key=None)
    )

    operator_key = PrivateKey.generate_ed25519()
    mock_client = MagicMock(spec=Client)
    mock_client.operator_private_key = operator_key
    mock_client.network = Network(network="testnet")

    with patch.object(AccountResolver, "get_default_account", return_value="0.0.1001"):
        params = CreateTopicParameters(is_submit_key=True)

        result = await HederaParameterNormaliser.normalise_create_topic_params(
            params, mock_context, mock_client, mock_mirror_node
        )

        assert result.submit_key is not None
        assert isinstance(result.submit_key, PublicKey)
        assert result.submit_key.to_string_der() == operator_key.public_key().to_string_der()


@pytest.mark.asyncio
async def test_raises_when_no_public_key_for_submit_key():
    """Should raise ValueError when is_submit_key=True and no public key can be determined."""
    mock_context = Context(account_id="0.0.1001")
    mock_client = MagicMock(spec=Client)
    mock_client.operator_private_key = None
    mock_client.network = Network(network="testnet")
    mock_mirror_node = AsyncMock()
    mock_mirror_node.get_account = AsyncMock(
        return_value=SimpleNamespace(account_public_key=None)
    )

    with patch.object(AccountResolver, "get_default_account", return_value="0.0.1001"):
        params = CreateTopicParameters(is_submit_key=True)

        with pytest.raises(ValueError, match="Could not determine public key for submit key"):
            await HederaParameterNormaliser.normalise_create_topic_params(
                params, mock_context, mock_client, mock_mirror_node
            )


@pytest.mark.asyncio
async def test_raises_when_no_default_account_id():
    """Should raise ValueError when AccountResolver.get_default_account returns None."""
    mock_context = Context()
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")
    mock_mirror_node = AsyncMock()

    with patch.object(AccountResolver, "get_default_account", return_value=None):
        params = CreateTopicParameters()

        with pytest.raises(ValueError, match="Could not determine default account ID"):
            await HederaParameterNormaliser.normalise_create_topic_params(
                params, mock_context, mock_client, mock_mirror_node
            )
