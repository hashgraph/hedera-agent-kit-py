from unittest.mock import Mock, AsyncMock

import pytest
from hiero_sdk_python import TokenId, Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    DeleteTokenAllowanceParameters,
)
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver


@pytest.mark.asyncio
class TestDeleteTokenAllowanceParamsNormalization:
    @pytest.fixture
    def mock_context(self):
        return Context()

    @pytest.fixture
    def mock_client(self):
        return Mock(spec=Client)

    @pytest.fixture
    def mock_mirrornode(self):
        service = Mock(spec=IHederaMirrornodeService)
        service.get_token_info = AsyncMock(return_value={"decimals": "2"})
        return service

    @pytest.fixture
    def mock_account_resolver(self, monkeypatch):
        mock_resolver = Mock(spec=AccountResolver)
        # Mock static method resolve_account
        monkeypatch.setattr(
            "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver.resolve_account",
            mock_resolver.resolve_account,
        )
        return mock_resolver

    async def test_normalise_with_explicit_owner_multiple_tokens_and_memo(
        self, mock_context, mock_client, mock_mirrornode, mock_account_resolver
    ):
        resolved_owner = "0.0.1234"
        spender = "0.0.5678"
        mock_account_resolver.resolve_account.return_value = resolved_owner

        params = DeleteTokenAllowanceParameters(
            owner_account_id=resolved_owner,
            spender_account_id=spender,
            token_ids=["0.0.111", "0.0.222"],
            transaction_memo="delete FT allowance",
        )

        res = await HederaParameterNormaliser.normalise_delete_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_account_resolver.resolve_account.assert_called_with(
            resolved_owner, mock_context, mock_client
        )

        assert len(res.token_allowances) == 2
        for allowance in res.token_allowances:
            assert str(allowance.owner_account_id) == resolved_owner
            assert str(allowance.spender_account_id) == spender
            assert allowance.amount == 0

        assert res.transaction_memo == "delete FT allowance"

    async def test_defaults_owner_account_id_using_account_resolver(
        self, mock_context, mock_client, mock_mirrornode, mock_account_resolver
    ):
        resolved_owner = "0.0.1234"
        spender = "0.0.5678"
        token_id = "0.0.9999"
        mock_account_resolver.resolve_account.return_value = resolved_owner

        params = DeleteTokenAllowanceParameters(
            spender_account_id=spender,
            token_ids=[token_id],
        )

        res = await HederaParameterNormaliser.normalise_delete_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_account_resolver.resolve_account.assert_called_with(
            None, mock_context, mock_client
        )

        allowance = res.token_allowances[0]
        assert str(allowance.owner_account_id) == resolved_owner
        assert str(allowance.spender_account_id) == spender
        assert str(allowance.token_id) == token_id
        assert allowance.amount == 0

    async def test_supports_multiple_token_ids(
        self, mock_context, mock_client, mock_mirrornode, mock_account_resolver
    ):
        resolved_owner = "0.0.1234"
        spender = "0.0.5678"
        mock_account_resolver.resolve_account.return_value = resolved_owner

        params = DeleteTokenAllowanceParameters(
            spender_account_id=spender,
            token_ids=["0.0.1", "0.0.2", "0.0.3"],
        )

        res = await HederaParameterNormaliser.normalise_delete_token_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        token_ids = [str(a.token_id) for a in res.token_allowances]
        amounts = [a.amount for a in res.token_allowances]

        assert token_ids == [
            "0.0.1",
            "0.0.2",
            "0.0.3",
        ]
        assert amounts == [0, 0, 0]
