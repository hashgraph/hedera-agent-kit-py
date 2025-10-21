from datetime import datetime
from typing import Optional, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, TopicId
from pydantic import BaseModel, Field

from hedera_agent_kit_py.shared.parameter_schemas import OptionalScheduledTransactionParams, \
    OptionalScheduledTransactionParamsNormalised


class GetTopicInfoParameters(BaseModel):
    topic_id: Annotated[
        str,
        Field(description="The topic ID to query.")
    ]


class DeleteTopicParameters(BaseModel):
    topic_id: Annotated[
        str,
        Field(description="The ID of the topic to delete.")
    ]


## TODO: adapt to the Python SDK Transaction Constructor impl
class DeleteTopicParametersNormalised(BaseModel):
    topic_id: Annotated[
        TopicId,
        Field(description="The ID of the topic to delete (normalized).")
    ]


class CreateTopicParameters(BaseModel):
    is_submit_key: Annotated[
        Optional[bool],
        Field(default=False, description="Whether to set a submit key for the topic (optional).")
    ]

    topic_memo: Annotated[
        Optional[str],
        Field(default=None, description="Memo for the topic (optional).")
    ]

    transaction_memo: Annotated[
        Optional[str],
        Field(default=None, description="An optional memo to include on the submitted transaction.")
    ]


## TODO: adapt to the Python SDK Transaction Constructor impl
class CreateTopicParametersNormalised(CreateTopicParameters):
    auto_renew_account_id: Annotated[
        Union[str, AccountId],
        Field(description="The auto-renew account for the topic.")
    ]

    submit_key: Annotated[
        Optional[PublicKey],
        Field(default=None, description="The submit key of the topic.")
    ]

    admin_key: Annotated[
        Optional[PublicKey],
        Field(default=None, description="The admin key of the topic.")
    ]


class SubmitTopicMessageParameters(OptionalScheduledTransactionParams):
    topic_id: Annotated[
        str,
        Field(description="The ID of the topic to submit the message to.")
    ]

    message: Annotated[
        str,
        Field(description="The message to submit to the topic.")
    ]

    transaction_memo: Annotated[
        Optional[str],
        Field(default=None, description="An optional memo to include with the submitted transaction.")
    ]


## TODO: adapt to the Python SDK Transaction Constructor impl
class SubmitTopicMessageParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    topic_id: Annotated[
        TopicId,
        Field(description="The ID of the topic to submit the message to (normalized).")
    ]

    message: Annotated[
        str,
        Field(description="The message to submit to the topic.")
    ]

    transaction_memo: Annotated[
        Optional[str],
        Field(default=None, description="An optional memo to include with the transaction.")
    ]


class TopicMessagesQueryParameters(BaseModel):
    topic_id: Annotated[
        str,
        Field(description="The topic ID to query.")
    ]

    start_time: Annotated[
        Optional[str],
        Field(default=None, description="Start timestamp (ISO 8601 format).")
    ]

    end_time: Annotated[
        Optional[str],
        Field(default=None, description="End timestamp (ISO 8601 format).")
    ]

    limit: Annotated[
        Optional[int],
        Field(default=None, description="Limit the number of messages returned.")
    ]


class UpdateTopicParameters(BaseModel):
    topic_id: Annotated[
        str,
        Field(description="The ID of the topic to update (e.g., 0.0.12345).")
    ]

    topic_memo: Annotated[
        Optional[str],
        Field(default=None, description="Optional new memo for the topic.")
    ]

    admin_key: Annotated[
        Optional[Union[bool, str]],
        Field(
            default=None,
            description=(
                "New admin key. Pass boolean `True` to use the operator/user key, "
                "or provide a Hedera-compatible public key string."
            ),
        ),
    ]

    submit_key: Annotated[
        Optional[Union[bool, str]],
        Field(
            default=None,
            description=(
                "New submit key. Pass boolean `True` to use the operator/user key, "
                "or provide a Hedera-compatible public key string."
            ),
        ),
    ]

    auto_renew_account_id: Annotated[
        Optional[str],
        Field(default=None, description="Account to automatically pay for topic renewal (Hedera account ID).")
    ]

    auto_renew_period: Annotated[
        Optional[int],
        Field(default=None, description="Auto renew period in seconds.")
    ]

    expiration_time: Annotated[
        Optional[Union[str, datetime]],
        Field(default=None, description="New expiration time for the topic (ISO string or datetime).")
    ]


## TODO: adapt to the Python SDK Transaction Constructor impl
class UpdateTopicParametersNormalised(BaseModel):
    topic_id: Annotated[
        TopicId,
        Field(description="The ID of the topic to update.")
    ]

    topic_memo: Annotated[
        Optional[str],
        Field(default=None, description="New memo for the topic.")
    ]

    admin_key: Annotated[
        Optional[PublicKey],
        Field(default=None, description="Resolved admin key.")
    ]

    submit_key: Annotated[
        Optional[PublicKey],
        Field(default=None, description="Resolved submit key.")
    ]

    auto_renew_account_id: Annotated[
        Optional[Union[str, AccountId]],
        Field(default=None, description="Account paying for topic renewal.")
    ]

    auto_renew_period: Annotated[
        Optional[int],
        Field(default=None, description="Auto renew period in seconds.")
    ]

    expiration_time: Annotated[
        Optional[datetime],
        Field(default=None, description="New expiration time for the topic.")
    ]
