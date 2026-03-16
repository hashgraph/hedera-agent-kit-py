import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hedera_agent_kit.hooks.hol_audit_trail_hook.hol_audit_trail_hook import HolAuditTrailHook
from hedera_agent_kit.hooks.abstract_hook import (
    PostSecondaryActionParams,
    PreToolExecutionParams,
)
from hedera_agent_kit.shared.configuration import AgentMode, Context


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.operator_private_key.public_key.return_value = "mock-public-key"
    return client


@pytest.fixture
def mock_registry_builder():
    with patch(
        "hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer.Hcs2RegistryBuilder"
    ) as mock:
        registry_tx = MagicMock()
        registry_receipt = MagicMock()
        registry_receipt.topic_id = MagicMock()
        registry_receipt.topic_id.__str__ = lambda self: "0.0.999"
        registry_tx.execute.return_value = registry_receipt
        mock.create_registry.return_value = registry_tx

        register_tx = MagicMock()
        register_tx.execute.return_value = MagicMock()
        mock.register_entry.return_value = register_tx

        yield mock


@pytest.fixture
def mock_file_builder():
    with patch(
        "hedera_agent_kit.hooks.hol_audit_trail_hook.audit.writers.hol_audit_writer.Hcs1FileBuilder"
    ) as mock:
        topic_tx = MagicMock()
        topic_receipt = MagicMock()
        topic_receipt.topic_id = MagicMock()
        topic_receipt.topic_id.__str__ = lambda self: "0.0.1001"
        topic_tx.execute.return_value = topic_receipt

        message_tx = MagicMock()
        message_tx.execute.return_value = MagicMock()

        file_result = MagicMock()
        file_result.topic_transaction = topic_tx
        file_result.build_message_transactions.return_value = [message_tx]
        mock.create_file.return_value = file_result

        yield mock


def make_post_params(client, **overrides):
    tool_result = MagicMock()
    tool_result.raw = {
        "status": "SUCCESS",
        "transactionId": "0.0.1@123",
        "accountId": "0.0.456",
    }
    tool_result.human_message = "Transfer of 100 HBAR succeeded"

    defaults = dict(
        context=Context(mode=AgentMode.AUTONOMOUS),
        raw_params={},
        normalized_params={"amount": 100},
        core_action_result=None,
        tool_result=tool_result,
        client=client,
        method="test_tool",
    )
    defaults.update(overrides)
    return PostSecondaryActionParams(**defaults)


class TestHolAuditTrailHookProperties:
    def test_name_description_and_relevant_tools(self):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        assert hook.name == "HOL Audit Trail Hook"
        assert "HOL-standards-compliant" in hook.description
        assert hook.relevant_tools == ["test_tool"]


class TestGetSessionTopicId:
    def test_returns_none_when_no_session_and_no_config(self):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        assert hook.get_session_topic_id() is None

    def test_returns_configured_session_topic_id(self):
        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        assert hook.get_session_topic_id() == "0.0.666"

    @pytest.mark.timeout(10)
    @pytest.mark.asyncio
    async def test_returns_session_id_after_first_execution(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        assert hook.get_session_topic_id() == "0.0.999"


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestPreToolExecutionHook:
    async def test_returns_none_for_irrelevant_tools(self):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = PreToolExecutionParams(
            context=context, raw_params={}, client=MagicMock(), method="other_tool"
        )

        result = await hook.pre_tool_execution_hook(context, params, "other_tool")
        assert result is None

    async def test_does_not_throw_in_autonomous_mode(self):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = PreToolExecutionParams(
            context=context, raw_params={}, client=MagicMock(), method="test_tool"
        )

        # Should not raise
        await hook.pre_tool_execution_hook(context, params, "test_tool")

    async def test_throws_in_return_bytes_mode(self):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.RETURN_BYTES)
        params = PreToolExecutionParams(
            context=context, raw_params={}, client=MagicMock(), method="test_tool"
        )

        with pytest.raises(
            RuntimeError,
            match="Unsupported hook: HolAuditTrailHook is available only in Agent Mode AUTONOMOUS.*test_tool",
        ):
            await hook.pre_tool_execution_hook(context, params, "test_tool")


@pytest.mark.timeout(10)
@pytest.mark.asyncio
class TestPostSecondaryActionHook:
    async def test_returns_none_for_irrelevant_tools(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        result = await hook.post_secondary_action_hook(context, params, "other_tool")

        assert result is None
        mock_registry_builder.create_registry.assert_not_called()
        mock_file_builder.create_file.assert_not_called()

    async def test_lazily_creates_session_on_first_relevant_call(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        mock_registry_builder.create_registry.assert_called_once()
        assert hook.get_session_topic_id() == "0.0.999"

    async def test_reuses_session_on_subsequent_calls(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")
        await hook.post_secondary_action_hook(context, params, "test_tool")

        # Registry created only once
        mock_registry_builder.create_registry.assert_called_once()
        # File created twice
        assert mock_file_builder.create_file.call_count == 2

    async def test_skips_registry_creation_when_session_topic_id_provided(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        mock_registry_builder.create_registry.assert_not_called()
        assert hook.get_session_topic_id() == "0.0.666"

    async def test_builds_audit_entry_with_tool_params_and_result(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        mock_file_builder.create_file.assert_called_once()
        call_kwargs = mock_file_builder.create_file.call_args[1]
        entry_content = json.loads(call_kwargs["content"])
        assert entry_content["tool"] == "test_tool"
        assert entry_content["params"] == {"amount": 100}
        assert entry_content["result"]["raw"] == {
            "status": "SUCCESS",
            "transactionId": "0.0.1@123",
            "accountId": "0.0.456",
        }
        assert entry_content["result"]["message"] == "Transfer of 100 HBAR succeeded"

    async def test_creates_hcs1_file_with_audit_entry_content(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        call_kwargs = mock_file_builder.create_file.call_args[1]
        assert '"hedera-agent-kit:audit-entry"' in call_kwargs["content"]
        assert '"test_tool"' in call_kwargs["content"]

    async def test_registers_entry_in_session_registry(
        self, mock_client, mock_registry_builder, mock_file_builder
    ):
        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        await hook.post_secondary_action_hook(context, params, "test_tool")

        mock_registry_builder.register_entry.assert_called_once_with(
            registry_topic_id="0.0.666",
            target_topic_id="0.0.1001",
        )

    async def test_catches_and_logs_write_errors(
        self, mock_client, mock_registry_builder, mock_file_builder, capsys
    ):
        mock_registry_builder.register_entry.return_value.execute.side_effect = RuntimeError(
            "Network error"
        )

        hook = HolAuditTrailHook(
            relevant_tools=["test_tool"],
            session_topic_id="0.0.666",
        )
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        # Should not raise
        await hook.post_secondary_action_hook(context, params, "test_tool")

        captured = capsys.readouterr()
        assert "HolAuditTrailHook: Failed to log audit entry" in captured.out

    async def test_catches_and_logs_init_errors(
        self, mock_client, mock_registry_builder, mock_file_builder, capsys
    ):
        mock_registry_builder.create_registry.return_value.execute.side_effect = RuntimeError(
            "Init error"
        )

        hook = HolAuditTrailHook(relevant_tools=["test_tool"])
        context = Context(mode=AgentMode.AUTONOMOUS)
        params = make_post_params(mock_client)

        # Should not raise
        await hook.post_secondary_action_hook(context, params, "test_tool")

        captured = capsys.readouterr()
        assert "HolAuditTrailHook: Failed to log audit entry" in captured.out
