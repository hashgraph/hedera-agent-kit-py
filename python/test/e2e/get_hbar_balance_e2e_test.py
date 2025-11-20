"""End-to-end tests for Get HBAR Balance tool.

This module provides full E2E testing from simulated user input through the
LangChain agent, Hedera client interaction, to on-chain balance queries.
"""

from typing import AsyncGenerator, Any, cast
import pytest

from hiero_sdk_python import PrivateKey, Hbar
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.verification import extract_tool_response
from test.utils.teardown import return_hbars_and_delete_account
from test.utils import wait

DEFAULT_EXECUTOR_BALANCE = Hbar(5, in_tinybars=False)

# ============================================================================
# SESSION FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """Operator client for the session."""
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """Operator wrapper for account operations."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION FIXTURES
# ============================================================================


@pytest.fixture
async def executor_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary executor account used as agent operator."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    """Initialize LangChain agent and toolkit using executor client as operator."""
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    """Provide LangChain agent executor."""
    return langchain_test_setup.agent


@pytest.fixture
def langchain_config():
    """LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "1"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_get_hbar_balance(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute balance query through the agent."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )


def extract_balance_info(agent_result: dict[str, Any]) -> tuple[str, str]:
    """Extract account ID and balance from the agent result."""
    observation = extract_tool_response(agent_result, "get_hbar_balance_query_tool")
    parsed_observation = cast(ToolResponse, observation)
    print(f"observation: {observation}")
    print(f"parsed_observation: {parsed_observation}")

    account_id = parsed_observation.extra.get("account_id")
    balance = parsed_observation.extra.get("balance")

    if not account_id or balance is None:
        raise ValueError("Missing account_id or balance in tool response")

    return account_id, balance


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_get_hbar_balance_for_executor_account(
    agent_executor,
    executor_account,
    langchain_config,
):
    """Test fetching HBAR balance for executor (default) account."""
    executor_account_id, _, executor_client, executor_wrapper = executor_account
    executor_id_str = str(executor_account_id)

    expected_balance = executor_wrapper.get_account_hbar_balance(executor_id_str)

    input_text = f"What is the HBAR balance of {executor_id_str}?"
    result = await execute_get_hbar_balance(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_hbar_balance_query_tool")

    assert observation is not None
    assert observation.error is None
    assert executor_id_str in observation.human_message
    assert str(int(expected_balance)) in observation.human_message
    assert "HBAR Balance" in observation.human_message


@pytest.mark.asyncio
async def test_get_hbar_balance_for_specific_account_nonzero(
    agent_executor,
    executor_account,
    langchain_config,
):
    """Test fetching HBAR balance for a specific account with nonzero balance."""
    _, _, _, executor_wrapper = executor_account

    hbar_balance = 2
    resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(hbar_balance, in_tinybars=False),
            key=executor_wrapper.client.operator_private_key.public_key(),
        )
    )
    account_id = resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"What is the HBAR balance of {account_id}?"
    result = await execute_get_hbar_balance(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_hbar_balance_query_tool")

    assert str(account_id) in observation.human_message
    assert str(hbar_balance) in observation.human_message
    assert observation.error is None

    await return_hbars_and_delete_account(
        executor_wrapper,
        account_id,
        executor_wrapper.client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_get_hbar_balance_for_specific_account_zero_balance(
    agent_executor,
    executor_account,
    langchain_config,
):
    """Test fetching HBAR balance for an account with zero HBAR."""
    _, _, executor_client, executor_wrapper = executor_account

    resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(0),
            key=executor_wrapper.client.operator_private_key.public_key(),
        )
    )
    account_id = resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"What is the HBAR balance of {account_id}?"
    result = await execute_get_hbar_balance(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(result, "get_hbar_balance_query_tool")

    assert str(account_id) in observation.human_message
    assert "0" in observation.human_message
    assert observation.extra.get("balance") == "0"
    assert observation.error is None

    await return_hbars_and_delete_account(
        executor_wrapper,
        account_id,
        executor_wrapper.client.operator_account_id,
    )
