"""Unit tests for associate token parameter normalization."""

from unittest.mock import MagicMock

import pytest
from hiero_sdk_python import AccountId, Client, PrivateKey

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import AssociateTokenParameters


@pytest.fixture
def mock_client():
    client = MagicMock(spec=Client)
    operator_key = PrivateKey.generate_ed25519()
    client.operator_private_key = operator_key
    client.operator_account_id = AccountId.from_string("0.0.1111")
    return client


@pytest.fixture
def context():
    return Context(account_id="0.0.1111")


def test_should_use_provided_account_id_and_pass_token_ids_through(
    mock_client, context
):
    params = AssociateTokenParameters(
        account_id="0.0.2222",
        token_ids=["0.0.1234", "0.0.5678"],
    )

    result = HederaParameterNormaliser.normalise_associate_token(
        params, context, mock_client
    )

    assert str(result.account_id) == "0.0.2222"
    assert [str(t) for t in result.token_ids] == ["0.0.1234", "0.0.5678"]


def test_should_fall_back_to_context_operator_account_when_account_id_not_provided(
    mock_client, context
):
    params = AssociateTokenParameters(
        token_ids=["0.0.9999"],
    )

    result = HederaParameterNormaliser.normalise_associate_token(
        params, context, mock_client
    )

    # Should fall back to context account_id which is 0.0.1111
    assert str(result.account_id) == "0.0.1111"
    assert [str(t) for t in result.token_ids] == ["0.0.9999"]
