from datetime import datetime
from typing import Optional, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, Duration, Timestamp, TopicId
from hiero_sdk_python.hapi.services import basic_types_pb2
from pydantic import Field

from hedera_agent_kit_py.shared.parameter_schemas import (
    OptionalScheduledTransactionParams,
    OptionalScheduledTransactionParamsNormalised,
    BaseModelWithArbitraryTypes,
)


class GetTopicInfoParameters(BaseModelWithArbitraryTypes):
    topic_id: Annotated[str, Field(description="The topic ID to query.")]


class DeleteTopicParameters(BaseModelWithArbitraryTypes):
    topic_id: Annotated[str, Field(description="The ID of the topic to delete.")]


class DeleteTopicParametersNormalised(BaseModelWithArbitraryTypes):
    topic_id: TopicId


class CreateTopicParameters(BaseModelWithArbitraryTypes):
    is_submit_key: Annotated[
        bool, Field(description="Whether to set a submit key for the topic (optional).")
    ] = False

    topic_memo: Annotated[
        Optional[str], Field(description="Memo for the topic (optional).")
    ] = None

    transaction_memo: Annotated[
        Optional[str],
        Field(description="An optional memo to include on the submitted transaction."),
    ] = None


class CreateTopicParametersNormalised(BaseModelWithArbitraryTypes):
    memo: Optional[str] = None
    submit_key: Optional[PublicKey] = None
    admin_key: Optional[PublicKey] = None
    transaction_memo: Optional[str] = None


class SubmitTopicMessageParameters(OptionalScheduledTransactionParams):
    topic_id: Annotated[
        str, Field(description="The ID of the topic to submit the message to.")
    ]

    message: Annotated[str, Field(description="The message to submit to the topic.")]

    transaction_memo: Annotated[
        Optional[str],
        Field(
            description="An optional memo to include with the submitted transaction."
        ),
    ] = None


class SubmitTopicMessageParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    topic_id: TopicId
    message: Optional[str] = None

    transaction_memo: Optional[str] = None


class TopicMessagesQueryParameters(BaseModelWithArbitraryTypes):
    topic_id: Annotated[str, Field(description="The topic ID to query.")]

    start_time: Annotated[
        Optional[str], Field(description="Start timestamp (ISO 8601 format).")
    ] = None

    end_time: Annotated[
        Optional[str], Field(description="End timestamp (ISO 8601 format).")
    ] = None

    limit: Annotated[
        Optional[int], Field(description="Limit the number of messages returned.")
    ] = None


class UpdateTopicParameters(BaseModelWithArbitraryTypes):
    topic_id: Annotated[
        str, Field(description="The ID of the topic to update (e.g., 0.0.12345).")
    ]

    topic_memo: Annotated[
        Optional[str], Field(description="Optional new memo for the topic.")
    ] = None

    admin_key: Annotated[
        Optional[Union[bool, str]],
        Field(
            description=(
                "New admin key. Pass boolean `True` to use the operator/user key, "
                "or provide a Hedera-compatible public key string."
            ),
        ),
    ] = None

    submit_key: Annotated[
        Optional[Union[bool, str]],
        Field(
            description=(
                "New submit key. Pass boolean `True` to use the operator/user key, "
                "or provide a Hedera-compatible public key string."
            ),
        ),
    ] = None

    auto_renew_account_id: Annotated[
        Optional[str],
        Field(
            description="Account to automatically pay for topic renewal (Hedera account ID)."
        ),
    ] = None

    auto_renew_period: Annotated[
        Optional[int], Field(description="Auto renew period in seconds.")
    ] = None

    expiration_time: Annotated[
        Optional[Union[str, datetime]],
        Field(
            description="New expiration time for the topic (ISO string or datetime)."
        ),
    ] = None


class UpdateTopicParametersNormalised(BaseModelWithArbitraryTypes):
    topic_id: TopicId

    memo: Optional[str] = None

    admin_key: Optional[PublicKey] = None
    submit_key: Optional[PublicKey] = None

    auto_renew_account: Annotated[
        Optional[AccountId],
        Field(description="Account paying for topic renewal."),
    ] = None

    auto_renew_period: Optional[int] = None  # Seconds

    expiration_time: Optional[datetime] = None
