"""Unit tests for get topic messages query parameter normalization.

This module tests the HederaParameterNormaliser.normalise_get_topic_messages method
to ensure correct handling of topic message query parameters.
"""

from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import (
    TopicMessagesQueryParameters,
)


def test_normalises_topic_messages_params_with_required_topic_id():
    """Should normalize params with only the required topic_id."""
    params = TopicMessagesQueryParameters(topic_id="0.0.1234")

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.1234"
    assert result["limit"] == 100  # Default limit
    assert result["lowerTimestamp"] == ""
    assert result["upperTimestamp"] == ""


def test_normalises_topic_messages_params_with_custom_limit():
    """Should use the provided limit instead of the default."""
    params = TopicMessagesQueryParameters(topic_id="0.0.5555", limit=50)

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.5555"
    assert result["limit"] == 50
    assert result["lowerTimestamp"] == ""
    assert result["upperTimestamp"] == ""


def test_normalises_topic_messages_params_with_zero_limit_uses_default():
    """Should use default limit (100) when limit is 0."""
    params = TopicMessagesQueryParameters(topic_id="0.0.6666", limit=0)

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.6666"
    assert result["limit"] == 100  # Falsy value defaults to 100


def test_normalises_topic_messages_params_with_none_limit_uses_default():
    """Should use default limit (100) when limit is None."""
    params = TopicMessagesQueryParameters(topic_id="0.0.7777", limit=None)

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.7777"
    assert result["limit"] == 100


def test_normalises_topic_messages_params_preserves_topic_id_format():
    """Should preserve the topic ID format as-is."""
    params = TopicMessagesQueryParameters(topic_id="0.0.99999999")

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.99999999"


def test_normalises_topic_messages_params_with_dict_input():
    """Should normalize params when passed as a dictionary (schema parsing)."""
    params = {"topic_id": "0.0.8888", "limit": 25}

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.8888"
    assert result["limit"] == 25
    assert result["lowerTimestamp"] == ""
    assert result["upperTimestamp"] == ""


def test_normalises_topic_messages_params_with_start_time():
    """Should convert start_time to Hedera Mirror Node timestamp format."""
    params = TopicMessagesQueryParameters(
        topic_id="0.0.1111",
        start_time="2024-01-01T00:00:00Z",
    )

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.1111"
    # 2024-01-01T00:00:00Z = 1704067200 seconds since epoch
    assert result["lowerTimestamp"] == "1704067200.000000000"
    assert result["upperTimestamp"] == ""


def test_normalises_topic_messages_params_with_end_time():
    """Should convert end_time to Hedera Mirror Node timestamp format."""
    params = TopicMessagesQueryParameters(
        topic_id="0.0.2222",
        end_time="2024-12-31T23:59:59Z",
    )

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.2222"
    assert result["lowerTimestamp"] == ""
    # 2024-12-31T23:59:59Z = 1735689599 seconds since epoch
    assert result["upperTimestamp"] == "1735689599.000000000"


def test_normalises_topic_messages_params_with_both_timestamps():
    """Should convert both start_time and end_time to Hedera Mirror Node timestamp format."""
    params = TopicMessagesQueryParameters(
        topic_id="0.0.3333",
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-12-31T23:59:59Z",
    )

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.3333"
    assert result["lowerTimestamp"] == "1704067200.000000000"
    assert result["upperTimestamp"] == "1735689599.000000000"


def test_normalises_topic_messages_params_with_timezone_offset():
    """Should handle ISO 8601 timestamps with timezone offsets."""
    params = TopicMessagesQueryParameters(
        topic_id="0.0.4444",
        start_time="2024-06-15T12:00:00+02:00",  # Noon in UTC+2 = 10:00 UTC
    )

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.4444"
    # 2024-06-15T10:00:00Z = 1718445600 seconds since epoch
    assert result["lowerTimestamp"] == "1718445600.000000000"


def test_normalises_topic_messages_params_without_timestamps():
    """Should set timestamps to empty strings when not provided."""
    params = TopicMessagesQueryParameters(topic_id="0.0.5555")

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    assert result["topic_id"] == "0.0.5555"
    assert result["lowerTimestamp"] == ""
    assert result["upperTimestamp"] == ""
