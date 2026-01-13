"""
End-to-end tests for mint non-fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
    TokenType,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateNonFungibleTokenParametersNormalised,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account

# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_environment(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Executor account (The Agent)
    # This account will also act as the Treasury/Admin for the tokens it creates
    # so it has permission to mint.
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])
            ),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # LangChain Setup
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "mint_nft_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Define standard NFT Params
    NFT_PARAMS = TokenParams(
        token_name="MintableNFT",
        token_symbol="MNFT",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        max_supply=100,
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
        "NFT_PARAMS": NFT_PARAMS,
    }

    # Teardown
    lc_setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_mintable_nft(
    executor_wrapper: HederaOperationsWrapper,
    executor_client,
    nft_params: TokenParams,
):
    """
    Helper to create a Non-Fungible Token using the wrapper.
    Ensures Supply Key is set to the executor so they can mint.
    """
    treasury_pubkey = executor_client.operator_private_key.public_key()

    # Supply key is required for minting
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)

    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=keys
    )
    resp = await executor_wrapper.create_non_fungible_token(create_params)
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
async def test_mint_single_nft(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    nft_params: TokenParams = setup_environment["NFT_PARAMS"]

    # 1. Setup: Create Token
    token_id = await create_mintable_nft(executor_wrapper, executor_client, nft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Get supply before
    info_before = executor_wrapper.get_token_info(token_id_str)
    supply_before = info_before.total_supply

    # 2. Execute
    input_text = f"Mint 1 NFT of token {token_id_str} with metadata ipfs://meta1.json"

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

    assert supply_after == supply_before + 1


@pytest.mark.asyncio
async def test_mint_multiple_nfts(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    nft_params: TokenParams = setup_environment["NFT_PARAMS"]

    # 1. Setup
    token_id = await create_mintable_nft(executor_wrapper, executor_client, nft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Get supply before
    info_before = executor_wrapper.get_token_info(token_id_str)
    supply_before = info_before.total_supply

    uris = ["ipfs://meta2.json", "ipfs://meta3.json", "ipfs://meta4.json"]

    # 2. Execute
    input_text = (
        f"Mint {len(uris)} NFTs of token {token_id_str} with metadata {', '.join(uris)}"
    )

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

    assert supply_after == supply_before + len(uris)


@pytest.mark.asyncio
async def test_schedule_minting_nft(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    nft_params: TokenParams = setup_environment["NFT_PARAMS"]

    # 1. Setup
    token_id = await create_mintable_nft(executor_wrapper, executor_client, nft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Execute
    input_text = (
        f"Mint 1 NFT of token {token_id_str} with metadata 'ipfs://meta1.json'. "
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
async def test_fail_mint_non_existent_token(setup_environment):
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]

    fake_token_id = "0.0.999999999"

    input_text = f"Mint 1 NFT of token {fake_token_id} with metadata ipfs://meta.json"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_error = tool_call.parsedData.get("raw", {}).get("error", "")

    assert "INVALID_TOKEN_ID" in human_message or "Failed" in human_message
    assert raw_error
