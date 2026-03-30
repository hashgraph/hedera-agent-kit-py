from unittest.mock import AsyncMock, MagicMock

from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.types import is_session_aware


def test_is_session_aware_returns_true_for_writer_with_set_session_id():
    writer = MagicMock()
    writer.write = AsyncMock()
    writer.set_session_id = MagicMock()

    assert is_session_aware(writer) is True


def test_is_session_aware_returns_false_for_plain_writer():
    writer = MagicMock(spec=["write"])

    assert is_session_aware(writer) is False
