from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_entry import (
    AuditEntry,
    build_audit_entry,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.constants import (
    HOL_AUDIT_ENTRY_SOURCE,
    HOL_AUDIT_ENTRY_TYPE,
    HOL_AUDIT_ENTRY_VERSION,
)


class TestBuildAuditEntry:
    def test_build_with_all_fields(self):
        entry = build_audit_entry(
            tool="transfer_hbar",
            params={"amount": 100, "to": "0.0.456"},
            result={
                "raw": {"status": "SUCCESS", "transactionId": "0.0.1@123"},
                "message": "Transfer of 100 HBAR succeeded",
            },
        )

        assert entry.type == HOL_AUDIT_ENTRY_TYPE
        assert entry.version == HOL_AUDIT_ENTRY_VERSION
        assert entry.source == HOL_AUDIT_ENTRY_SOURCE
        assert entry.tool == "transfer_hbar"
        assert entry.params == {"amount": 100, "to": "0.0.456"}
        assert entry.result.raw == {"status": "SUCCESS", "transactionId": "0.0.1@123"}
        assert entry.result.message == "Transfer of 100 HBAR succeeded"

    def test_type_is_constant(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.type == HOL_AUDIT_ENTRY_TYPE

    def test_version_is_constant(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.version == HOL_AUDIT_ENTRY_VERSION

    def test_source_is_constant(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.source == HOL_AUDIT_ENTRY_SOURCE

    def test_timestamp_is_iso_8601(self):
        before = datetime.now(timezone.utc).isoformat()
        entry = build_audit_entry(tool="test_tool")
        after = datetime.now(timezone.utc).isoformat()

        assert entry.timestamp >= before
        assert entry.timestamp <= after
        # Verify it's a valid ISO 8601 timestamp
        datetime.fromisoformat(entry.timestamp)

    def test_default_params_is_empty_dict(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.params == {}

    def test_default_result_raw_is_empty_dict(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.result.raw == {}

    def test_default_result_message_is_none(self):
        entry = build_audit_entry(tool="test_tool")
        assert entry.result.message is None

    def test_result_raw_defaults_when_result_has_only_message(self):
        entry = build_audit_entry(
            tool="test_tool",
            result={"message": "some message"},
        )
        assert entry.result.raw == {}

    def test_result_message_defaults_when_result_has_only_raw(self):
        entry = build_audit_entry(
            tool="test_tool",
            result={"raw": {"foo": "bar"}},
        )
        assert entry.result.message is None


class TestAuditEntryValidation:
    def test_accept_valid_entry(self):
        entry = build_audit_entry(
            tool="test_tool",
            params={"key": "value"},
            result={"raw": {"status": "OK"}, "message": "done"},
        )
        # Should not raise
        AuditEntry.model_validate(entry.model_dump())

    def test_reject_wrong_type_literal(self):
        entry_data = build_audit_entry(tool="test_tool").model_dump()
        entry_data["type"] = "wrong-type"

        with pytest.raises(ValidationError):
            AuditEntry.model_validate(entry_data)

    def test_reject_wrong_version_literal(self):
        entry_data = build_audit_entry(tool="test_tool").model_dump()
        entry_data["version"] = "2.0"

        with pytest.raises(ValidationError):
            AuditEntry.model_validate(entry_data)

    def test_reject_missing_tool_field(self):
        entry_data = build_audit_entry(tool="test_tool").model_dump()
        del entry_data["tool"]

        with pytest.raises(ValidationError):
            AuditEntry.model_validate(entry_data)
