from __future__ import annotations

import json
from typing import Any, Dict, Optional

from hiero_sdk_python import TopicId, TopicMessageSubmitTransaction

from .constants import HCS2_OPERATION, HCS2_PROTOCOL


class Hcs2RegistryBuilder:
    @staticmethod
    def register_entry(
        registry_topic_id: str,
        target_topic_id: str,
        metadata: Optional[str] = None,
        memo: Optional[str] = None,
    ) -> TopicMessageSubmitTransaction:
        message: Dict[str, Any] = {
            "p": HCS2_PROTOCOL,
            "op": HCS2_OPERATION["REGISTER"],
            "t_id": target_topic_id,
        }

        if metadata is not None:
            message["metadata"] = metadata
        if memo is not None:
            message["m"] = memo

        return TopicMessageSubmitTransaction(
            topic_id=TopicId.from_string(registry_topic_id),
            message=json.dumps(message, separators=(",", ":")),
        )
