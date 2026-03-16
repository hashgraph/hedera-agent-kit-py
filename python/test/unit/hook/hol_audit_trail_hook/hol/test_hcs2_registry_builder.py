import json

from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.constants import HCS2_REGISTRY_TYPE
from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.hcs2_registry_builder import Hcs2RegistryBuilder


class TestHcs2RegistryBuilderCreateRegistry:
    def test_creates_topic_with_hcs2_protocol_memo(self):
        result = Hcs2RegistryBuilder.create_registry()
        assert "hcs-2" in result.memo

    def test_defaults_registry_type_to_indexed(self):
        result = Hcs2RegistryBuilder.create_registry()
        assert result.memo == "hcs-2:0:0"

    def test_defaults_ttl_to_zero(self):
        result = Hcs2RegistryBuilder.create_registry()
        assert result.memo.endswith(":0")

    def test_non_indexed_registry_type(self):
        result = Hcs2RegistryBuilder.create_registry(
            registry_type=HCS2_REGISTRY_TYPE["NON_INDEXED"],
        )
        assert result.memo == "hcs-2:1:0"

    def test_custom_ttl(self):
        result = Hcs2RegistryBuilder.create_registry(ttl=3600)
        assert result.memo == "hcs-2:0:3600"


class TestHcs2RegistryBuilderRegisterEntry:
    def test_creates_register_message_with_protocol_operation_and_target(self):
        result = Hcs2RegistryBuilder.register_entry(
            registry_topic_id="0.0.100",
            target_topic_id="0.0.200",
        )
        message = json.loads(result.message)
        assert message["p"] == "hcs-2"
        assert message["op"] == "register"
        assert message["t_id"] == "0.0.200"

    def test_submits_to_correct_registry_topic(self):
        result = Hcs2RegistryBuilder.register_entry(
            registry_topic_id="0.0.100",
            target_topic_id="0.0.200",
        )
        assert str(result.topic_id) == "0.0.100"

    def test_includes_metadata_when_provided(self):
        result = Hcs2RegistryBuilder.register_entry(
            registry_topic_id="0.0.100",
            target_topic_id="0.0.200",
            metadata="some-metadata",
        )
        message = json.loads(result.message)
        assert message["metadata"] == "some-metadata"

    def test_includes_memo_when_provided(self):
        result = Hcs2RegistryBuilder.register_entry(
            registry_topic_id="0.0.100",
            target_topic_id="0.0.200",
            memo="test memo",
        )
        message = json.loads(result.message)
        assert message["m"] == "test memo"

    def test_omits_metadata_and_memo_when_not_provided(self):
        result = Hcs2RegistryBuilder.register_entry(
            registry_topic_id="0.0.100",
            target_topic_id="0.0.200",
        )
        message = json.loads(result.message)
        assert "metadata" not in message
        assert "m" not in message
