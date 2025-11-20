"""End-to-end tests for create fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from pprint import pprint
from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

DEFAULT_EXECUTOR_BALANCE = Hbar(50, in_tinybars=False)


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

    # Wait for account creation to propagate
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
    return RunnableConfig(configurable={"thread_id": "create_ft_e2e"})


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
