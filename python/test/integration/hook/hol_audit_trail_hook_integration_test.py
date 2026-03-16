import asyncio
import base64
import json
import os
import re

import brotli
import pytest
from hiero_sdk_python import Hbar, PrivateKey

from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_entry import (
    AuditEntry,
    build_audit_entry,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.audit_session import (
    AuditSession,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.constants import (
    HOL_AUDIT_ENTRY_SOURCE,
    HOL_AUDIT_ENTRY_TYPE,
    HOL_AUDIT_ENTRY_VERSION,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer import (
    HolAuditWriter,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.hol.constants import (
    HCS1_CHUNK_SIZE,
    HCS2_OPERATION,
    HCS2_PROTOCOL,
)
from hedera_agent_kit.hooks.hol_audit_trail_hook.hol_audit_trail_hook import (
    HolAuditTrailHook,
)
from hedera_agent_kit.plugins.core_account_plugin import TRANSFER_HBAR_TOOL
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    DeleteAccountParametersNormalised,
)
from test.utils.hedera_operations_wrapper import HederaOperationsWrapper
from test.utils.setup.client_setup import (
    get_custom_client,
    get_operator_client_for_tests,
)
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from test.utils.usd_to_hbar_service import UsdToHbarService

POLL_INTERVAL_MS = 500
POLL_TIMEOUT_MS = 30_000


async def poll_topic_messages(
    wrapper: HederaOperationsWrapper,
    topic_id: str,
    expected_count: int,
):
    """Poll mirror node until at least expected_count messages appear for the topic."""
    elapsed = 0
    while elapsed < POLL_TIMEOUT_MS:
        response = await wrapper.get_topic_messages(topic_id)
        if len(response.get("messages", [])) >= expected_count:
            return response
        await asyncio.sleep(POLL_INTERVAL_MS / 1000)
        elapsed += POLL_INTERVAL_MS
    # Final attempt — let the assertion in the test produce the failure
    return await wrapper.get_topic_messages(topic_id)


def reconstruct_hcs1_content(messages: list[dict]) -> dict:
    """Reassemble chunked HCS-1 messages into the original JSON audit entry."""
    chunks = [json.loads(m["message"]) for m in messages]
    chunks.sort(key=lambda c: c["o"])

    data_uri = "".join(c["c"] for c in chunks)
    base64_payload = re.sub(r"^data:[^;]+;base64,", "", data_uri)
    compressed = base64.b64decode(base64_payload)
    decompressed = brotli.decompress(compressed)
    return json.loads(decompressed.decode("utf-8"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def setup_environment():
    """Create operator + executor accounts for the HOL audit trail integration tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])
            ),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_client.operator_private_key.public_key(),
        )
    )
    recipient_account_id = recipient_resp.account_id

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "recipient_account_id": recipient_account_id,
    }

    # Cleanup
    try:
        await executor_wrapper.delete_account(
            DeleteAccountParametersNormalised(
                account_id=recipient_account_id,
                transfer_account_id=operator_client.operator_account_id,
            )
        )
        await executor_wrapper.delete_account(
            DeleteAccountParametersNormalised(
                account_id=executor_account_id,
                transfer_account_id=operator_client.operator_account_id,
            )
        )
    except Exception as e:
        print(f"Failed to clean up accounts: {e}")
    finally:
        executor_client.close()
        operator_client.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_single_write_creates_hcs2_session_and_hcs1_entry(setup_environment):
    """Create HCS-2 session registry and HCS-1 audit entry for a single write."""
    env = setup_environment
    executor_client = env["executor_client"]
    executor_wrapper: HederaOperationsWrapper = env["executor_wrapper"]
    recipient_account_id = env["recipient_account_id"]

    writer = HolAuditWriter(executor_client)
    session = AuditSession(writer)

    entry = build_audit_entry(
        tool=TRANSFER_HBAR_TOOL,
        params={
            "transfers": [
                {"accountId": str(recipient_account_id), "amount": 0.0001}
            ]
        },
        result={"raw": {"status": "SUCCESS"}, "message": "HBAR successfully transferred."},
    )

    await session.write_entry(entry)

    session_topic_id = session.get_session_id()
    assert session_topic_id, "Session topic ID should be truthy"

    # Verify session topic memo is HCS-2 registry format
    topic_info = executor_wrapper.get_topic_info(session_topic_id)
    assert topic_info.memo == "hcs-2:0:0"

    # Poll mirror node until the register message appears
    session_messages = await poll_topic_messages(executor_wrapper, session_topic_id, 1)
    messages = session_messages.get("messages", [])
    assert len(messages) == 1

    # Parse the HCS-2 register message
    register_msg = json.loads(messages[0]["message"])
    assert register_msg["p"] == HCS2_PROTOCOL
    assert register_msg["op"] == HCS2_OPERATION["REGISTER"]
    assert register_msg.get("t_id"), "Register message should have t_id"

    # Verify entry topic memo matches HCS-1 format: <sha256-hash>:brotli:base64
    entry_topic_id = register_msg["t_id"]
    entry_topic_info = executor_wrapper.get_topic_info(entry_topic_id)
    assert re.match(
        r"^[a-f0-9]{64}:brotli:base64$", entry_topic_info.memo
    ), f"Entry topic memo does not match HCS-1 format: {entry_topic_info.memo}"

    # Poll entry topic for HCS-1 chunk messages and reconstruct
    entry_messages = await poll_topic_messages(executor_wrapper, entry_topic_id, 1)
    entry_msgs = entry_messages.get("messages", [])
    assert len(entry_msgs) > 0

    audit_entry = reconstruct_hcs1_content(entry_msgs)
    parsed = AuditEntry(**audit_entry)

    assert parsed.tool == TRANSFER_HBAR_TOOL
    assert parsed.type == HOL_AUDIT_ENTRY_TYPE
    assert parsed.version == HOL_AUDIT_ENTRY_VERSION
    assert parsed.source == HOL_AUDIT_ENTRY_SOURCE


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_multiple_entries_under_same_session(setup_environment):
    """Multiple entries should be registered under the same HCS-2 session."""
    env = setup_environment
    executor_client = env["executor_client"]
    executor_wrapper: HederaOperationsWrapper = env["executor_wrapper"]
    recipient_account_id = env["recipient_account_id"]

    writer = HolAuditWriter(executor_client)
    session = AuditSession(writer)

    entry1 = build_audit_entry(
        tool=TRANSFER_HBAR_TOOL,
        params={
            "transfers": [
                {"accountId": str(recipient_account_id), "amount": 0.0001}
            ]
        },
        result={"raw": {"status": "SUCCESS"}, "message": "first transfer"},
    )

    entry2 = build_audit_entry(
        tool=TRANSFER_HBAR_TOOL,
        params={
            "transfers": [
                {"accountId": str(recipient_account_id), "amount": 0.0002}
            ]
        },
        result={"raw": {"status": "SUCCESS"}, "message": "second transfer"},
    )

    await session.write_entry(entry1)
    await session.write_entry(entry2)

    session_topic_id = session.get_session_id()
    assert session_topic_id, "Session topic ID should be truthy"

    # Poll until both register messages appear
    session_messages = await poll_topic_messages(executor_wrapper, session_topic_id, 2)
    messages = session_messages.get("messages", [])
    assert len(messages) == 2

    # Each register message should point to a different entry topic
    register_msg1 = json.loads(messages[0]["message"])
    register_msg2 = json.loads(messages[1]["message"])
    assert register_msg1["t_id"] != register_msg2["t_id"]


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_large_entry_splits_into_multiple_hcs1_chunks(setup_environment):
    """A large audit entry should be split into multiple HCS-1 chunks."""
    env = setup_environment
    executor_client = env["executor_client"]
    executor_wrapper: HederaOperationsWrapper = env["executor_wrapper"]

    writer = HolAuditWriter(executor_client)
    session = AuditSession(writer)

    # Build an entry with high-entropy padding so brotli cannot compress it
    # below the HCS-1 chunk threshold (~1008 chars per chunk in the data URI).
    # 1500 random bytes -> ~3000 hex chars -> ~2200 compressed bytes -> 3-4 chunks.
    padding = os.urandom(1500).hex()
    large_entry = build_audit_entry(
        tool=TRANSFER_HBAR_TOOL,
        params={"padding": padding},
        result={"raw": {"status": "SUCCESS"}, "message": "large entry test"},
    )

    await session.write_entry(large_entry)

    session_topic_id = session.get_session_id()
    assert session_topic_id, "Session topic ID should be truthy"

    # Poll for the register message in the session topic
    session_messages = await poll_topic_messages(executor_wrapper, session_topic_id, 1)
    messages = session_messages.get("messages", [])
    assert len(messages) == 1

    register_msg = json.loads(messages[0]["message"])
    entry_topic_id = register_msg["t_id"]

    # Poll for chunk messages — expect more than 1
    entry_messages = await poll_topic_messages(executor_wrapper, entry_topic_id, 2)
    entry_msgs = entry_messages.get("messages", [])
    assert len(entry_msgs) > 1

    # Verify each chunk message has the correct HCS-1 envelope format
    chunks = [json.loads(m["message"]) for m in entry_msgs]

    for chunk in chunks:
        assert "o" in chunk, "Chunk should have 'o' (order index)"
        assert "c" in chunk, "Chunk should have 'c' (content)"
        assert isinstance(chunk["o"], int)
        assert isinstance(chunk["c"], str)
        assert len(chunk["c"]) <= HCS1_CHUNK_SIZE

    # Verify order indices form a contiguous 0..N-1 sequence
    sorted_orders = sorted(c["o"] for c in chunks)
    assert sorted_orders == list(range(len(chunks)))

    # Reconstruct and validate the full audit entry
    reconstructed = reconstruct_hcs1_content(entry_msgs)
    parsed = AuditEntry(**reconstructed)

    assert parsed.tool == TRANSFER_HBAR_TOOL
    assert parsed.params["padding"] == padding
    assert parsed.type == HOL_AUDIT_ENTRY_TYPE
    assert parsed.version == HOL_AUDIT_ENTRY_VERSION
    assert parsed.source == HOL_AUDIT_ENTRY_SOURCE


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_rejects_return_bytes_mode(setup_environment):
    """Hook should reject tool execution when used in RETURN_BYTES mode."""
    env = setup_environment
    executor_client = env["executor_client"]

    hook = HolAuditTrailHook(relevant_tools=[TRANSFER_HBAR_TOOL])

    from hedera_agent_kit.hooks.abstract_hook import PreToolExecutionParams

    context = Context(mode=AgentMode.RETURN_BYTES, hooks=[hook])
    params = PreToolExecutionParams(
        context=context,
        raw_params={},
        client=executor_client,
        method=TRANSFER_HBAR_TOOL,
    )

    with pytest.raises(RuntimeError, match="Unsupported hook.*AUTONOMOUS"):
        await hook.pre_tool_execution_hook(context, params, TRANSFER_HBAR_TOOL)


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_does_not_trigger_for_irrelevant_tool(setup_environment):
    """Hook should not trigger when the executed tool is not in relevantTools."""
    env = setup_environment
    executor_client = env["executor_client"]

    hook = HolAuditTrailHook(relevant_tools=["some_other_tool"])

    from hedera_agent_kit.hooks.abstract_hook import PreToolExecutionParams

    context = Context(mode=AgentMode.AUTONOMOUS, hooks=[hook])
    params = PreToolExecutionParams(
        context=context,
        raw_params={},
        client=executor_client,
        method=TRANSFER_HBAR_TOOL,
    )

    # Should return None (no-op) without raising
    result = await hook.pre_tool_execution_hook(context, params, TRANSFER_HBAR_TOOL)
    assert result is None
    assert hook.get_session_topic_id() is None
