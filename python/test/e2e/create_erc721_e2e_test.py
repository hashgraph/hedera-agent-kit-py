"""End-to-end tests for create ERC721 tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution for ERC721 deployments.
"""

from datetime import datetime
from typing import AsyncGenerator, Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
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
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))


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
    return RunnableConfig(configurable={"thread_id": "create_erc721_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_create_erc721(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute ERC721 creation via the agent and return the parsed raw data."""
    response = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(response)

    if not parsed_tool_calls:
        raise ValueError("The create_erc721_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "create_erc721_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of create_erc721_tool"
        )

    return tool_call.parsedData


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_erc721_minimal_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an ERC721 token with minimal params via natural language."""
    input_text = "Create an ERC721 token named MyERC721 with symbol MNFT"
    parsed_data = await execute_create_erc721(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "ERC721 token created successfully" in human_message
    erc721_address = raw_data.get("erc721_address")
    assert erc721_address is not None
    assert isinstance(erc721_address, str)
    assert erc721_address.startswith("0x")

    # Wait for transaction to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc721_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_create_erc721_with_base_uri(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an ERC721 token with a base URI via natural language."""
    input_text = "Create an ERC721 token named ArtCollection with symbol ART and base URI https://example.com/metadata/"
    parsed_data = await execute_create_erc721(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "ERC721 token created successfully" in human_message
    erc721_address = raw_data.get("erc721_address")
    assert erc721_address is not None
    assert isinstance(erc721_address, str)
    assert erc721_address.startswith("0x")

    # Wait for transaction to propagate
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain contract info
    contract_info = await executor_wrapper.get_contract_info(erc721_address)
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_schedule_create_erc721(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test scheduling the creation of an ERC721 token via natural language."""
    name = f"SchedERC721-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    input_text = (
        f"Schedule deploy ERC721 token called {name} with symbol SNFT and base URI ipfs://collection/. "
        "Schedule this transaction instead of executing it immediately."
    )
    parsed_data = await execute_create_erc721(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert "Scheduled creation of ERC721 successfully" in human_message
    assert raw_data.get("schedule_id") is not None
    assert raw_data.get("transaction_id") is not None
