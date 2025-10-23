from datetime import datetime
from typing import Optional, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, TopicId
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


## TODO: adapt to the Python SDK Transaction Constructor impl
class DeleteTopicParametersNormalised(BaseModelWithArbitraryTypes):
    topic_id: Annotated[
        TopicId, Field(description="The ID of the topic to delete (normalized).")
    ]


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


## TODO: adapt to the Python SDK Transaction Constructor impl
class CreateTopicParametersNormalised(CreateTopicParameters):
    auto_renew_account_id: Annotated[
        Union[str, AccountId],
        Field(description="The auto-renew account for the topic."),
    ]

    submit_key: Annotated[
        Optional[PublicKey], Field(description="The submit key of the topic.")
    ] = None

    admin_key: Annotated[
        Optional[PublicKey], Field(description="The admin key of the topic.")
    ] = None


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


## TODO: adapt to the Python SDK Transaction Constructor impl
class SubmitTopicMessageParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    topic_id: Annotated[
        TopicId,
        Field(description="The ID of the topic to submit the message to (normalized)."),
    ]

    message: Annotated[str, Field(description="The message to submit to the topic.")]

    transaction_memo: Annotated[
        Optional[str],
        Field(description="An optional memo to include with the transaction."),
    ] = None


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


## TODO: adapt to the Python SDK Transaction Constructor impl
class UpdateTopicParametersNormalised(BaseModelWithArbitraryTypes):
    topic_id: Annotated[TopicId, Field(description="The ID of the topic to update.")]

    topic_memo: Annotated[
        Optional[str], Field(description="New memo for the topic.")
    ] = None

    admin_key: Annotated[
        Optional[PublicKey], Field(description="Resolved admin key.")
    ] = None

    submit_key: Annotated[
        Optional[PublicKey], Field(description="Resolved submit key.")
    ] = None

    auto_renew_account_id: Annotated[
        Optional[Union[str, AccountId]],
        Field(description="Account paying for topic renewal."),
    ] = None

    auto_renew_period: Annotated[
        Optional[int], Field(description="Auto renew period in seconds.")
    ] = None

    expiration_time: Annotated[
        Optional[datetime], Field(description="New expiration time for the topic.")
    ] = None
