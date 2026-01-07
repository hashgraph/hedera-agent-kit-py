import pytest
from hiero_sdk_python.schedule.schedule_id import ScheduleId

from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    SignScheduleTransactionToolParameters,
)


def test_normalise_valid_schedule_id():
    """Test normalization of a valid schedule ID string."""
    params = SignScheduleTransactionToolParameters(schedule_id="0.0.12345")

    result = HederaParameterNormaliser.normalise_sign_schedule_transaction(params)

    assert isinstance(result.schedule_id, ScheduleId)
    assert str(result.schedule_id) == "0.0.12345"


def test_normalise_schedule_id_with_different_shards():
    """Test normalization with non-zero shard and realm values."""
    params = SignScheduleTransactionToolParameters(schedule_id="1.2.99999")

    result = HederaParameterNormaliser.normalise_sign_schedule_transaction(params)

    assert isinstance(result.schedule_id, ScheduleId)
    assert str(result.schedule_id) == "1.2.99999"


def test_normalise_with_dict_input():
    """Test that dict input is properly parsed through Pydantic validation."""
    params_dict = {"schedule_id": "0.0.54321"}

    result = HederaParameterNormaliser.normalise_sign_schedule_transaction(params_dict)

    assert isinstance(result.schedule_id, ScheduleId)
    assert str(result.schedule_id) == "0.0.54321"


def test_normalise_missing_schedule_id():
    """Test that missing schedule_id raises a validation error."""
    params_dict = {}

    with pytest.raises(ValueError, match="Invalid parameters"):
        HederaParameterNormaliser.normalise_sign_schedule_transaction(params_dict)


def test_normalise_invalid_schedule_id_format():
    """Test that invalid schedule ID format raises an error."""
    params = SignScheduleTransactionToolParameters(schedule_id="invalid-id")

    with pytest.raises(Exception):  # ScheduleId.from_string will raise
        HederaParameterNormaliser.normalise_sign_schedule_transaction(params)


def test_normalise_empty_schedule_id():
    """Test that empty schedule ID raises a validation error."""
    params_dict = {"schedule_id": ""}

    with pytest.raises(Exception):  # ScheduleId.from_string will raise on empty string
        HederaParameterNormaliser.normalise_sign_schedule_transaction(params_dict)


@pytest.mark.parametrize(
    "schedule_id_str",
    [
        "0.0.1",
        "0.0.100",
        "0.0.999999",
        "0.0.123456789",
    ],
)
def test_normalise_various_valid_schedule_ids(schedule_id_str):
    """Test normalization with various valid schedule ID formats."""
    params = SignScheduleTransactionToolParameters(schedule_id=schedule_id_str)

    result = HederaParameterNormaliser.normalise_sign_schedule_transaction(params)

    assert isinstance(result.schedule_id, ScheduleId)
    assert str(result.schedule_id) == schedule_id_str
