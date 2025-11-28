from unittest.mock import MagicMock, patch
from hiero_sdk_python import Client, Network

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    AccountTokenBalancesQueryParameters,
    AccountTokenBalancesQueryParametersNormalised,
)


def test_normalises_token_balances_params_with_provided_account_id():
    """Should keep provided account_id as-is (no resolution) and pass token_id."""
    mock_context = Context(account_id="0.0.2001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    # Patch AccountResolver to ensure it's NOT called
    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_account_resolver:
        params = AccountTokenBalancesQueryParameters(
            account_id="0.0.2222", token_id="0.0.3333"
        )

        result = HederaParameterNormaliser.normalise_account_token_balances_params(
            params, mock_context, mock_client
        )

        assert isinstance(result, AccountTokenBalancesQueryParametersNormalised)
        assert result.account_id == "0.0.2222"
        assert result.token_id == "0.0.3333"
        mock_account_resolver.get_default_account.assert_not_called()


def test_normalises_token_balances_params_without_provided_account_id():
    """Should default to AccountResolver.get_default_account() when account_id not provided."""
    mock_context = Context(account_id="0.0.2001")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
    ) as mock_account_resolver:
        mock_account_resolver.get_default_account.return_value = "0.0.1001"

        params = AccountTokenBalancesQueryParameters(token_id="0.0.7777")

        result = HederaParameterNormaliser.normalise_account_token_balances_params(
            params, mock_context, mock_client
        )

        assert isinstance(result, AccountTokenBalancesQueryParametersNormalised)
        assert result.account_id == "0.0.1001"
        assert result.token_id == "0.0.7777"
        mock_account_resolver.get_default_account.assert_called_once_with(
            mock_context, mock_client
        )
