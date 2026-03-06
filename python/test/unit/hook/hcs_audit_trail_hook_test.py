import pytest
from unittest.mock import MagicMock, patch

from hiero_sdk_python import TopicId, TransactionId

from hedera_agent_kit.shared.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.shared.configuration import AgentMode, Context
from hedera_agent_kit.shared.abstract_hook import (
    PreToolExecutionParams,
    PostSecondaryActionParams,
)
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def hcs_hook(mock_client):
    return HcsAuditTrailHook(
        relevant_tools=["test_tool"],
        hcs_topic_id="0.0.1234",
        logging_client=mock_client,
    )


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_pre_hook_autonomous_mode(hcs_hook):
    context = Context(mode=AgentMode.AUTONOMOUS)
    params = PreToolExecutionParams(
        context=context, raw_params={}, client=MagicMock(), method="test_tool"
    )
    # Should not raise any error
    await hcs_hook.pre_tool_execution_hook(context, params, "test_tool")


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_pre_hook_return_bytes_mode(hcs_hook):
    context = Context(mode=AgentMode.RETURN_BYTES)
    params = PreToolExecutionParams(
        context=context, raw_params={}, client=MagicMock(), method="test_tool"
    )
    with pytest.raises(
        RuntimeError,
        match="Unsupported hook: HcsAuditTrailHook is available only in Agent Mode AUTONOMOUS",
    ):
        await hcs_hook.pre_tool_execution_hook(context, params, "test_tool")


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_post_hook_submits_message(hcs_hook, mock_client):
    context = Context(mode=AgentMode.AUTONOMOUS)

    raw_response = RawTransactionResponse(
        status="SUCCESS",
        transaction_id=TransactionId.from_string("0.0.1234@1234567890.1234567890"),
        topic_id=TopicId.from_string("0.0.5678"),
    )
    tool_result = ExecutedTransactionToolResponse(
        human_message="All good", raw=raw_response
    )

    params = PostSecondaryActionParams(
        context=context,
        raw_params={},
        normalized_params={"foo": "bar"},
        core_action_result=None,
        tool_result=tool_result,
        client=MagicMock(),
        method="test_tool",
    )

    with patch(
        "hedera_agent_kit.shared.hooks.hcs_audit_trail_hook.TopicMessageSubmitTransaction"
    ) as mock_tx_class:
        from hiero_sdk_python.hapi.services.response_code_pb2 import ResponseCodeEnum

        mock_tx_instance = mock_tx_class.return_value
        mock_tx_instance.execute.return_value.status = ResponseCodeEnum.SUCCESS

        await hcs_hook.post_secondary_action_hook(context, params, "test_tool")

        mock_tx_class.assert_called_once()
        # Verify method calls on the transaction instance
        mock_tx_instance.set_topic_id.assert_called_once()
        mock_tx_instance.set_message.assert_called_once()

        # Verify message content contains expected info
        message_arg = mock_tx_instance.set_message.call_args[0][0]
        assert "Agent executed tool test_tool" in message_arg
        assert "0.0.1234@1234567890.1234567890" in message_arg
        assert "0.0.5678" in message_arg
        assert "bar" in message_arg


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_post_hook_ignores_irrelevant_tools(hcs_hook, mock_client):
    context = Context(mode=AgentMode.AUTONOMOUS)
    params = PostSecondaryActionParams(
        context=context,
        raw_params={},
        normalized_params={},
        core_action_result=None,
        tool_result=MagicMock(),
        client=MagicMock(),
        method="other_tool",
    )

    with patch(
        "hedera_agent_kit.shared.hooks.hcs_audit_trail_hook.TopicMessageSubmitTransaction"
    ) as mock_tx_class:
        await hcs_hook.post_secondary_action_hook(context, params, "other_tool")
        mock_tx_class.assert_not_called()
