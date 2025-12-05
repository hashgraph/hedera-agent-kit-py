import pytest
from unittest.mock import patch, ANY
from datetime import datetime, timezone

from hiero_sdk_python import TopicId, PublicKey, PrivateKey, AccountId
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import UpdateTopicParameters

# Constants
TEST_TOPIC_ID = "0.0.123"
TEST_USER_KEY = PrivateKey.generate_ed25519().public_key()


@pytest.fixture
def mock_context():
    return Context(account_id="0.0.5005")


@pytest.fixture
def mock_client():
    class MockClient:
        operator_private_key = PrivateKey.generate_ed25519()
        operator_public_key = operator_private_key.public_key

    return MockClient()


@pytest.mark.asyncio
async def test_normalise_topic_only(mock_context, mock_client):
    """Only topic_id provided."""
    params = UpdateTopicParameters(topic_id=TEST_TOPIC_ID)

    with patch.object(
        HederaParameterNormaliser, "resolve_key", return_value=None
    ) as mock_resolve:
        res = await HederaParameterNormaliser.normalise_update_topic(
            params, mock_context, mock_client
        )

        assert isinstance(res.topic_id, TopicId)
        assert str(res.topic_id) == TEST_TOPIC_ID

        # UPDATED: Check against the correct output attribute names
        assert res.memo is None
        assert res.admin_key is None
        assert res.submit_key is None
        assert res.expiration_time is None
        assert res.auto_renew_account is None
        assert res.auto_renew_period is None


@pytest.mark.asyncio
async def test_normalise_topic_with_optional_fields(mock_context, mock_client):
    """Topic with memo, auto-renew, expiration."""
    iso_time = "2024-01-01T00:00:00Z"
    params = UpdateTopicParameters(
        topic_id="0.0.321",
        topic_memo="Test memo",
        auto_renew_account_id="0.0.789",
        auto_renew_period=3600,
        expiration_time=iso_time,
    )

    with patch.object(HederaParameterNormaliser, "resolve_key", return_value=None):
        res = await HederaParameterNormaliser.normalise_update_topic(
            params, mock_context, mock_client
        )

        assert str(res.topic_id) == "0.0.321"

        # UPDATED: 'topic_memo' becomes 'memo'
        assert res.memo == "Test memo"

        # UPDATED: 'auto_renew_account_id' becomes 'auto_renew_account' (AccountId object)
        assert isinstance(res.auto_renew_account, AccountId)
        assert str(res.auto_renew_account) == "0.0.789"

        assert res.auto_renew_period == 3600
        assert isinstance(res.expiration_time, datetime)
        assert res.expiration_time.isoformat() == "2024-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_normalise_keys(mock_context, mock_client):
    """Resolve admin_key=True and submit_key as string."""
    private_key = PrivateKey.generate_ed25519()
    new_key: PublicKey = private_key.public_key()

    params = UpdateTopicParameters(
        topic_id="0.0.555",
        admin_key=True,
        submit_key=new_key.to_string_der(),
    )

    with patch.object(
        HederaParameterNormaliser,
        "resolve_key",
        side_effect=lambda val, default: (
            TEST_USER_KEY if val is True else PublicKey.from_string(val)
        ),
    ) as mock_resolve:
        res = await HederaParameterNormaliser.normalise_update_topic(
            params, mock_context, mock_client
        )

        mock_resolve.assert_any_call(True, ANY)
        mock_resolve.assert_any_call(new_key.to_string_der(), ANY)

        assert isinstance(res.admin_key, PublicKey)
        assert str(res.admin_key) == str(TEST_USER_KEY)
        assert isinstance(res.submit_key, PublicKey)
        assert str(res.submit_key) == str(new_key)


@pytest.mark.asyncio
async def test_omits_keys_if_not_provided(mock_context, mock_client):
    """Optional keys are None if not provided."""
    params = UpdateTopicParameters(topic_id="0.0.999")

    with patch.object(HederaParameterNormaliser, "resolve_key", return_value=None):
        res = await HederaParameterNormaliser.normalise_update_topic(
            params, mock_context, mock_client
        )

        assert str(res.topic_id) == "0.0.999"
        assert res.admin_key is None
        assert res.submit_key is None
        # UPDATED: 'topic_memo' -> 'memo'
        assert res.memo is None
        assert res.auto_renew_period is None
        assert res.expiration_time is None


@pytest.mark.asyncio
async def test_expiration_as_datetime(mock_context, mock_client):
    """Expiration passed as datetime."""
    expiration = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)
    params = UpdateTopicParameters(topic_id="0.0.1010", expiration_time=expiration)

    with patch.object(HederaParameterNormaliser, "resolve_key", return_value=None):
        res = await HederaParameterNormaliser.normalise_update_topic(
            params, mock_context, mock_client
        )

        assert isinstance(res.expiration_time, datetime)
        assert res.expiration_time.isoformat() == expiration.isoformat()
