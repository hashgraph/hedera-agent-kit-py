"""End-to-end tests for create non-fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client, TokenType, SupplyType
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
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
    return RunnableConfig(configurable={"thread_id": "create_nft_e2e"})


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
async def test_create_nft_minimal_params(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating a non-fungible token with minimal params via natural language."""
    input_text = "Create a non-fungible token named MyNFT with symbol MNFT"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    token_id_str = extract_token_id(
        result, response_parser, "create_non_fungible_token_tool"
    )

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "MyNFT"
    assert token_info.symbol == "MNFT"
    assert token_info.token_type == TokenType.NON_FUNGIBLE_UNIQUE
    # Default supply type is finite
    assert token_info.supply_type == SupplyType.FINITE
    assert token_info.max_supply == 100 # the default max supply is 100


@pytest.mark.asyncio
async def test_create_nft_with_max_supply(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an NFT with explicit max supply."""
    input_text = (
        "Create a non-fungible token ArtCollection with symbol ART, "
        "and max supply 500"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    token_id_str = extract_token_id(
        result, response_parser, "create_non_fungible_token_tool"
    )

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "ArtCollection"
    assert token_info.symbol == "ART"
    assert token_info.max_supply == 500


@pytest.mark.asyncio
async def test_create_nft_with_explicit_finite_supply(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test creating an NFT with explicit finite supply type."""
    input_text = (
        "Create a non-fungible token LimitedEdition with symbol LTD, "
        "with finite supply and max supply 300"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    token_id_str = extract_token_id(
        result, response_parser, "create_non_fungible_token_tool"
    )

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "LimitedEdition"
    assert token_info.symbol == "LTD"
    assert token_info.supply_type == SupplyType.FINITE
    assert token_info.max_supply == 300


@pytest.mark.asyncio
async def test_schedule_create_nft(
    agent_executor,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test scheduling creation of an NFT successfully."""
    input_text = (
        "Create a non-fungible token named ScheduledNFT with symbol SNFT. "
        "Schedule the transaction instead of executing it immediately."
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = response_parser.parse_new_tool_messages(result)[0]

    parsed_data = tool_call.parsedData
    assert "Scheduled transaction created successfully" in parsed_data["humanMessage"]
    assert parsed_data["raw"].get("schedule_id") is not None
    assert parsed_data["raw"].get("transaction_id") is not None
