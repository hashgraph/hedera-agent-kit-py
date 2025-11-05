import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from hiero_sdk_python import AccountId, Client, Network
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    UpdateAccountParameters,
    UpdateAccountParametersNormalised,
    SchedulingParams,
)


@pytest.mark.asyncio
async def test_resolves_account_id_and_includes_only_supported_fields():
    """Should resolve account_id via AccountResolver and include only supported fields."""
    mock_context = Context(account_id="0.0.5005")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    mock_account_resolver = MagicMock()
    mock_account_resolver.resolve_account.return_value = "0.0.1001"

    params = UpdateAccountParameters(account_memo="hello")

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver",
        mock_account_resolver,
    ), patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params", AsyncMock()
    ):
        result = await HederaParameterNormaliser.normalise_update_account(
            params, mock_context, mock_client
        )

    assert isinstance(result, UpdateAccountParametersNormalised)
    assert result.account_params.account_id == AccountId.from_string("0.0.1001")
    assert result.account_params.account_memo == "hello"
    # Fields not supported by SDK should not exist
    assert not hasattr(result.account_params, "max_automatic_token_associations")
    assert not hasattr(result.account_params, "decline_reward")
    assert not hasattr(result.account_params, "staked_account_id")
    mock_account_resolver.resolve_account.assert_called_once_with(
        None, mock_context, mock_client
    )


@pytest.mark.asyncio
async def test_passes_through_account_id_only():
    """Should pass through account_id when provided (unsupported fields ignored)."""
    mock_context = Context(account_id="0.0.5005")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    mock_account_resolver = MagicMock()
    mock_account_resolver.resolve_account.return_value = "0.0.7777"

    params = UpdateAccountParameters(account_id="0.0.7777")

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver",
        mock_account_resolver,
    ), patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params", AsyncMock()
    ):
        result = await HederaParameterNormaliser.normalise_update_account(
            params, mock_context, mock_client
        )

    assert result.account_params.account_id == AccountId.from_string("0.0.7777")
    mock_account_resolver.resolve_account.assert_called_once_with(
        "0.0.7777", mock_context, mock_client
    )


@pytest.mark.asyncio
async def test_omits_all_unsupported_fields_when_not_provided():
    """Should omit all unsupported fields when not provided."""
    mock_context = Context(account_id="0.0.5005")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    mock_account_resolver = MagicMock()
    mock_account_resolver.resolve_account.return_value = "0.0.1"

    params = UpdateAccountParameters(account_id="0.0.1")

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver",
        mock_account_resolver,
    ), patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params", AsyncMock()
    ):
        result = await HederaParameterNormaliser.normalise_update_account(
            params, mock_context, mock_client
        )

    assert result.account_params.account_memo is None
    assert not hasattr(result.account_params, "max_automatic_token_associations")
    assert not hasattr(result.account_params, "decline_reward")
    assert not hasattr(result.account_params, "staked_account_id")


@pytest.mark.asyncio
async def test_supports_scheduling_params_when_provided():
    """Should normalize scheduling parameters when provided."""
    mock_context = Context(account_id="0.0.5005")
    mock_client = MagicMock(spec=Client)
    mock_client.network = Network(network="testnet")

    mock_account_resolver = MagicMock()
    mock_account_resolver.resolve_account.return_value = "0.0.1234"

    params = UpdateAccountParameters(
        account_id="0.0.1234",
        account_memo="scheduled memo",
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    with patch(
        "hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.AccountResolver",
        mock_account_resolver,
    ), patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        AsyncMock(return_value={"is_scheduled": True}),
    ) as mock_schedule_normaliser:
        result = await HederaParameterNormaliser.normalise_update_account(
            params, mock_context, mock_client
        )

    assert result.account_params.account_id == AccountId.from_string("0.0.1234")
    assert result.account_params.account_memo == "scheduled memo"
    assert result.scheduling_params is not None
    mock_schedule_normaliser.assert_awaited_once()
