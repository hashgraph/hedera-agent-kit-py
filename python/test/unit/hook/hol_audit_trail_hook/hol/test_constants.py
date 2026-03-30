from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.constants import (
    HCS1_CHUNK_ENVELOPE_SIZE,
    HCS1_CHUNK_SIZE,
    HCS1_CHUNK_THRESHOLD,
    HCS2_OPERATION,
    HCS2_PROTOCOL,
)


class TestHcs1Constants:
    def test_hcs1_chunk_threshold_is_1024(self):
        assert HCS1_CHUNK_THRESHOLD == 1024

    def test_hcs1_chunk_envelope_size_is_16(self):
        assert HCS1_CHUNK_ENVELOPE_SIZE == 16

    def test_hcs1_chunk_size_is_threshold_minus_envelope(self):
        assert HCS1_CHUNK_SIZE == HCS1_CHUNK_THRESHOLD - HCS1_CHUNK_ENVELOPE_SIZE
        assert HCS1_CHUNK_SIZE == 1008


class TestHcs2Constants:
    def test_hcs2_protocol_is_hcs_2(self):
        assert HCS2_PROTOCOL == "hcs-2"

    def test_hcs2_operation_values(self):
        assert HCS2_OPERATION == {
            "REGISTER": "register",
            "UPDATE": "update",
            "DELETE": "delete",
            "MIGRATE": "migrate",
        }
