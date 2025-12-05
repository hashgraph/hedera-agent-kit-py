import pytest
from unittest.mock import patch, MagicMock
from hiero_sdk_python import AccountId, Client
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit.shared.parameter_schemas import DeleteAccountParameters
from hedera_agent_kit.shared.configuration import Context


@pytest.fixture
def mock_context():
    """Provide a mock Context with an account_id."""
    return Context(account_id="0.0.5005")


@pytest.fixture
def mock_client():
    """Provide a mock Client instance."""
    return MagicMock(spec=Client)


@pytest.fixture(autouse=True)
def mock_resolvers():
    """Mock AccountResolver methods globally for tests."""
    with patch.object(
        AccountResolver,
        "is_hedera_address",
        side_effect=lambda addr: addr.count(".") == 2
        and all(p.isdigit() for p in addr.split(".")),
    ) as mock_is_addr, patch.object(
        AccountResolver, "get_default_account", return_value="0.0.1001"
    ) as mock_get_default:
        yield mock_is_addr, mock_get_default


def test_uses_provided_account_and_transfer_ids(mock_context, mock_client):
    """Should use provided valid Hedera addresses for both account_id and transfer_account_id."""
    params = DeleteAccountParameters(
        account_id="0.0.1234", transfer_account_id="0.0.4321"
    )

    with patch.object(
        AccountResolver, "is_hedera_address", wraps=AccountResolver.is_hedera_address
    ) as mock_is_addr:
        result = HederaParameterNormaliser.normalise_delete_account(
            params, mock_context, mock_client
        )

        mock_is_addr.assert_called_with("0.0.1234")
        assert isinstance(result.account_id, AccountId)
        assert isinstance(result.transfer_account_id, AccountId)
        assert str(result.account_id) == "0.0.1234"
        assert str(result.transfer_account_id) == "0.0.4321"


def test_defaults_transfer_account_id_when_missing(mock_context, mock_client):
    """Should use AccountResolver.get_default_account when transfer_account_id not provided."""
    with patch.object(
        AccountResolver, "get_default_account", return_value="0.0.7777"
    ) as mock_get_default:
        params = DeleteAccountParameters(account_id="0.0.999")

        result = HederaParameterNormaliser.normalise_delete_account(
            params, mock_context, mock_client
        )

        mock_get_default.assert_called_once_with(mock_context, mock_client)
        assert str(result.account_id) == "0.0.999"
        assert str(result.transfer_account_id) == "0.0.7777"


def test_raises_when_account_id_invalid(mock_context, mock_client):
    """Should raise ValueError when account_id is not a valid Hedera address."""
    with patch.object(AccountResolver, "is_hedera_address", return_value=False):
        params = DeleteAccountParameters(
            account_id="not-hedera", transfer_account_id="0.0.1"
        )

        with pytest.raises(ValueError, match="Account ID must be a Hedera address"):
            HederaParameterNormaliser.normalise_delete_account(
                params, mock_context, mock_client
            )


def test_converts_string_ids_to_accountid(mock_context, mock_client):
    """Should convert string IDs to AccountId instances."""
    params = DeleteAccountParameters(account_id="0.0.12", transfer_account_id="0.0.34")

    result = HederaParameterNormaliser.normalise_delete_account(
        params, mock_context, mock_client
    )

    assert isinstance(result.account_id, AccountId)
    assert isinstance(result.transfer_account_id, AccountId)
    assert str(result.account_id) == "0.0.12"
    assert str(result.transfer_account_id) == "0.0.34"


def test_raises_when_transfer_account_id_cannot_be_determined(
    mock_context, mock_client
):
    """Should raise ValueError when transfer_account_id cannot be determined."""
    with patch.object(AccountResolver, "get_default_account", return_value=None):
        params = DeleteAccountParameters(account_id="0.0.1234")

        with pytest.raises(ValueError, match="Could not determine transfer account ID"):
            HederaParameterNormaliser.normalise_delete_account(
                params, mock_context, mock_client
            )
