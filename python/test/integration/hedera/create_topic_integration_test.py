"""Hedera integration tests for create topic tool.

This module tests the topic creation tool by calling it directly with parameters,
omitting the LLM and focusing on testing logic and on-chain execution.
"""

from typing import cast

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar

from hedera_agent_kit.plugins.core_consensus_plugin import CreateTopicTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateTopicParameters,
    DeleteAccountParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client


@pytest.fixture(scope="module")
async def setup_environment():
    """Setup Hedera operator client and context for tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5, in_tinybars=False),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "context": context,
    }

    operator_client.close()
    await executor_wrapper.delete_account(
        DeleteAccountParametersNormalised(
            account_id=executor_account_id,
            transfer_account_id=operator_client.operator_account_id,
        )
    )


@pytest.mark.asyncio
async def test_create_topic_with_default_params(setup_environment):
    """Test creating a topic with default parameters."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateTopicParameters()
    tool = CreateTopicTool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Topic created successfully" in result.human_message
    assert exec_result.raw.topic_id is not None
    assert exec_result.raw.transaction_id is not None

    topic_info = wrapper.get_topic_info(str(exec_result.raw.topic_id))
    assert topic_info is not None
    assert topic_info.memo is ""
    # Admin key should be set by default (defaults to True)
    assert topic_info.admin_key is not None
    assert topic_info.submit_key is None


@pytest.mark.asyncio
async def test_create_topic_with_memo_and_submit_key(setup_environment):
    """Test creating a topic with a memo and submit key enabled."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateTopicParameters(
        topic_memo="Integration test topic", submit_key=True
    )
    tool = CreateTopicTool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Topic created successfully" in result.human_message
    topic_info = wrapper.get_topic_info(str(exec_result.raw.topic_id))

    assert topic_info is not None
    assert topic_info.memo == "Integration test topic"
    # Admin key should be set by default
    assert topic_info.admin_key is not None
    assert (
        topic_info.submit_key.ECDSA_secp256k1
        == client.operator_private_key.public_key().to_bytes_raw()
    )


@pytest.mark.asyncio
async def test_create_topic_with_empty_memo(setup_environment):
    """Test creating a topic with an empty string memo."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateTopicParameters(topic_memo="", submit_key=False, admin_key=False)
    tool = CreateTopicTool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Topic created successfully" in result.human_message
    topic_info = wrapper.get_topic_info(str(exec_result.raw.topic_id))

    assert topic_info.memo == ""
    assert topic_info.submit_key is None
    assert topic_info.admin_key is None


@pytest.mark.asyncio
async def test_create_topic_with_custom_public_key(setup_environment):
    """Test creating a topic with a custom public key string."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    # Generate a custom key pair
    custom_key = PrivateKey.generate_ecdsa()
    custom_public_key_str = custom_key.public_key().to_string_der()

    params = CreateTopicParameters(
        topic_memo="Custom key topic",
        submit_key=custom_public_key_str,
        admin_key=False,
    )
    tool = CreateTopicTool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Topic created successfully" in result.human_message
    topic_info = wrapper.get_topic_info(str(exec_result.raw.topic_id))

    assert topic_info.memo == "Custom key topic"
    assert topic_info.admin_key is None
    assert topic_info.submit_key is not None
    assert (
        topic_info.submit_key.ECDSA_secp256k1
        == custom_key.public_key().to_bytes_raw()
    )
