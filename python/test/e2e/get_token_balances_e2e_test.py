"""End-to-end tests for Get Token Balances tool.

This module provides full E2E testing from simulated user input through the
LangChain agent, Hedera client interaction, to on-chain token balance queries.
"""

import pytest
from typing import Any
from hiero_sdk_python import PrivateKey, Hbar, SupplyType
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import TransferFungibleTokenParametersNormalised
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_environment():
    """
    Setup operator, executor (agent), and tokens for balance query tests.
    """
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Create an executor account (The Agent)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Setup LangChain (Agent)
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(
        configurable={"thread_id": "get_token_balances_e2e"}
    )

    # 3. Create a Fungible Token (Treasury is Operator for simplicity here)
    ft_params = TokenParams(
        token_name="E2E Balance Token",
        token_symbol="BAL",
        decimals=2,
        initial_supply=1000,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=operator_client.operator_account_id,
    )
    ft_keys = TokenKeys(
        supply_key=operator_client.operator_private_key.public_key(),
        admin_key=operator_client.operator_private_key.public_key(),
    )

    create_token_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=ft_keys
    )
    token_resp = await operator_wrapper.create_fungible_token(create_token_params)
    token_id = token_resp.token_id

    # 4. Associate Token with Executor
    await executor_wrapper.associate_token(
        {"accountId": str(executor_account_id), "tokenId": str(token_id)}
    )

    # 5. Transfer Tokens to Executor (so they have a balance to query)
    await operator_wrapper.transfer_fungible(
        TransferFungibleTokenParametersNormalised(
            ft_transfers={token_id: {executor_account_id: 25, operator_client.operator_account_id: -25}},
        )
    )


    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "token_id": token_id,
        "agent_executor": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "langchain_config": langchain_config,
    }

    # Teardown
    lc_setup.cleanup()

    await return_hbars_and_delete_account(
        account_wrapper=executor_wrapper,
        account_to_delete=executor_account_id,
        account_to_return=operator_client.operator_account_id,
    )

    executor_client.close()
    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


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
async def test_get_token_balances_for_specific_account(setup_environment):
    """Test fetching token balances for a specific account ID."""
    agent_executor = setup_environment["agent_executor"]
    langchain_config = setup_environment["langchain_config"]
    response_parser = setup_environment["response_parser"]
    executor_account_id = setup_environment["executor_account_id"]
    token_id = setup_environment["token_id"]

    # 1. Execute Agent Request
    input_text = f"Get the token balances for account {executor_account_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    # 2. Extract Data
    tool_call = extract_tool_result(result, response_parser)

    # 3. Assertions
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})

    # Check for core elements in the response
    assert "Token Balances" in human_message
    assert str(token_id) in human_message
    # We transferred 25 raw units
    assert "25" in human_message
    assert raw_data.get("error") is None


@pytest.mark.asyncio
async def test_get_token_balances_for_self(setup_environment):
    """Test fetching token balances for the agent's own account (context inference)."""
    agent_executor = setup_environment["agent_executor"]
    langchain_config = setup_environment["langchain_config"]
    response_parser = setup_environment["response_parser"]
    token_id = setup_environment["token_id"]

    # 1. Execute Agent Request
    input_text = "Show me my token balances"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    # 2. Extract Data
    tool_call = extract_tool_result(result, response_parser)

    # 3. Assertions
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})

    assert "Token Balances" in human_message
    assert str(token_id) in human_message
    assert "25" in human_message
    assert raw_data.get("error") is None


@pytest.mark.asyncio
async def test_get_token_balances_no_tokens(setup_environment):
    """Test fetching balances for an account that has no tokens."""
    agent_executor = setup_environment["agent_executor"]
    langchain_config = setup_environment["langchain_config"]
    response_parser = setup_environment["response_parser"]
    operator_client = setup_environment["operator_client"]
    operator_wrapper = setup_environment["operator_wrapper"]

    # Create a fresh account with no tokens
    empty_key = PrivateKey.generate_ed25519()
    empty_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=empty_key.public_key(), initial_balance=Hbar(1)
        )
    )
    empty_account_id = empty_resp.account_id

    await wait(MIRROR_NODE_WAITING_TIME)

    try:
        # 1. Execute Agent Request
        input_text = f"Check token balances for {empty_account_id}"
        result = await execute_agent_request(
            agent_executor, input_text, langchain_config
        )

        # 2. Extract Data
        tool_call = extract_tool_result(result, response_parser)

        # 3. Assertions
        assert tool_call is not None
        human_message = tool_call.parsedData.get("humanMessage", "")

        # Expecting a message indicating no tokens found
        assert "No token balances found" in human_message

    finally:
        # Cleanup the temporary account
        wrapper = HederaOperationsWrapper(
            get_custom_client(empty_account_id, empty_key)
        )
        await return_hbars_and_delete_account(
            wrapper, empty_account_id, operator_client.operator_account_id
        )
        wrapper.client.close()