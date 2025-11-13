from unittest.mock import patch

import pytest
from hiero_sdk_python import TopicId
from pydantic import ValidationError

from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import DeleteTopicParameters
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver


@pytest.fixture(autouse=True)
def mock_resolvers():
    """Mock AccountResolver methods globally for tests."""
    with patch.object(
        AccountResolver,
        "is_hedera_address",
        side_effect=lambda addr: addr is not None
        and addr.count(".") == 2
        and all(p.isdigit() for p in addr.split(".")),
    ) as mock_is_addr:
        yield mock_is_addr


def test_normalise_delete_topic_valid_id(mock_resolvers):
    """Should correctly normalise parameters with a valid topic_id."""
    params = DeleteTopicParameters(topic_id="0.0.5678")

    result = HederaParameterNormaliser.normalise_delete_topic(params)

    mock_resolvers.assert_called_with("0.0.5678")
    assert isinstance(result.topic_id, TopicId)
    assert str(result.topic_id) == "0.0.5678"


def test_normalise_delete_topic_invalid_id(mock_resolvers):
    """Should raise ValueError when topic_id is not a valid Hedera address."""
    params = DeleteTopicParameters(topic_id="not-a-valid-id")

    # Expect correct ValueError message from implementation
    with pytest.raises(ValueError, match="Topic ID must be a Hedera address"):
        HederaParameterNormaliser.normalise_delete_topic(params)


def test_converts_string_id_to_topicid(mock_resolvers):
    """Should convert a valid string topic_id to a TopicId instance."""
    params = DeleteTopicParameters(topic_id="0.0.12")

    result = HederaParameterNormaliser.normalise_delete_topic(params)

    assert isinstance(result.topic_id, TopicId)
    assert str(result.topic_id) == "0.0.12"
