from __future__ import annotations

from hiero_sdk_python import Client

from ..audit_entry import AuditEntry
from ...hol.hcs1_file_builder import Hcs1FileBuilder
from ...hol.hcs2_registry_builder import Hcs2RegistryBuilder
from ...hol.constants import HCS2_REGISTRY_TYPE


class HolAuditWriter:
    """Writes audit entries using HCS-1 file storage and HCS-2 registry indexing."""

    def __init__(self, client: Client):
        self._client = client
        self._session_id: str = ""

    def set_session_id(self, session_id: str) -> None:
        self._session_id = session_id

    async def initialize(self) -> str:
        tx = Hcs2RegistryBuilder.create_registry(
            submit_key=self._client.operator_private_key.public_key(),
            registry_type=HCS2_REGISTRY_TYPE["INDEXED"],
            ttl=0,
        )

        receipt = tx.execute(self._client)
        if not receipt.topic_id:
            raise RuntimeError("Failed to create session topic")

        return str(receipt.topic_id)

    async def write(self, entry: AuditEntry) -> None:
        file_result = Hcs1FileBuilder.create_file(
            content=entry.model_dump_json(),
            submit_key=self._client.operator_private_key.public_key(),
        )

        receipt = file_result.topic_transaction.execute(self._client)
        if not receipt.topic_id:
            raise RuntimeError("Failed to create HCS-1 topic for audit entry")

        entry_topic_id = str(receipt.topic_id)

        message_txs = file_result.build_message_transactions(entry_topic_id)
        for message_tx in message_txs:
            message_tx.execute(self._client)

        register_tx = Hcs2RegistryBuilder.register_entry(
            registry_topic_id=self._session_id,
            target_topic_id=entry_topic_id,
        )
        register_tx.execute(self._client)
