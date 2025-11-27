import pytest
from unittest.mock import Mock
from hiero_sdk_python import AccountId, Client, Hbar
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    DeleteHbarAllowanceParameters,
)


@pytest.mark.asyncio
class TestDeleteHbarAllowanceParameterNormalization:
    async def test_normalise_delete_hbar_allowance_with_explicit_owner(self):
        # Arrange
        context = Context()
        client = Mock(spec=Client)
        params = DeleteHbarAllowanceParameters(
            owner_account_id="0.0.123",
            spender_account_id="0.0.456",
            transaction_memo="Delete allowance",
        )

        # Act
        normalised = await HederaParameterNormaliser.normalise_delete_hbar_allowance(
            params, context, client
        )

        # Assert
        assert len(normalised.hbar_allowances) == 1
        allowance = normalised.hbar_allowances[0]
        assert str(allowance.owner_account_id) == "0.0.123"
        assert str(allowance.spender_account_id) == "0.0.456"
        assert allowance.amount == 0
        assert normalised.transaction_memo == "Delete allowance"

    async def test_normalise_delete_hbar_allowance_with_default_owner(self):
        # Arrange
        context = Context(account_id="0.0.789")
        client = Mock(spec=Client)
        params = DeleteHbarAllowanceParameters(
            spender_account_id="0.0.456",
        )

        # Act
        normalised = await HederaParameterNormaliser.normalise_delete_hbar_allowance(
            params, context, client
        )

        # Assert
        assert len(normalised.hbar_allowances) == 1
        allowance = normalised.hbar_allowances[0]
        assert str(allowance.owner_account_id) == "0.0.789"
        assert str(allowance.spender_account_id) == "0.0.456"
        assert allowance.amount == 0

    async def test_normalise_delete_hbar_allowance_fails_without_owner(self):
        # Arrange
        context = Context()  # No default account
        client = Mock(spec=Client)
        client.operator_account_id = None  # No operator account
        params = DeleteHbarAllowanceParameters(
            spender_account_id="0.0.456",
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="neither context.account_id nor operator account"
        ):
            await HederaParameterNormaliser.normalise_delete_hbar_allowance(
                params, context, client
            )
