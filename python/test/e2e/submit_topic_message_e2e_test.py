"""End-to-end tests for submit topic message tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import asyncio
from typing import AsyncGenerator
import pytest
from hiero_sdk_python import Hbar, PrivateKey, TopicId
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(
    10, in_tinybars=False
)  # Needs to cover account + topic ops
MIRROR_NODE_WAITING_TIME_SEC = 10  # Wait for mirror node to ingest data


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """Initialize operator client once per test session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Create a wrapper for operator client operations."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary executor account for tests.
    Yields:
        tuple: (account_id, private_key, client, wrapper)
    Teardown:
        Returns funds and deletes the account.
    """
    executor_key: PrivateKey = PrivateKey.generate_ecdsa()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=executor_key.public_key()
        )
    )
    executor_account_id = resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Wait for account creation to propagate
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Set up LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "submit_topic_message_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> TopicId:
    """Helper function to create a topic for message submission tests.

    Creates a topic with no submit key, so the executor (as creator) can
    submit messages freely.
    """
    resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=None)
    )
    assert resp.topic_id is not None

    return resp.topic_id


@pytest.fixture
async def pre_created_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> AsyncGenerator[TopicId, None]:
    """Provides a pre-created topic ID for tests."""
    topic_id = await create_test_topic(executor_wrapper)
    yield topic_id


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_submit_message_to_pre_created_topic(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    pre_created_topic: TopicId,
    langchain_config: RunnableConfig,
):
    """Test submitting a message to a topic via natural language."""
    target_topic_id = str(pre_created_topic)
    message = "Hello Hedera from the E2E test"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Submit message '{message}' to topic {target_topic_id}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "submit_topic_message_tool")
    assert isinstance(observation, ExecutedTransactionToolResponse)
    assert "submitted successfully" in observation.human_message.lower()

    # Wait for mirror node ingestion
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    # Verify message was received
    topic_messages = await executor_wrapper.get_topic_messages(target_topic_id)
    assert len(topic_messages["messages"]) >= 1


@pytest.mark.asyncio
async def test_fail_submit_to_non_existent_topic(
    agent_executor, langchain_config: RunnableConfig
):
    """Test attempting to submit a message to a topic that does not exist."""
    fake_topic_id = "0.0.999999999"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Submit message 'test' to topic {fake_topic_id}",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "submit_topic_message_tool")

    # Expect a ToolResponse with an error, not an ExecutedTransactionToolResponse
    assert isinstance(observation, ToolResponse)
    assert observation.error is not None
    # Check for expected Hedera error codes
    assert any(
        err in observation.error.upper()
        for err in [
            "INVALID_TOPIC_ID",
            "NOT_FOUND",
        ]
    )


@pytest.mark.asyncio
async def test_submit_message_scheduled(
    agent_executor,
    pre_created_topic: TopicId,
    langchain_config: RunnableConfig,
):
    """Test scheduling a topic message submission via natural language."""
    target_topic_id = str(pre_created_topic)
    message = "This is a scheduled message"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Submit message '{message}' to topic {target_topic_id}. Schedule this transaction.",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "submit_topic_message_tool")
    assert isinstance(observation, ExecutedTransactionToolResponse)
    assert "scheduled transaction created successfully" in observation.human_message.lower()
    assert observation.raw.schedule_id is not None
    assert observation.raw.transaction_id is not None
