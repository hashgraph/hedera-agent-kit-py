"""End-to-end tests for Get Account Query tool.

This module validates querying account information through the LangChain agent,
Hedera client interaction, and Mirror Node queries.
"""

import pytest
from hiero_sdk_python import PrivateKey, Hbar
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import (
    create_langchain_test_setup,
    wait,
)
from test.utils.setup import (
    get_operator_client_for_tests,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.verification import extract_tool_response


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
async def langchain_test_setup():
    """Initialize LangChain agent and toolkit using an operator client as context."""
    setup = await create_langchain_test_setup()
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


@pytest.fixture
async def hedera_ops(operator_client):
    """Provide Hedera operations wrapper."""
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_get_account_query(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute account query through the agent."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_get_account_query_for_newly_created_account(
    agent_executor,
    hedera_ops,
    langchain_config,
):
    """Test fetching account info for a newly created account via agent."""
    private_key = PrivateKey.generate_ed25519()
    create_resp = await hedera_ops.create_account(
        CreateAccountParametersNormalised(
            key=private_key.public_key(),
            initial_balance=Hbar(1, in_tinybars=False),
        )
    )
    account_id = create_resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    input_text = f"Get account info for {account_id}"
    query_result = await execute_get_account_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(query_result, "get_account_query_tool")

    assert observation.error is None
    assert f"Details for {account_id}" in observation.human_message
    assert "Balance:" in observation.human_message
    assert "Public Key:" in observation.human_message
    assert "EVM address:" in observation.human_message

    # Direct validation
    info = hedera_ops.get_account_info(str(account_id))
    assert str(info.account_id) == str(account_id)
    assert info.balance is not None
    assert info.key is not None
    assert info.key.to_string_der() == private_key.public_key().to_string_der()


@pytest.mark.asyncio
async def test_get_account_query_for_operator_account(
    agent_executor,
    operator_client,
    hedera_ops,
    langchain_config,
):
    """Test fetching account info for the operator account via agent."""
    operator_id = str(operator_client.operator_account_id)

    input_text = f"Query details for account {operator_id}"
    query_result = await execute_get_account_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(query_result, "get_account_query_tool")

    assert observation.error is None
    assert f"Details for {operator_id}" in observation.human_message
    assert "Balance:" in observation.human_message
    assert "Public Key:" in observation.human_message
    assert "EVM address:" in observation.human_message

    info = hedera_ops.get_account_info(operator_id)
    assert str(info.account_id) == operator_id


@pytest.mark.asyncio
async def test_get_account_query_for_nonexistent_account(
    agent_executor,
    langchain_config,
):
    """Test that querying a nonexistent account fails gracefully."""
    fake_account_id = "0.0.999999999"

    input_text = f"Get account info for {fake_account_id}"
    query_result = await execute_get_account_query(
        agent_executor, input_text, langchain_config
    )
    observation = extract_tool_response(query_result, "get_account_query_tool")

    assert "Failed" in observation.human_message
    assert fake_account_id in observation.human_message
