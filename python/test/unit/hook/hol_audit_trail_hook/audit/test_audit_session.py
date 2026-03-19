import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_entry import AuditEntry, AuditEntryResult
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_session import AuditSession


def make_entry(tool: str = "test_tool") -> AuditEntry:
    return AuditEntry(
        timestamp="2024-01-01T00:00:00+00:00",
        tool=tool,
        params={"amount": 100},
        result=AuditEntryResult(raw={"status": "SUCCESS"}, message="ok"),
    )


@pytest.fixture
def mock_writer():
    writer = MagicMock()
    writer.initialize = AsyncMock(return_value="0.0.999")
    writer.write = AsyncMock(return_value=None)
    # Plain writer: no set_session_id
    if hasattr(writer, "set_session_id"):
        del writer.set_session_id
    return writer


@pytest.fixture
def session_aware_writer():
    writer = MagicMock()
    writer.initialize = AsyncMock(return_value="0.0.999")
    writer.write = AsyncMock(return_value=None)
    writer.set_session_id = MagicMock()
    return writer


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestAuditSession:
    async def test_returns_null_session_id_when_constructed_without_one(self, mock_writer):
        session = AuditSession(mock_writer)
        assert session.get_session_id() is None

    async def test_returns_provided_session_id(self, mock_writer):
        session = AuditSession(mock_writer, "0.0.666")
        assert session.get_session_id() == "0.0.666"

    async def test_initializes_writer_and_writes_entry(self, mock_writer):
        session = AuditSession(mock_writer)
        entry = make_entry()

        await session.write_entry(entry)

        mock_writer.initialize.assert_awaited_once()
        assert session.get_session_id() == "0.0.999"
        mock_writer.write.assert_awaited_with(entry)

    async def test_delegates_write_to_writer(self, mock_writer):
        session = AuditSession(mock_writer)
        entry = make_entry()

        await session.write_entry(entry)

        mock_writer.write.assert_awaited_once_with(entry)

    async def test_skips_initialization_when_session_id_provided(self, mock_writer):
        session = AuditSession(mock_writer, "0.0.666")
        entry = make_entry()

        await session.write_entry(entry)

        mock_writer.initialize.assert_not_awaited()
        assert session.get_session_id() == "0.0.666"
        mock_writer.write.assert_awaited_with(entry)

    async def test_initializes_only_once_on_concurrent_writes(self, mock_writer):
        async def slow_init():
            await asyncio.sleep(0.05)
            return "0.0.999"

        mock_writer.initialize = AsyncMock(side_effect=slow_init)

        session = AuditSession(mock_writer)
        entry = make_entry()

        await asyncio.gather(
            session.write_entry(entry),
            session.write_entry(entry),
            session.write_entry(entry),
        )

        mock_writer.initialize.assert_awaited_once()

    async def test_propagates_write_errors(self, mock_writer):
        mock_writer.write = AsyncMock(side_effect=RuntimeError("Write failed"))

        session = AuditSession(mock_writer)
        entry = make_entry()

        with pytest.raises(RuntimeError, match="Write failed"):
            await session.write_entry(entry)

    async def test_propagates_initialization_errors(self, mock_writer):
        mock_writer.initialize = AsyncMock(side_effect=RuntimeError("Init failed"))

        session = AuditSession(mock_writer)
        entry = make_entry()

        with pytest.raises(RuntimeError, match="Init failed"):
            await session.write_entry(entry)


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestAuditSessionWithSessionAwareWriter:
    async def test_calls_set_session_id_on_construction_with_session_id(self, session_aware_writer):
        AuditSession(session_aware_writer, "0.0.666")

        session_aware_writer.set_session_id.assert_called_once_with("0.0.666")

    async def test_does_not_call_set_session_id_without_session_id(self, session_aware_writer):
        AuditSession(session_aware_writer)

        session_aware_writer.set_session_id.assert_not_called()

    async def test_calls_set_session_id_after_initialization(self, session_aware_writer):
        session = AuditSession(session_aware_writer)
        entry = make_entry()

        await session.write_entry(entry)

        session_aware_writer.set_session_id.assert_called_once_with("0.0.999")

    async def test_does_not_call_set_session_id_on_plain_writer(self, mock_writer):
        session = AuditSession(mock_writer)
        entry = make_entry()

        await session.write_entry(entry)

        assert not hasattr(mock_writer, "set_session_id")
