"""
End-to-end tests for get token info tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import Hbar, PrivateKey, AccountId
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateFungibleTokenParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_environment():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Executor account (The Agent)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Token Creator / Treasury account (Holds the token to be queried)
    token_executor_key = PrivateKey.generate_ed25519()
    token_executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=token_executor_key.public_key(), initial_balance=Hbar(20)
        )
    )
    token_executor_account_id = token_executor_resp.account_id
    token_executor_client = get_custom_client(
        token_executor_account_id, token_executor_key
    )
    token_executor_wrapper = HederaOperationsWrapper(token_executor_client)

    # LangChain Setup
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "get_token_info_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    FT_PARAMS = TokenParams(
        token_name="InfoToken",
        token_symbol="INFO",
        initial_supply=1000,
        decimals=0,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=token_executor_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "token_executor_client": token_executor_client,
        "token_executor_wrapper": token_executor_wrapper,
        "token_executor_account_id": token_executor_account_id,
        "agent_executor": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "langchain_config": langchain_config,
        "FT_PARAMS": FT_PARAMS,
    }

    # Teardown
    lc_setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        token_executor_wrapper,
        token_executor_account_id,
        operator_client.operator_account_id,
    )
    token_executor_client.close()

    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client,
    treasury_account_id: AccountId,
    ft_params: TokenParams,
):
    treasury_pubkey = executor_client.operator_private_key.public_key()
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


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
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_token_info_happy_path(setup_environment):
    # Unpack fixture
    token_executor_client = setup_environment["token_executor_client"]
    token_executor_wrapper = setup_environment["token_executor_wrapper"]
    token_executor_account_id = setup_environment["token_executor_account_id"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Create a token via a treasury client (wrapper approach)
    token_id = await create_test_token(
        token_executor_wrapper,
        token_executor_client,
        token_executor_account_id,
        ft_params,
    )
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Agent Execution
    input_text = f"Get token info for token {token_id_str}"
    result = await execute_agent_request(agent_executor, input_text, config)

    # 3. Extraction
    tool_call = extract_tool_result(result, response_parser)

    # 4. Verification
    assert tool_call is not None

    # Extract data based on valid schema structure
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})
    token_info = raw_data.get("tokenInfo", {})

    # Verify human readable content
    assert ft_params.token_name in human_message
    assert ft_params.token_symbol in human_message
    assert token_id_str in human_message

    # Verify structured data
    assert token_info.get("token_id") == token_id_str
    assert token_info.get("name") == ft_params.token_name
    assert token_info.get("symbol") == ft_params.token_symbol
    assert "1000" in human_message


@pytest.mark.asyncio
async def test_get_token_info_non_existent(setup_environment):
    # Unpack fixture
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]

    fake_token_id = "0.0.999999999"

    input_text = f"Get information for token {fake_token_id}"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None

    # Check error handling
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_error = tool_call.parsedData.get("raw", {}).get("error", "")

    assert "Failed to get token info" in human_message or "Not Found" in human_message
    assert raw_error
