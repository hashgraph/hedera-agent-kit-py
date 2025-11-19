import pytest

from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransactionRecordQueryParameters,
    TransactionRecordQueryParametersNormalised,
)


def test_normalises_mirror_node_style_id_as_is():
    """Should return mirror-node style transactionId as-is."""
    params = TransactionRecordQueryParameters(
        transaction_id="0.0.90-1756968265-343000618", nonce=5
    )

    result = HederaParameterNormaliser.normalise_get_transaction_record_params(params)

    assert isinstance(result, TransactionRecordQueryParametersNormalised)
    assert result.transaction_id == "0.0.90-1756968265-343000618"
    assert result.nonce == 5


def test_converts_sdk_style_id_to_mirror_node_style():
    """Should convert SDK-style transactionId to mirror-node style."""
    params = TransactionRecordQueryParameters(
        transaction_id="0.0.90@1756968265.343000618", nonce=2
    )

    result = HederaParameterNormaliser.normalise_get_transaction_record_params(params)

    assert result.transaction_id == "0.0.90-1756968265-343000618"
    assert result.nonce == 2


def test_converts_sdk_style_id_with_leading_zero_nanos():
    """Should correctly convert SDK-style transactionId with leading zero nanos."""
    params = TransactionRecordQueryParameters(
        transaction_id="0.0.90@1756968265.043000618", nonce=2
    )

    result = HederaParameterNormaliser.normalise_get_transaction_record_params(params)

    assert result.transaction_id == "0.0.90-1756968265-043000618"
    assert result.nonce == 2


def test_raises_value_error_if_transaction_id_format_invalid():
    """Should raise ValueError if transactionId format is invalid."""
    params = TransactionRecordQueryParameters(transaction_id="invalid-format", nonce=1)

    with pytest.raises(
        ValueError, match="Invalid transactionId format: invalid-format"
    ):
        HederaParameterNormaliser.normalise_get_transaction_record_params(params)


def test_passes_through_nonce():
    """Should correctly pass through the nonce value."""
    params = TransactionRecordQueryParameters(
        transaction_id="0.0.1-123456-7890", nonce=42
    )

    result = HederaParameterNormaliser.normalise_get_transaction_record_params(params)

    assert result.transaction_id == "0.0.1-123456-7890"
    assert result.nonce == 42


def test_handles_none_nonce():
    """Should handle nonce=None, which is the default."""
    params = TransactionRecordQueryParameters(
        transaction_id="0.0.1-123456-7890", nonce=None
    )

    result = HederaParameterNormaliser.normalise_get_transaction_record_params(params)

    assert result.transaction_id == "0.0.1-123456-7890"
    assert result.nonce is None
