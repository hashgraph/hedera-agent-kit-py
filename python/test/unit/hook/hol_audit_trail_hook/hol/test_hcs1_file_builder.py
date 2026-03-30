import base64
import json
import os
import re

import pytest

from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.constants import (
    HCS1_CHUNK_ENVELOPE_SIZE,
    HCS1_CHUNK_SIZE,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.hcs1_file_builder import Hcs1FileBuilder


class TestHcs1FileBuilderCreateFile:
    def test_returns_topic_transaction_and_build_message_transactions(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')

        assert result.topic_transaction is not None
        assert callable(result.build_message_transactions)

    def test_topic_memo_has_hash_brotli_base64_format(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')

        memo = result.topic_transaction.memo
        assert re.match(r"^[a-f0-9]{64}:brotli:base64$", memo)

    def test_default_mime_type_is_application_json(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')
        messages = result.build_message_transactions("0.0.100")

        first_msg = json.loads(messages[0].message)
        assert first_msg["c"].startswith("data:application/json;base64,")

    def test_custom_mime_type(self):
        result = Hcs1FileBuilder.create_file(
            content='{"key":"value"}',
            mime_type="text/plain",
        )
        messages = result.build_message_transactions("0.0.100")

        first_msg = json.loads(messages[0].message)
        assert first_msg["c"].startswith("data:text/plain;base64,")

    def test_data_uri_contains_valid_base64_brotli_content(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')
        messages = result.build_message_transactions("0.0.100")

        data_uri = "".join(json.loads(msg.message)["c"] for msg in messages)
        assert re.match(r"^data:application/json;base64,.+", data_uri)

        base64_part = data_uri.split(",")[1]
        # Should be valid base64
        base64.b64decode(base64_part)

    def test_single_chunk_for_small_content(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')
        messages = result.build_message_transactions("0.0.100")

        assert len(messages) == 1

    def test_multiple_chunks_for_large_content(self):
        large_content = base64.b64encode(os.urandom(5000)).decode("ascii")
        result = Hcs1FileBuilder.create_file(content=large_content)
        messages = result.build_message_transactions("0.0.100")

        assert len(messages) > 1

    def test_sequential_ordinals_starting_at_zero(self):
        large_content = base64.b64encode(os.urandom(5000)).decode("ascii")
        result = Hcs1FileBuilder.create_file(content=large_content)
        messages = result.build_message_transactions("0.0.100")

        for index, msg in enumerate(messages):
            parsed = json.loads(msg.message)
            assert parsed["o"] == index

    def test_chunk_content_does_not_exceed_hcs1_chunk_size(self):
        large_content = base64.b64encode(os.urandom(5000)).decode("ascii")
        result = Hcs1FileBuilder.create_file(content=large_content)
        messages = result.build_message_transactions("0.0.100")

        for msg in messages:
            parsed = json.loads(msg.message)
            assert len(parsed["c"]) <= HCS1_CHUNK_SIZE

    def test_chunk_envelope_does_not_exceed_budget(self):
        large_content = base64.b64encode(os.urandom(5000)).decode("ascii")
        result = Hcs1FileBuilder.create_file(content=large_content)
        messages = result.build_message_transactions("0.0.100")

        assert len(messages) > 1
        for msg in messages:
            parsed = json.loads(msg.message)
            envelope_size = len(msg.message.encode("utf-8")) - len(parsed["c"].encode("utf-8"))
            assert envelope_size <= HCS1_CHUNK_ENVELOPE_SIZE

    def test_message_transactions_target_provided_topic_id(self):
        result = Hcs1FileBuilder.create_file(content='{"key":"value"}')
        messages = result.build_message_transactions("0.0.100")

        for msg in messages:
            assert str(msg.topic_id) == "0.0.100"
