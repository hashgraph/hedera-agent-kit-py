from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.constants import (
    HOL_AUDIT_ENTRY_SOURCE,
    HOL_AUDIT_ENTRY_TYPE,
    HOL_AUDIT_ENTRY_VERSION,
)


def test_hol_audit_entry_version():
    assert HOL_AUDIT_ENTRY_VERSION == "1.0"


def test_hol_audit_entry_source():
    assert HOL_AUDIT_ENTRY_SOURCE == "hedera-agent-kit-py"


def test_hol_audit_entry_type():
    assert HOL_AUDIT_ENTRY_TYPE == "hedera-agent-kit:audit-entry"
