"""
End-to-end tests for mint fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import Hbar, PrivateKey
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
    # This account will also act as the Treasury/Admin for the tokens it creates
    # so it has permission to mint.
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # LangChain Setup
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "mint_ft_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Define standard Token Params: Decimals 2, Init 100, Max 1000
    FT_PARAMS = TokenParams(
        token_name="MintableToken",
        token_symbol="MINT",
        decimals=2,
        initial_supply=100,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
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
    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_mintable_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client,
    ft_params: TokenParams,
):
    """
    Helper to create a Fungible Token using the wrapper.
    Ensures Supply Key is set to the executor so they can mint.
    """
    treasury_pubkey = executor_client.operator_private_key.public_key()

    # Supply key is required for minting
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
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_mint_additional_supply(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Setup: Create Token
    token_id = await create_mintable_token(executor_wrapper, executor_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Get supply before
    info_before = executor_wrapper.get_token_info(token_id_str)
    supply_before = info_before.total_supply

    # 2. Execute
    # "Mint 5" means 5 units of display value.
    # Since decimals=2, this translates to 500 tiny units (5.00).
    input_text = f"Mint 5 of token {token_id_str}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Response
    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})

    assert "successfully minted" in human_message
    assert raw_data.get("status") == "SUCCESS"

    # 4. Verify On-Chain
    await wait(MIRROR_NODE_WAITING_TIME)

    info_after = executor_wrapper.get_token_info(token_id_str)
    supply_after = info_after.total_supply

    # Expected: 5 * 10^2 = 500 additional units
    assert supply_after == supply_before + 500


@pytest.mark.asyncio
async def test_schedule_minting(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Setup
    token_id = await create_mintable_token(executor_wrapper, executor_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Execute
    input_text = (
        f"Mint 5 of token {token_id_str}. "
        "Schedule the transaction instead of executing it immediately."
    )

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Response
    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})

    assert "Scheduled mint transaction created successfully" in human_message
    assert raw_data.get("schedule_id") is not None


@pytest.mark.asyncio
async def test_fail_mint_max_supply_exceeded(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Setup
    token_id = await create_mintable_token(executor_wrapper, executor_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Max supply is 1000 (raw units). Initial supply is 100.
    # Attempt to mint 5000 display units -> 500,000 raw units.
    input_text = f"Mint 5000 of token {token_id_str}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Failure
    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_error = tool_call.parsedData.get("raw", {}).get("error", "")

    # Check for specific Hedera error code related to max supply
    # Note: precise error message depends on SDK/Tool wrapper exception handling
    assert (
        "TOKEN_MAX_SUPPLY_REACHED" in raw_error
        or "TOKEN_MAX_SUPPLY_REACHED" in human_message
    )


@pytest.mark.asyncio
async def test_fail_mint_non_existent_token(setup_environment):
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]

    fake_token_id = "0.0.999999999"

    input_text = f"Mint 10 of token {fake_token_id}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_error = tool_call.parsedData.get("raw", {}).get("error", "")

    assert "Not Found" in human_message or "Failed" in human_message
    assert raw_error
