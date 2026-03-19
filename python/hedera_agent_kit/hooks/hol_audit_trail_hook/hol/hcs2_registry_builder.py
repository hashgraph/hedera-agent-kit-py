from __future__ import annotations

import json
from typing import Any, Dict, Optional

from hiero_sdk_python import TopicCreateTransaction, TopicId, TopicMessageSubmitTransaction
from hiero_sdk_python.crypto.public_key import PublicKey

from .constants import HCS2_OPERATION, HCS2_PROTOCOL, HCS2_REGISTRY_TYPE


class Hcs2RegistryBuilder:
    @staticmethod
    def create_registry(
        submit_key: Optional[PublicKey] = None,
        registry_type: Optional[int] = None,
        ttl: Optional[int] = None,
    ) -> TopicCreateTransaction:
        effective_registry_type = registry_type if registry_type is not None else HCS2_REGISTRY_TYPE["INDEXED"]
        effective_ttl = ttl if ttl is not None else 0

        memo = f"{HCS2_PROTOCOL}:{effective_registry_type}:{effective_ttl}"

        return TopicCreateTransaction(
            memo=memo,
            submit_key=submit_key,
        )

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
