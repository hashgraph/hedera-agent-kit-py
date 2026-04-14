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
    writer.write = AsyncMock(return_value=None)
    # Plain writer: no set_session_id
    if hasattr(writer, "set_session_id"):
        del writer.set_session_id
    return writer


@pytest.fixture
def session_aware_writer():
    writer = MagicMock()
    writer.write = AsyncMock(return_value=None)
    writer.set_session_id = MagicMock()
    return writer


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestAuditSession:
    async def test_returns_provided_session_id(self, mock_writer):
        session = AuditSession(mock_writer, "0.0.666")
        assert session.get_session_id() == "0.0.666"

    async def test_delegates_write_to_writer(self, mock_writer):
        session = AuditSession(mock_writer, "0.0.666")
        entry = make_entry()

        await session.write_entry(entry)

        mock_writer.write.assert_awaited_once_with(entry)

    async def test_propagates_write_errors(self, mock_writer):
        mock_writer.write = AsyncMock(side_effect=RuntimeError("Write failed"))

        session = AuditSession(mock_writer, "0.0.666")
        entry = make_entry()

        with pytest.raises(RuntimeError, match="Write failed"):
            await session.write_entry(entry)


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestAuditSessionWithSessionAwareWriter:
    async def test_calls_set_session_id_on_construction_with_session_id(self, session_aware_writer):
        AuditSession(session_aware_writer, "0.0.666")

        session_aware_writer.set_session_id.assert_called_once_with("0.0.666")

    async def test_does_not_call_set_session_id_on_plain_writer(self, mock_writer):
        session = AuditSession(mock_writer, "0.0.666")
        entry = make_entry()

        await session.write_entry(entry)

        assert not hasattr(mock_writer, "set_session_id")
