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


def test_normalises_topic_messages_params_optional_timestamps_are_empty():
    """Should set timestamps to empty strings (not None) as per service contract."""
    params = TopicMessagesQueryParameters(
        topic_id="0.0.1111",
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-12-31T23:59:59Z",
    )

    result = HederaParameterNormaliser.normalise_get_topic_messages(params)

    # Note: Current implementation sets these to empty strings regardless of input
    # This test documents the current behavior
    assert result["topic_id"] == "0.0.1111"
    assert result["lowerTimestamp"] == ""
    assert result["upperTimestamp"] == ""
