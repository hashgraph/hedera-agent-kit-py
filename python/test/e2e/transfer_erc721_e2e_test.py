"""
End-to-end tests for transfer_erc721 tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateERC721Parameters,
    MintERC721Parameters,
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
    """Setup test environment with ERC721 token and accounts."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Executor account (Agent performing transfers)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Recipient account
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(5)
        )
    )
    recipient_account_id = recipient_resp.account_id

    # LangChain setup with RunnableConfig to avoid checkpointer error
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "transfer_erc721_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Create test ERC721 token
    create_params = CreateERC721Parameters(
        token_name="TestNFT",
        token_symbol="TNFT",
        base_uri="https://example.com/metadata/",
    )

    create_result = await executor_wrapper.create_erc721(create_params)

    if not create_result.get("erc721_address"):
        raise Exception("Failed to create test ERC721 token for transfers")

    test_token_address = create_result["erc721_address"]
    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_account_id": recipient_account_id,
        "agent_executor": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "langchain_config": langchain_config,
        "test_token_address": test_token_address,
        "next_token_id": 0,
    }

    # Teardown
    lc_setup.cleanup()
    await return_hbars_and_delete_account(
        executor_wrapper, recipient_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def mint_token_for_transfer(setup_env):
    """Helper to mint a new NFT for transfer tests."""
    wrapper = setup_env["executor_wrapper"]
    token_address = setup_env["test_token_address"]
    executor_account_id = setup_env["executor_account_id"]
    token_id = setup_env["next_token_id"]

    mint_params = MintERC721Parameters(
        contract_id=token_address,
        to_address=str(executor_account_id),
    )

    await wrapper.mint_erc721(mint_params)
    await wait(MIRROR_NODE_WAITING_TIME)

    setup_env["next_token_id"] += 1
    return token_id


async def execute_agent_request(
    agent_executor: Any, input_text: str, config: RunnableConfig
):
    """Execute agent request and return result."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )


def extract_tool_result(result: Any, response_parser: ResponseParserService):
    """Extract tool result from agent response."""
    parsed_response = response_parser.parse_new_tool_messages(result)
    if not parsed_response or len(parsed_response) == 0:
        return None
    return parsed_response[0]


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_transfer_erc721_via_natural_language(setup_environment):
    """Test transferring ERC721 tokens via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]
    executor_account_id = env["executor_account_id"]

    # Mint a token first
    token_id = await mint_token_for_transfer(env)

    input_text = f"Transfer ERC721 token {test_token_address} with id {token_id} from {executor_account_id} to {recipient_account_id}"
    print(input_text)

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["status"] == "SUCCESS"
    assert parsed_data["raw"]["transaction_id"] is not None

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify the ownership after transfer
    executor_wrapper = env["executor_wrapper"]
    recipient_info = await executor_wrapper.get_account_info_mirrornode(
        str(recipient_account_id)
    )
    recipient_evm_address = recipient_info.get("evm_address")

    owner_address = await executor_wrapper.get_erc721_owner(
        test_token_address, token_id
    )
    assert (
        owner_address.lower() == recipient_evm_address.lower()
    ), f"Expected owner {recipient_evm_address}, got {owner_address}"


@pytest.mark.asyncio
async def test_transfer_with_explicit_from_address(setup_environment):
    """Test transferring token with explicit from address."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]

    # Mint a token first
    token_id = await mint_token_for_transfer(env)

    input_text = f"Transfer erc721 {token_id} of contract {test_token_address} to address {recipient_account_id}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["status"] == "SUCCESS"
    assert parsed_data["raw"]["transaction_id"] is not None

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify the ownership after transfer
    executor_wrapper = env["executor_wrapper"]
    recipient_info = await executor_wrapper.get_account_info_mirrornode(
        str(recipient_account_id)
    )
    recipient_evm_address = recipient_info.get("evm_address")

    owner_address = await executor_wrapper.get_erc721_owner(
        test_token_address, token_id
    )
    assert (
        owner_address.lower() == recipient_evm_address.lower()
    ), f"Expected owner {recipient_evm_address}, got {owner_address}"


@pytest.mark.asyncio
async def test_schedule_transfer_erc721_via_natural_language(setup_environment):
    """Test scheduling transfer of ERC721 token via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]
    executor_account_id = env["executor_account_id"]

    # Mint a token first
    token_id = await mint_token_for_transfer(env)

    input_text = f"Transfer ERC721 token {test_token_address} with id {token_id} from {executor_account_id} to {recipient_account_id}. Schedule this transaction."

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["transaction_id"] is not None
    assert parsed_data["raw"]["schedule_id"] is not None
    assert "Scheduled transfer of ERC721 successfully" in parsed_data["humanMessage"]


@pytest.mark.asyncio
async def test_fail_gracefully_with_non_existent_token_id(setup_environment):
    """Test that transfer fails gracefully with non-existent token ID."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]

    input_text = f"Transfer ERC721 token 999999 from {test_token_address} to {recipient_account_id}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert "Failed to transfer ERC721" in parsed_data["humanMessage"]
