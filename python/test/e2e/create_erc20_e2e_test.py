"""End-to-end tests for create ERC20 tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

# Constants
# ERC20 creation is more expensive than topic creation
DEFAULT_EXECUTOR_BALANCE = Hbar(20, in_tinybars=False)
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

    # Wait for account creation to propagate to mirror nodes
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

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
    return RunnableConfig(configurable={"thread_id": "create_erc20_e2e"})


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


async def execute_create_erc20(
    agent_executor, input_text: str, config: RunnableConfig
) -> ExecutedTransactionToolResponse:
    """Execute ERC20 creation via the agent and return the parsed response dict."""
    response = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Extract the tool response
    tool_response = extract_tool_response(response, "create_erc20_tool")

    # Ensure it's the correct type
    if not isinstance(tool_response, ExecutedTransactionToolResponse):
        raise TypeError(
            f"Expected ExecutedTransactionToolResponse, got {type(tool_response)}"
        )

    return tool_response


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_erc20_minimal_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
):
    """Test creating an ERC20 token with minimal params via natural language."""
    input_text = "Create an ERC20 token named MyERC20 with symbol M20"
    response: ExecutedTransactionToolResponse = await execute_create_erc20(
        agent_executor, input_text, langchain_config
    )

    assert "ERC20 token created successfully" in response.human_message
    assert response.extra is not None
    erc20_address = response.extra.get("erc20_address")
    assert erc20_address is not None
    assert erc20_address.startswith("0x")

    # Wait for transaction to propagate
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc20_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_create_erc20_with_decimals_and_supply(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
):
    """Test creating an ERC20 token with decimals and initial supply."""
    input_text = "Create an ERC20 token GoldToken with symbol GLD, decimals 2, initial supply 1000"
    response: ExecutedTransactionToolResponse = await execute_create_erc20(
        agent_executor, input_text, langchain_config
    )

    assert "ERC20 token created successfully" in response.human_message
    assert response.extra is not None
    erc20_address = response.extra.get("erc20_address")
    assert erc20_address is not None

    # Wait for transaction to propagate
    await asyncio.sleep(MIRROR_NODE_WAITING_TIME_SEC)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc20_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_create_erc20_scheduled(
    agent_executor,
    langchain_config: RunnableConfig,
):
    """Test scheduling the creation of an ERC20 token."""
    # Use a unique name to avoid collisions
    name = f"SchedERC-{int(datetime.now().timestamp())}"
    symbol = f"S{int(datetime.now().timestamp()) % 1000}"
    input_text = f'Create an ERC20 token named "{name}" with symbol {symbol}. Schedule this transaction instead of executing it immediately.'

    response: ExecutedTransactionToolResponse = await execute_create_erc20(
        agent_executor, input_text, langchain_config
    )

    # Validate response structure for a scheduled transaction
    assert "Scheduled creation of ERC20 successfully" in response.human_message
    assert response.raw is not None
    assert response.raw.transaction_id is not None
    assert response.raw.schedule_id is not None
