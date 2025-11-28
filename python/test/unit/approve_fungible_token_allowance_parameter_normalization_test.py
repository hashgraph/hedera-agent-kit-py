from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    ApproveTokenAllowanceParameters,
    TokenApproval,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)


class TestApproveFungibleTokenAllowanceParameterNormalization:
    @pytest.fixture
    def mock_context(self):
        return MagicMock(spec=Context)

    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def mock_mirrornode(self):
        mock = MagicMock(spec=IHederaMirrornodeService)
        mock.get_token_info = AsyncMock(return_value={"decimals": "2"})
        return mock

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

    @pytest.mark.asyncio
    async def test_normalises_params_with_explicit_owner_spender_token_memo(
        self,
        mock_context,
        mock_client,
        mock_mirrornode,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveTokenAllowanceParameters(
            owner_account_id="0.0.1111",
            spender_account_id="0.0.2222",
            token_approvals=[TokenApproval(token_id="0.0.9999", amount=100)],
            transaction_memo="approve FT allowance",
        )

        # Override resolve_account for this test to return the input owner
        mock_account_resolver.resolve_account.return_value = "0.0.1111"

        res = await HederaParameterNormaliser.normalise_approve_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_account_resolver.resolve_account.assert_called_with(
            "0.0.1111", mock_context, mock_client
        )

        assert len(res.token_allowances) == 1
        allowance = res.token_allowances[0]
        assert str(allowance.owner_account_id) == "0.0.1111"
        assert str(allowance.spender_account_id) == "0.0.2222"
        assert str(allowance.token_id) == "0.0.9999"
        # With 2 decimals, 100 * 10^2 = 10000
        assert allowance.amount == 10000
        assert res.transaction_memo == "approve FT allowance"

    @pytest.mark.asyncio
    async def test_supports_multiple_token_allowances(
        self,
        mock_context,
        mock_client,
        mock_mirrornode,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveTokenAllowanceParameters(
            spender_account_id="0.0.2222",
            token_approvals=[
                TokenApproval(token_id="0.0.1", amount=1),
                TokenApproval(token_id="0.0.2", amount=2),
            ],
        )

        res = await HederaParameterNormaliser.normalise_approve_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        assert len(res.token_allowances) == 2
        assert str(res.token_allowances[0].token_id) == "0.0.1"
        assert res.token_allowances[0].amount == 100  # 1 * 10^2
        assert str(res.token_allowances[1].token_id) == "0.0.2"
        assert res.token_allowances[1].amount == 200  # 2 * 10^2

    @pytest.mark.asyncio
    async def test_defaults_owner_account_id_using_account_resolver(
        self,
        mock_context,
        mock_client,
        mock_mirrornode,
        mock_account_resolver,
        operator_id,
    ):
        params = ApproveTokenAllowanceParameters(
            spender_account_id="0.0.3333",
            token_approvals=[TokenApproval(token_id="0.0.9999", amount=5)],
        )

        res = await HederaParameterNormaliser.normalise_approve_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        assert len(res.token_allowances) == 1
        allowance = res.token_allowances[0]
        assert str(allowance.owner_account_id) == operator_id

    @pytest.mark.asyncio
    async def test_handles_missing_decimals_by_defaulting_to_0(
        self,
        mock_context,
        mock_client,
        mock_mirrornode,
        mock_account_resolver,
        operator_id,
    ):
        mock_mirrornode.get_token_info.return_value = {}  # no decimals

        params = ApproveTokenAllowanceParameters(
            spender_account_id="0.0.3333",
            token_approvals=[TokenApproval(token_id="0.0.9999", amount=7)],
        )

        res = await HederaParameterNormaliser.normalise_approve_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        allowance = res.token_allowances[0]
        # With decimals=0, base = 7
        assert allowance.amount == 7

    @pytest.mark.asyncio
    async def test_explicitly_passed_none_owner_account_id_defaults_correctly(
        self,
        mock_context,
        mock_client,
        mock_mirrornode,
        mock_account_resolver,
        operator_id,
    ):
        # Explicitly passing None to owner_account_id
        params = ApproveTokenAllowanceParameters(
            owner_account_id=None,
            spender_account_id="0.0.4444",
            token_approvals=[TokenApproval(token_id="0.0.8888", amount=10)],
        )

        res = await HederaParameterNormaliser.normalise_approve_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        # Verify resolver is called with None, triggering the default account logic
        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        # Verify the result uses the operator_id returned by the resolver
        allowance = res.token_allowances[0]
        assert str(allowance.owner_account_id) == operator_id
        assert str(allowance.spender_account_id) == "0.0.4444"
