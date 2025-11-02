from typing import TypedDict, List, Optional

from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types.common import (
    MirrornodeKeyInfo,
)


class TopicMessage(TypedDict):
    topic_id: str
    message: str
    consensus_timestamp: str


class TopicMessagesResponse(TypedDict):
    topic_id: str
    messages: List[TopicMessage]


class TopicMessagesQueryParams(TypedDict):
    topic_id: str
    lowerTimestamp: str
    upperTimestamp: str
    limit: int


class TopicInfo(TypedDict, total=False):
    topic_id: Optional[str]
    memo: Optional[str]
    admin_key: Optional[MirrornodeKeyInfo]
    submit_key: Optional[MirrornodeKeyInfo]
    auto_renew_account: Optional[str]
    auto_renew_period: Optional[int]
    created_timestamp: Optional[str]
    deleted: Optional[bool]
    sequence_number: Optional[int]
    running_hash: Optional[str]
    running_hash_version: Optional[int]
