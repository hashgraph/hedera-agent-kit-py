import json
from unittest.mock import MagicMock, patch

import pytest

from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_entry import AuditEntry, AuditEntryResult
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer import HolAuditWriter


def make_entry() -> AuditEntry:
    return AuditEntry(
        timestamp="2024-01-01T00:00:00+00:00",
        tool="transfer_hbar",
        params={"amount": 100},
        result=AuditEntryResult(raw={"status": "SUCCESS"}, message="ok"),
    )


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.operator_private_key.public_key.return_value = "mock-public-key"
    return client


@pytest.fixture
def mock_registry_builder():
    with patch(
        "hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer.Hcs2RegistryBuilder"
    ) as mock:
        # register_entry returns a transaction mock
        register_tx = MagicMock()
        register_tx.execute.return_value = MagicMock()
        mock.register_entry.return_value = register_tx

        yield mock


@pytest.fixture
def mock_file_builder():
    with patch(
        "hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer.Hcs1FileBuilder"
    ) as mock:
        topic_tx = MagicMock()
        topic_receipt = MagicMock()
        topic_receipt.topic_id = MagicMock()
        topic_receipt.topic_id.__str__ = lambda self: "0.0.1001"
        topic_tx.execute.return_value = topic_receipt

        message_tx = MagicMock()
        message_tx.execute.return_value = MagicMock()

        file_result = MagicMock()
        file_result.topic_transaction = topic_tx
        file_result.build_message_transactions.return_value = [message_tx]
        mock.create_file.return_value = file_result

        yield mock


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestHolAuditWriterSetSessionId:
    async def test_stores_session_id_for_write_operations(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.666")
        entry = make_entry()
        await writer.write(entry)

        mock_registry_builder.register_entry.assert_called_once()
        call_kwargs = mock_registry_builder.register_entry.call_args
        assert call_kwargs[1]["registry_topic_id"] == "0.0.666"


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestHolAuditWriterWrite:
    async def test_creates_hcs1_file_with_json_serialized_entry(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()
        await writer.write(entry)

        mock_file_builder.create_file.assert_called_once()
        call_kwargs = mock_file_builder.create_file.call_args[1]
        assert call_kwargs["content"] == entry.model_dump_json()

    async def test_passes_operator_credentials_to_create_file(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()
        await writer.write(entry)

        call_kwargs = mock_file_builder.create_file.call_args[1]
        assert call_kwargs["submit_key"] == "mock-public-key"

    async def test_submits_chunk_messages(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()
        await writer.write(entry)

        file_result = mock_file_builder.create_file.return_value
        file_result.topic_transaction.execute.assert_called_once()
        for msg_tx in file_result.build_message_transactions.return_value:
            msg_tx.execute.assert_called_once()

    async def test_handles_multiple_chunk_messages(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        msg_txs = [MagicMock() for _ in range(3)]
        for tx in msg_txs:
            tx.execute.return_value = MagicMock()
        mock_file_builder.create_file.return_value.build_message_transactions.return_value = msg_txs

        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()
        await writer.write(entry)

        for tx in msg_txs:
            tx.execute.assert_called_once()

    async def test_registers_entry_in_session_registry(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()
        await writer.write(entry)

        mock_registry_builder.register_entry.assert_called_once_with(
            registry_topic_id="0.0.999",
            target_topic_id="0.0.1001",
        )

    async def test_uses_session_id_as_registry_topic_id(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.666")
        entry = make_entry()
        await writer.write(entry)

        call_kwargs = mock_registry_builder.register_entry.call_args[1]
        assert call_kwargs["registry_topic_id"] == "0.0.666"

    async def test_raises_when_hcs1_topic_has_no_topic_id(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        topic_tx = mock_file_builder.create_file.return_value.topic_transaction
        receipt = MagicMock()
        receipt.topic_id = None
        topic_tx.execute.return_value = receipt

        writer = HolAuditWriter(mock_client)
        writer.set_session_id("0.0.999")
        entry = make_entry()

        with pytest.raises(RuntimeError, match="Failed to create HCS-1 topic for audit entry"):
            await writer.write(entry)
