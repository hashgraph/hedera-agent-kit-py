from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Callable, List, Optional

import brotli
from hiero_sdk_python import TopicCreateTransaction, TopicId, TopicMessageSubmitTransaction
from hiero_sdk_python.crypto.public_key import PublicKey

from .constants import HCS1_CHUNK_SIZE


@dataclass
class Hcs1FileResult:
    topic_transaction: TopicCreateTransaction
    build_message_transactions: Callable[[str], List[TopicMessageSubmitTransaction]]


class Hcs1FileBuilder:
    @staticmethod
    def create_file(
        content: str,
        submit_key: Optional[PublicKey] = None,
        mime_type: Optional[str] = None,
    ) -> Hcs1FileResult:
        effective_mime_type = mime_type or "application/json"
        content_bytes = content.encode("utf-8")

        content_hash = hashlib.sha256(content_bytes).hexdigest()

        compressed = brotli.compress(content_bytes, quality=11)
        base64_data = base64.b64encode(compressed).decode("ascii")

        data_uri = f"data:{effective_mime_type};base64,{base64_data}"

        chunks: List[str] = []
        for i in range(0, len(data_uri), HCS1_CHUNK_SIZE):
            chunks.append(data_uri[i : i + HCS1_CHUNK_SIZE])

        topic_memo = f"{content_hash}:brotli:base64"

        topic_transaction = TopicCreateTransaction(
            memo=topic_memo,
            submit_key=submit_key,
        )

        def build_message_transactions(topic_id: str) -> List[TopicMessageSubmitTransaction]:
            txs: List[TopicMessageSubmitTransaction] = []
            for index, chunk in enumerate(chunks):
                chunk_message = json.dumps({"o": index, "c": chunk}, separators=(",", ":"))
                tx = TopicMessageSubmitTransaction(
                    topic_id=TopicId.from_string(topic_id),
                    message=chunk_message,
                )
                txs.append(tx)
            return txs

        return Hcs1FileResult(
            topic_transaction=topic_transaction,
            build_message_transactions=build_message_transactions,
        )
