"""End-to-end tests for create topic tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""
import json
from typing import AsyncGenerator, cast
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import CreateAccountParametersNormalised
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(10, in_tinybars=False)


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
    executor_key_pair: PrivateKey = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper_instance: HederaOperationsWrapper = HederaOperationsWrapper(
        executor_client
    )

    yield executor_account_id, executor_key_pair, executor_client, executor_wrapper_instance

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def executor_wrapper(executor_account):
    """Provide just the executor wrapper from the executor_account fixture."""
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "create_topic_e2e"})


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
async def toolkit(langchain_test_setup):
    """Provide the LangChain toolkit."""
    return langchain_test_setup.toolkit


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_create_topic(agent_executor, input_text: str, config: RunnableConfig) -> ExecutedTransactionToolResponse:
    """Execute topic creation via the agent and return the parsed response dict."""
    response = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Find the ToolMessage in the response
    messages = response.get("messages", [])
    tool_message = next(
        (m for m in messages if m.__class__.__name__ == "ToolMessage" or getattr(m, "name", None) == "create_topic_tool"),
        None,
    )

    if not tool_message:
        raise ValueError("No ToolMessage found in agent response")

    # The ToolMessage content is a JSON string — parse it
    result = json.loads(tool_message.content)

    return ExecutedTransactionToolResponse.from_dict(result)


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_topic_with_default_settings(
    agent_executor, executor_wrapper: HederaOperationsWrapper, langchain_config: RunnableConfig
):
    """Test creating a topic with default settings."""
    input_text = "Create a new Hedera topic"
    response: ExecutedTransactionToolResponse = await execute_create_topic(agent_executor, input_text, langchain_config)


    topic_info = executor_wrapper.get_topic_info(str(response.raw.topic_id))
    assert topic_info is not None
    assert topic_info.submit_key is None
    assert topic_info.memo == ""


@pytest.mark.asyncio
async def test_create_topic_with_memo_and_submit_key(
    agent_executor, executor_wrapper: HederaOperationsWrapper, executor_account, langchain_config: RunnableConfig
):
    """Test creating a topic with memo and submit key."""
    _, _, executor_client, _ = executor_account
    input_text = 'Create a topic with memo "E2E test topic" and set submit key'
    response: ExecutedTransactionToolResponse = await execute_create_topic(agent_executor, input_text, langchain_config)

    topic_info = executor_wrapper.get_topic_info(str(response.raw.topic_id))
    assert (
        topic_info.submit_key.ECDSA_secp256k1
        == executor_client.operator_private_key.public_key().to_bytes_raw()
    )


@pytest.mark.asyncio
async def test_create_topic_with_memo_and_no_submit_key(
    agent_executor, executor_wrapper: HederaOperationsWrapper, langchain_config: RunnableConfig
):
    """Test creating a topic with memo and without submit key restriction."""
    input_text = 'Create a topic with memo "E2E test topic" and do not restrict submit access'
    response: ExecutedTransactionToolResponse = await execute_create_topic(agent_executor, input_text, langchain_config)

    topic_info = executor_wrapper.get_topic_info(str(response.raw.topic_id))
    assert topic_info.submit_key is None
