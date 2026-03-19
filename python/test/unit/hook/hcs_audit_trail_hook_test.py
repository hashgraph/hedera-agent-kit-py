import pytest
from unittest.mock import MagicMock, patch


from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.hooks.utils import stringify_recursive
from hedera_agent_kit.hooks.abstract_hook import (
    PreToolExecutionParams,
    PostSecondaryActionParams,
)
from hedera_agent_kit.shared.configuration import AgentMode, Context
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    SubmitTopicMessageParametersNormalised,
    UpdateTopicParametersNormalised,
    TransferHbarParametersNormalised,
    ContractExecuteTransactionParametersNormalised,
    EvmContractCallParametersNormalised,
)
from hiero_sdk_python import AccountId, TokenId, TopicId, PublicKey, Hbar, TransactionId
from hiero_sdk_python.contract.contract_id import ContractId
from datetime import datetime


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
        normalized_params={"foo": "bar", "data": b"\x01\x02\x03"},
        core_action_result=None,
        tool_result=tool_result,
        client=MagicMock(),
        method="test_tool",
    )

    with patch(
        "hedera_agent_kit.hooks.hcs_audit_trail_hook.TopicMessageSubmitTransaction"
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
        assert '"foo": "bar"' in message_arg
        assert '"data": "0x010203"' in message_arg


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
        "hedera_agent_kit.hooks.hcs_audit_trail_hook.TopicMessageSubmitTransaction"
    ) as mock_tx_class:
        await hcs_hook.post_secondary_action_hook(context, params, "other_tool")
        mock_tx_class.assert_not_called()


def test_stringify_recursive_bytes():
    data = {"secret": b"hello", "nested": {"key": bytearray(b"world")}}
    result = stringify_recursive(data)
    assert result == {"secret": "0x68656c6c6f", "nested": {"key": "0x776f726c64"}}


def test_stringify_recursive_sdk_objects():
    data = {
        "account": AccountId.from_string("0.0.1"),
        "token": TokenId.from_string("0.0.2"),
        "topic": TopicId.from_string("0.0.3"),
    }
    result = stringify_recursive(data)
    assert result == {"account": "0.0.1", "token": "0.0.2", "topic": "0.0.3"}


def test_stringify_recursive_real_schemas():
    # Test CreateAccountParametersNormalised
    create_account = CreateAccountParametersNormalised(
        initial_balance=Hbar(10),
        key=PublicKey.from_string(
            "302a300506032b6570032100e0c8ec20b6d9700f48e1d22bb7fd5ad863f828e556a4d1d74542187e101fa245"
        ),
        max_automatic_token_associations=5,
    )
    result = stringify_recursive(create_account)
    # PublicKey stringification might vary depending on whether it's Ed25519 or ECDSA, but it should be a string.
    assert result["initial_balance"] == "10.00000000 ℏ"
    assert isinstance(result["key"], str)
    assert result["max_automatic_token_associations"] == 5

    # Test SubmitTopicMessageParametersNormalised
    submit_msg = SubmitTopicMessageParametersNormalised(
        topic_id=TopicId.from_string("0.0.123"),
        message="hello world",
    )
    result = stringify_recursive(submit_msg)
    assert result == {
        "topic_id": "0.0.123",
        "message": "hello world",
        "transaction_memo": None,
        "scheduling_params": None,
    }

    # Test UpdateTopicParametersNormalised
    now = datetime(2023, 1, 1, 12, 0, 0)
    update_topic = UpdateTopicParametersNormalised(
        topic_id=TopicId.from_string("0.0.123"),
        expiration_time=now,
    )
    result = stringify_recursive(update_topic)
    assert result["topic_id"] == "0.0.123"
    assert "2023-01-01" in result["expiration_time"]

    # Test TransferHbarParametersNormalised (dict with AccountId keys)
    transfer_hbar = TransferHbarParametersNormalised(
        hbar_transfers={
            AccountId.from_string("0.0.1"): 1000,
            AccountId.from_string("0.0.2"): -1000,
        }
    )
    result = stringify_recursive(transfer_hbar)
    assert result["hbar_transfers"] == {"0.0.1": 1000, "0.0.2": -1000}

    # Test EVM schemas
    evm_execute = ContractExecuteTransactionParametersNormalised(
        contract_id=ContractId.from_string("0.0.456"),
        function_parameters=b"\xde\xad\xbe\xef",
        gas=100000,
    )
    result = stringify_recursive(evm_execute)
    assert result == {
        "contract_id": "0.0.456",
        "function_parameters": "0xdeadbeef",
        "gas": 100000,
        "scheduling_params": None,
    }

    evm_call = EvmContractCallParametersNormalised(
        contract_id="0.0.789",
        function_parameters=b"\xca\xfe\xba\xbe",
        gas=50000,
    )
    result = stringify_recursive(evm_call)
    assert result == {
        "contract_id": "0.0.789",
        "function_parameters": "0xcafebabe",
        "gas": 50000,
        "scheduling_params": None,
    }


def test_stringify_recursive_mixed():
    data = [
        {"id": AccountId.from_string("0.0.10"), "data": b"\xff"},
        "simple string",
        123,
        None,
    ]
    result = stringify_recursive(data)
    assert result == [
        {"id": "0.0.10", "data": "0xff"},
        "simple string",
        123,
        None,
    ]
