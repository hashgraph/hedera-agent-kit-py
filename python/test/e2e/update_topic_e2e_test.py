"""End-to-end tests for update topic tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
    TopicId,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
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

# Constants
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
    """Create a temporary executor account for tests.

    Yields:
        tuple: (account_id, private_key, client, wrapper)
    """
    executor_key_pair: PrivateKey = PrivateKey.generate_ed25519()
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

    await wait(MIRROR_NODE_WAITING_TIME)

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
    return RunnableConfig(configurable={"thread_id": "update_topic_e2e"})


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
async def response_parser(langchain_test_setup):
    """Provide the LangChain response parser."""
    return langchain_test_setup.response_parser


@pytest.fixture
async def test_topic(
    executor_wrapper, executor_account
) -> AsyncGenerator[TopicId, None]:
    """Creates a topic with admin and submit keys set to the executor's key.

    This corresponds to the `beforeEach` setup in the TS tests.
    """
    _, _, executor_client, _ = executor_account
    key = executor_client.operator_private_key.public_key()

    resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(
            admin_key=key,
            submit_key=key,
            memo="initial-topic-memo",
        )
    )

    assert resp.topic_id is not None
    print(f"Created topic {resp.topic_id}")
    await wait(MIRROR_NODE_WAITING_TIME)

    yield resp.topic_id


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute a request via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    """Helper to extract tool data from response."""
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    if not tool_calls:
        raise ValueError("No tool calls found in agent result.")
    return tool_calls[0]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_update_topic_keys_explicit(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_topic: TopicId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test changing topic keys using explicitly provided values."""
    _, _, executor_client, _ = executor_account
    topic_id_str = str(test_topic)

    # Generate a new key
    new_submit_key = PrivateKey.generate_ed25519().public_key()
    new_submit_key_str = new_submit_key.to_string()

    input_text = (
        f"For topic {topic_id_str}, change the submit key to: {new_submit_key_str}."
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    topic_info = executor_wrapper.get_topic_info(topic_id_str)

    # Admin key should remain unchanged (executor's key)
    assert str(topic_info.admin_key.ed25519.hex()) == str(
        executor_client.operator_private_key.public_key().to_string()
    )

    # Submit key should be the new key
    assert topic_info.submit_key.ed25519.hex() == new_submit_key.to_string()


@pytest.mark.asyncio
async def test_update_topic_keys_default(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_topic: TopicId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test changing topic keys using 'my key' (default values) and updating memo."""
    _, _, executor_client, _ = executor_account
    topic_id_str = str(test_topic)

    input_text = f"For topic {topic_id_str}, change the submit key to my key and set the topic memo to 'just updated'"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    topic_info = executor_wrapper.get_topic_info(topic_id_str)

    # Submit key should be the executor's key
    assert str(topic_info.submit_key.ed25519.hex()) == str(
        executor_client.operator_private_key.public_key().to_string()
    )
    assert topic_info.memo == "just updated"


@pytest.mark.asyncio
async def test_fail_update_no_submit_key(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test failure when updating a topic that was created without a submit key."""
    _, _, executor_client, _ = executor_account
    key = executor_client.operator_private_key.public_key()

    # Create a topic without a submit key
    resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(
            admin_key=key,
            submit_key=None,  # Explicitly None
            memo="no-submit",
        )
    )
    topic_without_submit_id = str(resp.topic_id)
    await wait(MIRROR_NODE_WAITING_TIME)

    # Attempt to add a submit key
    input_text = f"For topic {topic_without_submit_id}, change the submit key to my key"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # Verification
    # The tool logic catches the exception and returns it in the tool response
    human_message = tool_call.parsedData["humanMessage"]
    raw_error = tool_call.parsedData["raw"].get("error", "")

    expected_error_substr = (
        "Cannot update submit_key: topic was created without a submit_key"
    )

    assert expected_error_substr in human_message or expected_error_substr in raw_error
    assert "Failed to update topic" in human_message


@pytest.mark.asyncio
async def test_update_autorenew_account(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_topic: TopicId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test updating the autoRenewAccountId."""
    _, _, executor_client, _ = executor_account
    topic_id_str = str(test_topic)

    # Create a secondary account to serve as the new auto-renew account
    secondary_key = executor_client.operator_private_key
    secondary_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(0), key=secondary_key.public_key()
        )
    )
    secondary_account_id = str(secondary_resp.account_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = (
        f"For topic {topic_id_str} set auto renew account id to {secondary_account_id}."
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    topic_info = executor_wrapper.get_topic_info(topic_id_str)
    assert (
        topic_info.auto_renew_account.accountNum
        == AccountId.from_string(secondary_account_id).num
    )


@pytest.mark.asyncio
async def test_reject_unauthorized_update(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    operator_wrapper: HederaOperationsWrapper,
    operator_client,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test that updates are rejected if the agent does not hold the admin key."""

    # 1. Create a secondary "outsider" account
    outsider_key = PrivateKey.generate_ed25519()
    outsider_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=outsider_key.public_key()
        )
    )
    outsider_id = outsider_resp.account_id
    outsider_client = get_custom_client(outsider_id, outsider_key)
    outsider_wrapper = HederaOperationsWrapper(outsider_client)

    # 2. Outsider creates a topic (Admin Key = Outsider Key)
    resp = await outsider_wrapper.create_topic(
        CreateTopicParametersNormalised(
            admin_key=outsider_key.public_key(), memo="outsider-topic"
        )
    )
    outsider_topic_id = str(resp.topic_id)
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Agent (Executor) tries to update the outsider's topic
    # Agent signs with Executor Key, but Topic requires Outsider Key
    input_text = f"For topic {outsider_topic_id}, change the admin key to my key"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 4. Verification
    human_message = tool_call.parsedData["humanMessage"]
    raw_error = tool_call.parsedData["raw"].get("error", "")

    # The tool logic explicitly checks permissions in check_validity_of_updates
    expected_msg = "You do not have permission to update this topic"

    assert expected_msg in human_message or expected_msg in raw_error

    # Cleanup outsider
    await return_hbars_and_delete_account(
        outsider_wrapper, outsider_id, operator_client.operator_account_id
    )
