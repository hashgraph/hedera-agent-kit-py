import json

from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.hcs2_registry_builder import Hcs2RegistryBuilder


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
