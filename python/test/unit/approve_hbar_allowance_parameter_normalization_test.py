from unittest.mock import MagicMock, patch

import pytest
from hiero_sdk_python import AccountId, Client, Hbar

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    ApproveHbarAllowanceParameters,
)
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver


class TestApproveHbarAllowanceParameterNormalization:
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

    def test_normalises_params_with_explicit_owner_spender_amount_memo(
        self, mock_context, mock_client, mock_account_resolver, operator_id
    ):
        params = ApproveHbarAllowanceParameters(
            owner_account_id="0.0.1111",
            spender_account_id="0.0.2222",
            amount=0.12345678,
            transaction_memo="approve memo",
        )

        # Override resolve_account for this test to return the input owner
        mock_account_resolver.resolve_account.return_value = "0.0.1111"

        res = HederaParameterNormaliser.normalise_approve_hbar_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            "0.0.1111", mock_context, mock_client
        )

        assert len(res.hbar_allowances) == 1
        allowance = res.hbar_allowances[0]
        assert str(allowance.owner_account_id) == "0.0.1111"
        assert str(allowance.spender_account_id) == "0.0.2222"
        assert res.transaction_memo == "approve memo"
        assert isinstance(allowance.amount, Hbar)
        assert allowance.amount == Hbar(0.12345678)

    def test_defaults_owner_account_id_using_account_resolver(
        self, mock_context, mock_client, mock_account_resolver, operator_id
    ):
        params = ApproveHbarAllowanceParameters(
            spender_account_id="0.0.3333",
            amount=1,
        )

        res = HederaParameterNormaliser.normalise_approve_hbar_allowance(
            params, mock_context, mock_client
        )

        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        assert len(res.hbar_allowances) == 1
        allowance = res.hbar_allowances[0]
        assert str(allowance.owner_account_id) == operator_id
        assert str(allowance.spender_account_id) == "0.0.3333"
        assert allowance.amount == Hbar(1)
