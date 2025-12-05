"""
End-to-end tests for transfer_erc20 tool.

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
    CreateERC20Parameters,
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
    """Setup test environment with ERC20 token and accounts."""
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
    langchain_config = RunnableConfig(configurable={"thread_id": "transfer_erc20_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Create test ERC20 token with initial supply
    create_params = CreateERC20Parameters(
        token_name="TestTransferToken",
        token_symbol="TTT",
        decimals=18,
        initial_supply=1000,
    )

    create_result = await executor_wrapper.create_erc20(create_params)

    if not create_result.get("erc20_address"):
        raise Exception("Failed to create test ERC20 token for transfers")

    test_token_address = create_result["erc20_address"]
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


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute an agent request with the given input text."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    """Extract tool result from agent response."""
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    return tool_calls[0] if tool_calls else None


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_transfer_erc20_via_natural_language(setup_environment):
    """Test transferring ERC20 tokens via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]

    input_text = (
        f"Transfer 10 ERC20 tokens {test_token_address} to {recipient_account_id}"
    )

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["status"] == "SUCCESS"
    assert parsed_data["raw"]["transaction_id"] is not None

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify the balance after transfer
    executor_wrapper = env["executor_wrapper"]
    recipient_balance = await executor_wrapper.get_erc20_balance(
        test_token_address, str(recipient_account_id)
    )
    expected_balance = 10
    assert (
        recipient_balance == expected_balance
    ), f"Expected balance {expected_balance}, got {recipient_balance}"


@pytest.mark.asyncio
async def test_handle_various_natural_language_variations(setup_environment):
    """Test handling various natural language variations for transfers."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]

    variations = [
        f"Transfer 1 ERC20 token {test_token_address} to {recipient_account_id}",
        f"Send 5 ERC20 tokens {test_token_address} to recipient {recipient_account_id}",
        f"Transfer 2 tokens of contract {test_token_address} to address {recipient_account_id}",
    ]

    total_transferred = 0
    for input_text in variations:
        result = await execute_agent_request(agent_executor, input_text, config)
        tool_call = extract_tool_result(result, response_parser)

        assert tool_call is not None
        parsed_data = tool_call.parsedData
        assert parsed_data["raw"]["status"] == "SUCCESS"
        assert parsed_data["raw"]["transaction_id"] is not None

        # Extract amount from the input text
        amount_str = input_text.split()[1]
        total_transferred += int(amount_str)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify the cumulative balance after all transfers
    executor_wrapper = env["executor_wrapper"]
    recipient_balance = await executor_wrapper.get_erc20_balance(
        test_token_address, str(recipient_account_id)
    )
    # Total transferred: 1 + 5 + 2 = 8 tokens, plus 10 from the first test = 18 base units
    expected_balance = 18
    assert (
        recipient_balance == expected_balance
    ), f"Expected balance {expected_balance}, got {recipient_balance}"


@pytest.mark.asyncio
async def test_schedule_transfer_erc20_via_natural_language(setup_environment):
    """Test scheduling a transfer of ERC20 tokens via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    test_token_address = env["test_token_address"]
    recipient_account_id = env["recipient_account_id"]

    input_text = (
        f"Transfer 10 ERC20 tokens {test_token_address} to {recipient_account_id}. "
        f"Schedule this transaction."
    )

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["transaction_id"] is not None
    assert parsed_data["raw"]["schedule_id"] is not None
    assert (
        "scheduled transfer of erc20 successfully"
        in parsed_data["humanMessage"].lower()
    )
