from unittest.mock import MagicMock, patch

import pytest
from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    ApproveNftAllowanceParameters,
)


class TestApproveNftAllowanceParameterNormalization:
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
        with patch(
            "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver"
        ) as mock:
            mock.resolve_account.return_value = operator_id
            yield mock

    def test_normalises_params_with_explicit_owner_spender_token_serials_and_memo(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveNftAllowanceParameters(
            owner_account_id="0.0.1111",
            spender_account_id="0.0.2222",
            token_id="0.0.7777",
            serial_numbers=[1, 2, 3],
            transaction_memo="approve NFT memo",
        )

        # Override resolve_account for this test to return the input owner
        mock_account_resolver.resolve_account.return_value = "0.0.1111"

        res = HederaParameterNormaliser.normalise_approve_nft_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            "0.0.1111", mock_context, mock_client
        )

        assert len(res.nft_allowances) == 1
        allowance = res.nft_allowances[0]
        assert str(allowance.owner_account_id) == "0.0.1111"
        assert str(allowance.spender_account_id) == "0.0.2222"
        assert str(allowance.token_id) == "0.0.7777"
        assert allowance.serial_numbers == [1, 2, 3]
        assert res.transaction_memo == "approve NFT memo"

    def test_defaults_owner_account_id_using_account_resolver(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveNftAllowanceParameters(
            spender_account_id="0.0.3333",
            token_id="0.0.4444",
            serial_numbers=[10],
        )

        res = HederaParameterNormaliser.normalise_approve_nft_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        allowance = res.nft_allowances[0]
        assert str(allowance.owner_account_id) == operator_id
        assert str(allowance.spender_account_id) == "0.0.3333"
        assert str(allowance.token_id) == "0.0.4444"
        assert allowance.serial_numbers == [10]

    def test_throws_when_all_serials_true_and_serial_numbers_provided(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
    ):
        params = ApproveNftAllowanceParameters(
            owner_account_id="0.0.1111",
            spender_account_id="0.0.2222",
            token_id="0.0.7777",
            all_serials=True,
            serial_numbers=[1, 2],
        )

        with pytest.raises(
            ValueError, match=r"Cannot specify both all_serials=true and serial_numbers"
        ):
            HederaParameterNormaliser.normalise_approve_nft_allowance(
                params, mock_context, mock_client
            )

    def test_throws_when_all_serials_not_true_and_serial_numbers_empty(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
    ):
        # Test with empty serial_numbers
        params_empty = ApproveNftAllowanceParameters(
            spender_account_id="0.0.2222",
            token_id="0.0.7777",
            serial_numbers=[],
        )

        with pytest.raises(
            ValueError,
            match=r"Either all_serials must be true or serial_numbers must be provided",
        ):
            HederaParameterNormaliser.normalise_approve_nft_allowance(
                params_empty, mock_context, mock_client
            )

    def test_throws_when_all_serials_not_true_and_serial_numbers_omitted(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
    ):
        # Test with serial_numbers omitted (None)
        params_omitted = ApproveNftAllowanceParameters(
            spender_account_id="0.0.2222",
            token_id="0.0.7777",
        )

        with pytest.raises(
            ValueError,
            match=r"Either all_serials must be true or serial_numbers must be provided",
        ):
            HederaParameterNormaliser.normalise_approve_nft_allowance(
                params_omitted, mock_context, mock_client
            )

    def test_normalises_approve_all_with_all_serials_true(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveNftAllowanceParameters(
            owner_account_id="0.0.1111",
            spender_account_id="0.0.2222",
            token_id="0.0.7777",
            all_serials=True,
            transaction_memo="approve all",
        )

        # Override resolve_account for this test to return the input owner
        mock_account_resolver.resolve_account.return_value = "0.0.1111"

        res = HederaParameterNormaliser.normalise_approve_nft_allowance(
            params, mock_context, mock_client
        )

        allowance = res.nft_allowances[0]
        assert allowance.approved_for_all is True
        assert allowance.serial_numbers == []
        assert str(allowance.token_id) == "0.0.7777"
        assert str(allowance.owner_account_id) == "0.0.1111"
        assert str(allowance.spender_account_id) == "0.0.2222"
        assert res.transaction_memo == "approve all"

    def test_explicitly_passed_none_owner_account_id_defaults_correctly(
        self,
        mock_context,
        mock_client,
        mock_account_resolver,
        operator_id,
    ):
        # Explicitly passing None to owner_account_id
        params = ApproveNftAllowanceParameters(
            owner_account_id=None,
            spender_account_id="0.0.4444",
            token_id="0.0.8888",
            serial_numbers=[5, 6],
        )

        res = HederaParameterNormaliser.normalise_approve_nft_allowance(
            params, mock_context, mock_client
        )

        # Verify resolver is called with None, triggering the default account logic
        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        # Verify the result uses the operator_id returned by the resolver
        allowance = res.nft_allowances[0]
        assert str(allowance.owner_account_id) == operator_id
        assert str(allowance.spender_account_id) == "0.0.4444"
        assert str(allowance.token_id) == "0.0.8888"
        assert allowance.serial_numbers == [5, 6]
