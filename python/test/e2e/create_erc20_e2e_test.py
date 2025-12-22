"""End-to-end tests for create ERC20 tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from datetime import datetime
from typing import AsyncGenerator, Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client

from test.utils.usd_to_hbar_service import UsdToHbarService
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper_instance = HederaOperationsWrapper(executor_client)

    # Wait for account creation to propagate to mirror nodes
    await wait(MIRROR_NODE_WAITING_TIME)

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=executor_client)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key_pair": executor_key_pair,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper_instance,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "toolkit": setup.toolkit,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture(scope="module")
def executor_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["executor_account_id"],
        res["executor_key_pair"],
        res["executor_client"],
        res["executor_wrapper"],
    )


@pytest.fixture(scope="module")
def executor_wrapper(setup_module_resources):
    return setup_module_resources["executor_wrapper"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def toolkit(setup_module_resources):
    return setup_module_resources["toolkit"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "create_erc20_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_create_erc20(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute ERC20 creation via the agent and return the parsed raw data."""
    response = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(response)

    if not parsed_tool_calls:
        raise ValueError("The create_erc20_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "create_erc20_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of create_erc20_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_erc20_minimal_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an ERC20 token with minimal params via natural language."""
    input_text = "Create an ERC20 token named MyERC20 with symbol M20"
    parsed_data = await execute_create_erc20(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "ERC20 token created successfully" in human_message
    erc20_address = raw_data.get("erc20_address")
    assert erc20_address is not None
    assert isinstance(erc20_address, str)
    assert erc20_address.startswith("0x")

    # Wait for transaction to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc20_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_create_erc20_with_decimals_and_supply(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an ERC20 token with decimals and initial supply."""
    input_text = "Create an ERC20 token GoldToken with symbol GLD, decimals 2, initial supply 1000"
    parsed_data = await execute_create_erc20(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "ERC20 token created successfully" in human_message
    erc20_address = raw_data.get("erc20_address")
    assert erc20_address is not None

    # Wait for transaction to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc20_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_create_erc20_scheduled(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test scheduling the creation of an ERC20 token."""
    # Use a unique name to avoid collisions
    name = f"SchedERC-{int(datetime.now().timestamp())}"
    symbol = f"S{int(datetime.now().timestamp()) % 1000}"
    input_text = f'Create an ERC20 token named "{name}" with symbol {symbol}. Schedule this transaction instead of executing it immediately.'

    parsed_data = await execute_create_erc20(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    # Validate response structure for a scheduled transaction
    assert "Scheduled creation of ERC20 successfully" in human_message
    assert raw_data is not None
    assert raw_data.get("transaction_id") is not None
    assert raw_data.get("schedule_id") is not None
    # We don't expect erc20_address yet since it's not executed immediately
    assert raw_data.get("erc20_address") is None
