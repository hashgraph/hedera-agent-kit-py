"""End-to-end tests for delete topic tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import json
import asyncio
from os import waitid
from typing import AsyncGenerator
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client, TopicId
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

DEFAULT_EXECUTOR_BALANCE = Hbar(20, in_tinybars=False)

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
    """Create a temporary executor account for tests."""
    executor_key_pair = PrivateKey.generate_ecdsa()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    account_id = resp.account_id
    client = get_custom_client(account_id, executor_key_pair)
    wrapper = HederaOperationsWrapper(client)

    yield account_id, executor_key_pair, client, wrapper

    await return_hbars_and_delete_account(
        wrapper, account_id, operator_client.operator_account_id
    )


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Setup LangChain agent and toolkit with a real Hedera executor account."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide the LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
async def toolkit(langchain_test_setup):
    """Provide the LangChain toolkit."""
    return langchain_test_setup.toolkit


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_call(
    agent_executor, input_text: str, config: RunnableConfig
) -> ExecutedTransactionToolResponse | ToolResponse:
    """Execute a tool call via the agent and return the parsed response dict."""
    raw = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )

    return extract_tool_response(raw, "delete_topic_tool")


async def create_test_topic(
    wrapper: HederaOperationsWrapper, client: Client
) -> TopicId:
    """Create a topic to be deleted later."""
    admin_key = client.operator_private_key.public_key()
    resp = await wrapper.create_topic(
        CreateTopicParametersNormalised(admin_key=admin_key)
    )
    return resp.topic_id


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_delete_pre_created_topic(
    agent_executor, executor_wrapper, executor_account, langchain_config
):
    """E2E: delete an existing topic via agent command."""
    _, _, client, _ = executor_account
    topic_id = await create_test_topic(executor_wrapper, client)
    topic_str = str(topic_id)

    # Delete the topic
    observation = await execute_agent_call(
        agent_executor, f"Delete the topic {topic_str}", langchain_config
    )

    assert isinstance(observation, ExecutedTransactionToolResponse)
    assert "deleted successfully" in observation.human_message.lower()
    assert topic_str in observation.human_message


@pytest.mark.asyncio
async def test_delete_non_existent_topic(agent_executor, langchain_config):
    """E2E: attempt to delete a non-existent topic."""
    fake_topic = "0.0.999999999"

    observation = await execute_agent_call(
        agent_executor, f"Delete the topic {fake_topic}", langchain_config
    )

    assert isinstance(observation, ToolResponse)
    assert observation.error is not None
    assert any(
        err in observation.error.upper()
        for err in ["INVALID_TOPIC_ID", "TOPIC_WAS_DELETED", "NOT_FOUND"]
    )
