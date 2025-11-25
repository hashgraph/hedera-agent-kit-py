"""End-to-end tests for delete HBAR allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import asyncio
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    CreateAccountParametersNormalised,
    ApproveHbarAllowanceParametersNormalised,
    HbarAllowance,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(30, in_tinybars=False)
MIRROR_NODE_WAITING_TIME_SEC = 10


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
    """Create a temporary executor account for tests (the agent/owner).

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

    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    yield executor_account_id, executor_key_pair, executor_client, executor_wrapper_instance

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def spender_account(
        executor_account, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a separate spender account.

    Yields:
        tuple: (account_id, private_key, client, wrapper)
    """
    spender_key: PrivateKey = PrivateKey.generate_ed25519()
    _, _, executor_client, executor_wrapper = executor_account

    # Executor creates spender funded with a small balance
    spender_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5),
            key=spender_key.public_key(),
        )
    )

    spender_id = spender_resp.account_id
    spender_client = get_custom_client(spender_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    yield spender_id, spender_key, spender_client, spender_wrapper

    # Cleanup
    await return_hbars_and_delete_account(
        spender_wrapper,
        spender_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "delete_allowance_e2e"})


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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def approve_allowance(
        owner_wrapper: HederaOperationsWrapper,
        spender_id: AccountId,
        amount_hbar: float,
):
    """Helper to approve HBAR allowance from Owner to Spender."""
    amount_tinybar = int(Hbar(amount_hbar).to_tinybars())
    allowance_params = ApproveHbarAllowanceParametersNormalised(
        hbar_allowances=[
            HbarAllowance(
                spender_account_id=spender_id,
                amount=amount_tinybar,
            )
        ]
    )
    await owner_wrapper.approve_hbar_allowance(allowance_params)
    # Wait for mirror node to index allowance
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)


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
        return None
    return tool_calls[0]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_delete_existing_allowance(
        agent_executor,
        executor_account,
        spender_account,
        langchain_config: RunnableConfig,
        response_parser: ResponseParserService,
):
    """Test deleting an existing allowance via natural language."""
    # 1. Setup
    owner_id, _, _, executor_wrapper = executor_account
    spender_id, _, _, _ = spender_account

    # Grant allowance first
    await approve_allowance(executor_wrapper, spender_id, 1.5)

    # 2. Execute Deletion via Agent
    input_text = f"Delete HBAR allowance from {owner_id} to {spender_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Response
    assert tool_call is not None
    assert "HBAR allowance deleted successfully" in tool_call.parsedData["humanMessage"]
    assert tool_call.parsedData["raw"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_delete_non_existent_allowance(
        agent_executor,
        executor_account,
        spender_account,
        langchain_config: RunnableConfig,
        response_parser: ResponseParserService,
):
    """Test deleting a non-existent allowance (should succeed gracefully)."""
    # 1. Setup (No prior allowance granted)
    owner_id, _, _, _ = executor_account
    spender_id, _, _, _ = spender_account

    # 2. Execute Deletion via Agent
    input_text = f"Delete HBAR allowance from {owner_id} to {spender_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Response
    # Setting allowance to 0 for an account with no allowance is a valid transaction
    assert tool_call is not None
    assert "HBAR allowance deleted successfully" in tool_call.parsedData["humanMessage"]
    assert tool_call.parsedData["raw"]["status"] == "SUCCESS"