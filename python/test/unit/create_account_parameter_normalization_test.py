"""Unit tests for create account parameter normalization.

This module tests the normalization logic for account creation parameters,
ensuring that raw LLM-extracted parameters are correctly parsed and processed.
"""

from unittest.mock import AsyncMock, patch
import pytest
from hiero_sdk_python import PublicKey, PrivateKey, Hbar
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParameters,
    SchedulingParams,
)


# Helper to create CreateAccountParameters instances
def make_params(
    public_key=None,
    account_memo=None,
    initial_balance=0,
    max_automatic_token_associations=-1,
    scheduling_params=None,
):
    """Create CreateAccountParameters for testing."""
    return CreateAccountParameters(
        public_key=public_key,
        account_memo=account_memo,
        initial_balance=initial_balance,
        max_automatic_token_associations=max_automatic_token_associations,
        scheduling_params=scheduling_params,
    )


@pytest.mark.asyncio
async def test_uses_param_public_key_if_provided():
    """Test that params.public_key is used when provided."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_client.network = "testnet"
    generated_key = PrivateKey.generate_ed25519().public_key()
    public_key_str = generated_key.to_string_der()
    mock_mirrornode = AsyncMock()

    params = make_params(public_key=public_key_str, initial_balance=5)
    result = await HederaParameterNormaliser.normalise_create_account(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert str(result.initial_balance) == str(Hbar(5))
    assert isinstance(result.key, PublicKey)
    assert result.key.to_string_der() == public_key_str
    assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_uses_operator_public_key_if_no_param():
    """Test that client.operator_public_key is used when no param.public_key."""
    mock_context = Context()
    operator_key = PrivateKey.generate_ed25519()
    mock_client = AsyncMock()
    mock_client.operator_private_key = operator_key
    mock_client.network = "testnet"
    mock_mirrornode = AsyncMock()

    params = make_params(initial_balance=1, account_memo="test account")
    result = await HederaParameterNormaliser.normalise_create_account(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert result.key.to_string_der() == operator_key.public_key().to_string_der()
    assert result.memo == "test account"
    assert result.scheduling_params is None


@pytest.mark.asyncio
@patch.object(AccountResolver, "get_default_account")
async def test_falls_back_to_mirrornode_when_no_operator_key(mock_get_default_account):
    """Test fallback to mirrornode.get_account when no param and no operator key."""
    mock_context = Context()
    client_no_op_key = AsyncMock()
    client_no_op_key.operator_private_key = None
    client_no_op_key.network = "testnet"

    mock_get_default_account.return_value = "0.0.2002"
    secondary_key = PrivateKey.generate_ed25519().public_key()

    mock_mirrornode = AsyncMock()
    mock_mirrornode.get_account = AsyncMock(
        return_value={"account_public_key": secondary_key.to_string_der()}
    )

    params = make_params(account_memo="test account", initial_balance=0)
    result = await HederaParameterNormaliser.normalise_create_account(
        params, mock_context, client_no_op_key, mock_mirrornode
    )

    assert result.key.to_string_der() == secondary_key.to_string_der()
    assert str(result.initial_balance) == str(Hbar(0))
    mock_mirrornode.get_account.assert_called_once_with("0.0.2002")


@pytest.mark.asyncio
@patch.object(AccountResolver, "get_default_account")
async def test_throws_error_when_no_public_key_available(mock_get_default_account):
    """Test that error is thrown when no public key is available anywhere."""
    mock_context = Context()
    client_no_op_key = AsyncMock()
    client_no_op_key.operator_private_key = None
    client_no_op_key.network = "testnet"

    mock_get_default_account.return_value = None
    mock_mirrornode = AsyncMock()

    params = make_params(initial_balance=0)

    with pytest.raises(ValueError, match="Unable to resolve public key"):
        await HederaParameterNormaliser.normalise_create_account(
            params, mock_context, client_no_op_key, mock_mirrornode
        )


@pytest.mark.asyncio
async def test_applies_defaults_when_values_not_provided():
    """Test that defaults are applied when values are not provided."""
    mock_context = Context()
    operator_key = PrivateKey.generate_ed25519()
    mock_client = AsyncMock()
    mock_client.operator_private_key = operator_key
    mock_client.network = "testnet"
    mock_mirrornode = AsyncMock()

    params = make_params()

    result = await HederaParameterNormaliser.normalise_create_account(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert str(result.initial_balance) == str(Hbar(0))
    assert result.key.to_string_der() == operator_key.public_key().to_string_der()
    assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_calls_normalise_scheduled_transaction_params_when_scheduled():
    """Test that normalise_scheduled_transaction_params is called when is_scheduled=True."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_client.operator_private_key = PrivateKey.generate_ed25519()
    mock_client.network = "testnet"
    mock_mirrornode = AsyncMock()

    secondary_key = PrivateKey.generate_ed25519().public_key()
    mock_schedule_params = ScheduleCreateParams(wait_for_expiry=False)
    spy = AsyncMock(return_value=mock_schedule_params)

    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        spy,
    ):
        params = make_params(
            public_key=secondary_key.to_string_der(),
            scheduling_params=SchedulingParams(
                is_scheduled=True, admin_key=False, wait_for_expiry=False
            ),
        )

        result = await HederaParameterNormaliser.normalise_create_account(
            params, mock_context, mock_client, mock_mirrornode
        )

        spy.assert_called_once()
        assert result.scheduling_params == mock_schedule_params
        assert result.key.to_string_der() == secondary_key.to_string_der()


@pytest.mark.asyncio
async def test_does_not_call_scheduled_params_when_not_scheduled():
    """Test that scheduling params are not processed when is_scheduled=False."""
    mock_context = Context()
    operator_key = PrivateKey.generate_ed25519()
    mock_client = AsyncMock()
    mock_client.operator_private_key = operator_key
    mock_client.network = "testnet"
    mock_mirrornode = AsyncMock()

    spy = AsyncMock()

    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        spy,
    ):
        params = make_params(scheduling_params=SchedulingParams(is_scheduled=False))

        result = await HederaParameterNormaliser.normalise_create_account(
            params, mock_context, mock_client, mock_mirrornode
        )

        spy.assert_not_called()
        assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_handles_memo_correctly():
    """Test that memo is correctly handled."""
    mock_context = Context()
    operator_key = PrivateKey.generate_ed25519()
    mock_client = AsyncMock()
    mock_client.operator_private_key = operator_key
    mock_client.network = "testnet"
    mock_mirrornode = AsyncMock()

    memo = "Test memo for account creation"
    params = make_params(account_memo=memo)

    result = await HederaParameterNormaliser.normalise_create_account(
        params, mock_context, mock_client, mock_mirrornode
    )

    assert result.memo == memo
