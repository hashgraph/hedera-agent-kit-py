import pytest
from unittest.mock import MagicMock, patch

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    DeleteNonFungibleTokenAllowanceParameters,
)


class TestDeleteNonFungibleTokenAllowanceParameterNormalization:
    @pytest.fixture
    def mock_context(self):
        return MagicMock(spec=Context)

    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def operator_id(self):
        return "0.0.5005"

    @pytest.fixture
    def mock_account_resolver(self, operator_id):
        # Patch the AccountResolver used in the normalizer module
        with patch(
            "hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
        ) as mock:
            # Mock resolve_account to return the input account or operator_id if None
            mock.resolve_account.side_effect = lambda account, ctx, client: (
                account if account else operator_id
            )
            yield mock

    def test_normalises_delete_params_correctly(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
    ):
        """Should correctly normalize parameters with explicit owner and serial numbers."""
        params = DeleteNonFungibleTokenAllowanceParameters(
            owner_account_id="0.0.1111",
            token_id="0.0.7777",
            serial_numbers=[1, 2, 3],
            transaction_memo="delete allowance memo",
        )

        res = HederaParameterNormaliser.normalise_delete_non_fungible_token_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            "0.0.1111", mock_context, mock_client
        )

        # The method returns 'nft_wipe', not 'nft_allowances'
        assert len(res.nft_wipe) == 1
        allowance = res.nft_wipe[0]

        assert str(allowance.owner_account_id) == "0.0.1111"
        assert allowance.spender_account_id is None
        assert str(allowance.token_id) == "0.0.7777"
        assert allowance.serial_numbers == [1, 2, 3]
        assert res.transaction_memo == "delete allowance memo"

    def test_defaults_owner_account_id_to_operator(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
        operator_id,
    ):
        """Should default owner_account_id to operator when not provided."""
        params = DeleteNonFungibleTokenAllowanceParameters(
            token_id="0.0.4444",
            serial_numbers=[10],
        )

        res = HederaParameterNormaliser.normalise_delete_non_fungible_token_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        allowance = res.nft_wipe[0]
        assert str(allowance.owner_account_id) == operator_id
        assert allowance.spender_account_id is None
        assert str(allowance.token_id) == "0.0.4444"
        assert allowance.serial_numbers == [10]

    def test_throws_when_no_serials(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
    ):
        """Should raise ValueError when serial_numbers is empty."""
        params = DeleteNonFungibleTokenAllowanceParameters(
            token_id="0.0.7777",
            serial_numbers=[],
        )

        with pytest.raises(
            ValueError,
            match=r"serial_numbers must be provided",
        ):
            HederaParameterNormaliser.normalise_delete_non_fungible_token_allowance(
                params, mock_context, mock_client
            )
