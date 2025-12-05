"""End-to-end tests for Get Pending Airdrop Query tool.

This module provides full E2E testing from simulated user input through the
LangChain agent, Hedera client interaction, to on-chain pending airdrop queries.
"""

import pytest
from typing import Any
from hiero_sdk_python import PrivateKey, Hbar, SupplyType
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from hiero_sdk_python.tokens.token_transfer import TokenTransfer
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    AirdropFungibleTokenParametersNormalised,
)
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
    Setup operator, executor (agent), token, and recipient for pending airdrop tests.
    """
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # 1. Create an executor account (The Agent)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Setup LangChain (Agent)
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "pending_airdrop_e2e"})

    # 3. Create Fungible Token
    ft_params = TokenParams(
        token_name="AirdropE2EToken",
        token_symbol="ADE",
        initial_supply=100000,
        decimals=2,
        max_supply=500000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
        auto_renew_account_id=executor_account_id,
    )
    ft_keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )

    create_token_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=ft_keys
    )
    token_resp = await executor_wrapper.create_fungible_token(create_token_params)
    token_id_ft = token_resp.token_id

    # 4. Create a recipient with 0 auto-associations (force airdrop to be pending)
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),  # Using an executor key for simplicity in test control
            initial_balance=Hbar(0),
            max_automatic_token_associations=0,
        )
    )
    recipient_id = recipient_resp.account_id

    # 5. Airdrop tokens
    airdrop_params = AirdropFungibleTokenParametersNormalised(
        token_transfers=[
            TokenTransfer(token_id=token_id_ft, account_id=recipient_id, amount=100),
            TokenTransfer(
                token_id=token_id_ft, account_id=executor_account_id, amount=-100
            ),
        ]
    )

    await executor_wrapper.airdrop_token(airdrop_params)

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_id": recipient_id,
        "token_id_ft": token_id_ft,
        "agent_executor": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "langchain_config": langchain_config,
    }

    # Teardown
    lc_setup.cleanup()

    # Delete recipient
    await return_hbars_and_delete_account(
        account_wrapper=executor_wrapper,
        account_to_delete=recipient_id,
        account_to_return=operator_client.operator_account_id,
    )

    # Delete executor
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
async def test_get_pending_airdrops_e2e(setup_environment):
    """Test fetching pending airdrops for a recipient account via Agent."""
    agent_executor = setup_environment["agent_executor"]
    langchain_config = setup_environment["langchain_config"]
    response_parser = setup_environment["response_parser"]
    recipient_id = setup_environment["recipient_id"]

    # 1. Execute Agent Request
    input_text = f"Show pending airdrops for account {recipient_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    # 2. Extract Data
    tool_call = extract_tool_result(result, response_parser)

    # 3. Assertions
    assert tool_call is not None

    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})
    pending_airdrops = raw_data.get("pending_airdrops", {}).get("airdrops", [])

    assert raw_data.get("error") is None
    assert f"pending airdrops for account **{recipient_id}**" in human_message
    assert len(pending_airdrops) > 0


@pytest.mark.asyncio
async def test_get_pending_airdrops_non_existent_account(setup_environment):
    """Test fetching pending airdrops for a non-existent account via Agent."""
    agent_executor = setup_environment["agent_executor"]
    langchain_config = setup_environment["langchain_config"]
    response_parser = setup_environment["response_parser"]

    non_existent_id = "0.0.999999999"

    # 1. Execute Agent Request
    input_text = f"Show pending airdrops for account {non_existent_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    # 2. Extract Data
    tool_call = extract_tool_result(result, response_parser)

    # 3. Assertions
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")

    assert (
        "No pending airdrops found" in human_message
        or "No pending airdrops" in human_message
    )
