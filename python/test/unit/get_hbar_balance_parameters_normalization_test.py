from unittest.mock import MagicMock, patch
from hiero_sdk_python import Client, Network

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    AccountBalanceQueryParameters,
    AccountBalanceQueryParametersNormalised,
)


def test_normalises_hbar_balance_params_with_provided_account_id():
    """Should keep provided account_id as-is (no resolution)."""
    mock_context = Context(account_id="0.0.2001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    # Patch AccountResolver to ensure it's NOT called
    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_account_resolver:
        params = AccountBalanceQueryParameters(account_id="0.0.1001")

        result = HederaParameterNormaliser.normalise_get_hbar_balance(
            params, mock_context, mock_client
        )

        # ✅ Should simply pass through the provided account_id
        assert isinstance(result, AccountBalanceQueryParametersNormalised)
        assert result.account_id == "0.0.1001"
        mock_account_resolver.get_default_account.assert_not_called()


def test_normalises_hbar_balance_params_without_provided_account_id():
    """Should default to AccountResolver.get_default_account() when account_id not provided."""
    mock_context = Context(account_id="0.0.2001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_account_resolver:
        mock_account_resolver.get_default_account.return_value = "0.0.1001"

        params = AccountBalanceQueryParameters(account_id=None)

        result = HederaParameterNormaliser.normalise_get_hbar_balance(
            params, mock_context, mock_client
        )

        # ✅ Should call get_default_account() and use its result
        assert isinstance(result, AccountBalanceQueryParametersNormalised)
        assert result.account_id == "0.0.1001"
        mock_account_resolver.get_default_account.assert_called_once_with(
            mock_context, mock_client
        )
