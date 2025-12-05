import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python import Client, Network, TopicId
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import (
    SubmitTopicMessageParameters,
    SubmitTopicMessageParametersNormalised,
    SchedulingParams,
)


@pytest.fixture
def mock_context():
    """Provide a mock Context."""
    return Context(account_id="0.0.2001")


@pytest.fixture
def mock_client():
    """Provide a mock Client instance."""
    mock = MagicMock(spec=Client)
    mock.network = Network(network="testnet")
    return mock


@pytest.mark.asyncio
async def test_normalises_with_no_scheduling(mock_context, mock_client):
    """
    Should correctly normalise parameters when no scheduling_params are provided.
    """
    params = SubmitTopicMessageParameters(topic_id="0.0.1234", message="Hello, HCS!")

    with patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params"
    ) as mock_norm_sched:
        result = await HederaParameterNormaliser.normalise_submit_topic_message(
            params, mock_context, mock_client
        )

        assert isinstance(result, SubmitTopicMessageParametersNormalised)
        assert isinstance(result.topic_id, TopicId)
        assert str(result.topic_id) == "0.0.1234"
        assert result.message == "Hello, HCS!"
        assert result.transaction_memo is None
        assert result.scheduling_params is None
        mock_norm_sched.assert_not_called()


@pytest.mark.asyncio
async def test_normalises_with_scheduling_disabled(mock_context, mock_client):
    """
    Should normalise parameters and ignore scheduling_params if is_scheduled is False.
    """
    scheduling_params = SchedulingParams(is_scheduled=False)
    params = SubmitTopicMessageParameters(
        topic_id="0.0.5678",
        message="test message",
        scheduling_params=scheduling_params,
    )

    with patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params"
    ) as mock_norm_sched:
        result = await HederaParameterNormaliser.normalise_submit_topic_message(
            params, mock_context, mock_client
        )

        assert isinstance(result, SubmitTopicMessageParametersNormalised)
        assert str(result.topic_id) == "0.0.5678"
        assert result.scheduling_params is None
        mock_norm_sched.assert_not_called()


@pytest.mark.asyncio
async def test_normalises_with_scheduling_enabled(mock_context, mock_client):
    """
    Should call normalise_scheduled_transaction_params if is_scheduled is True.
    """
    # 1. Define the expected output from the mocked normaliser
    mock_normalised_schedule = ScheduleCreateParams(wait_for_expiry=False)

    # 2. Create the spy mock
    mock_norm_sched_spy = AsyncMock(return_value=mock_normalised_schedule)

    # 3. Define the raw input scheduling parameters
    raw_scheduling_params = SchedulingParams(
        is_scheduled=True, admin_key=False, wait_for_expiry=False
    )

    # 4. Define the main input parameters
    params = SubmitTopicMessageParameters(
        topic_id="0.0.9999",
        message="scheduled message",
        scheduling_params=raw_scheduling_params,
        transaction_memo="tx memo",
    )

    # 5. Patch the normaliser method with the spy
    with patch.object(
        HederaParameterNormaliser,
        "normalise_scheduled_transaction_params",
        mock_norm_sched_spy,
    ):
        result = await HederaParameterNormaliser.normalise_submit_topic_message(
            params, mock_context, mock_client
        )

        assert isinstance(result, SubmitTopicMessageParametersNormalised)
        assert str(result.topic_id) == "0.0.9999"
        assert result.message == "scheduled message"
        assert result.transaction_memo == "tx memo"

        # 6. Check that the normalised schedule params are in the result
        assert result.scheduling_params == mock_normalised_schedule

        # 7. Check that the normaliser spy was called correctly
        mock_norm_sched_spy.assert_called_once_with(
            raw_scheduling_params, mock_context, mock_client
        )


@pytest.mark.asyncio
async def test_raises_value_error_for_invalid_topic_id_format(
    mock_context, mock_client
):
    """
    Should raise ValueError (from TopicId.from_string) if topic_id has an invalid format.
    """
    params = SubmitTopicMessageParameters(topic_id="not-a-real-id", message="test")

    # The parameter will pass Pydantic validation (it's a string)
    # but fail at TopicId.from_string()
    with pytest.raises(ValueError):
        await HederaParameterNormaliser.normalise_submit_topic_message(
            params, mock_context, mock_client
        )
