"""End-to-end tests for create fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from pprint import pprint
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

DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key.public_key(),
        )
    )

    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=executor_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture(scope="module")
def executor_account(setup_module_resources):
    res = setup_module_resources
    # Accessor for backward compatibility and test usage
    return (
        res["executor_account_id"],
        res["executor_key"],
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
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "create_ft_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def extract_token_id(
    agent_result: dict[str, Any], response_parser: ResponseParserService, tool_name: str
) -> str:
    """Helper to parse the agent result and extract the created token ID."""
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")

    target_call = next(
        (call for call in parsed_tool_calls if call.toolName == tool_name), None
    )

    if not target_call:
        raise ValueError(f"Tool {tool_name} was not called in the response")

    # The token_id might be in 'token_id' field of the 'raw' dictionary
    raw_data = target_call.parsedData.get("raw", {})
    token_id = raw_data.get("token_id")

    if not token_id:
        # Fallback or error if structure differs
        raise ValueError(f"Token ID not found in tool response: {raw_data}")

    return str(token_id)


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute a request via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_create_fungible_token_minimal_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating a fungible token with minimal params via natural language."""
    input_text = "Create a fungible token named MyToken with symbol MTK"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    token_id_str = extract_token_id(
        result, response_parser, "create_fungible_token_tool"
    )

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "MyToken"
    assert token_info.symbol == "MTK"
    assert token_info.decimals == 0


@pytest.mark.asyncio
async def test_create_fungible_token_complex_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating a token with supply, decimals, and finite supply type."""
    input_text = (
        "Create a fungible token GoldCoin with symbol GLD, "
        "initial supply 1000, decimals 2, finite supply with max supply 5000"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    token_id_str = extract_token_id(
        result, response_parser, "create_fungible_token_tool"
    )

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "GoldCoin"
    assert token_info.symbol == "GLD"
    assert token_info.decimals == 2

    # Note: SDK/Mirror node usually reports supply in smallest units
    # If user input 1000 with decimals 2, check if normalizer scaled it or kept it raw.
    # Based on TS test expectation (5000 -> 500000), it scales input by decimals.
    # 1000 * 100 = 100,000
    # 5000 * 100 = 500,000
    assert token_info.total_supply == 100000
    assert token_info.max_supply == 500000


@pytest.mark.asyncio
async def test_schedule_create_fungible_token(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test scheduling creation of a FT successfully."""
    input_text = (
        "Create a fungible token named MyToken with symbol MTK. "
        "Schedule the transaction instead of executing it immediately."
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = response_parser.parse_new_tool_messages(result)[0]

    parsed_data = tool_call.parsedData
    assert "Scheduled transaction created successfully" in parsed_data["humanMessage"]
    assert parsed_data["raw"].get("schedule_id") is not None
    assert parsed_data["raw"].get("transaction_id") is not None


@pytest.mark.asyncio
async def test_create_fungible_token_invalid_params(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test handling invalid requests gracefully (initial supply > max supply)."""
    input_text = (
        "Create a fungible token BrokenToken with symbol BRK, "
        "initial supply 2000 and max supply 1000"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    pprint(result)
    ai_response = result["messages"][-1]

    # Expect error regarding supply constraint
    assert "token id" not in ai_response.content
