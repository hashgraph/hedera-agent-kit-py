"""
End-to-end tests for airdrop fungible token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateFungibleTokenParametersNormalised,
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

    # Executor account (Agent performing airdrops)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75))
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # LangChain setup with RunnableConfig to avoid checkpointer error
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "airdrop_ft_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Define standard Token Params: Decimals 2, Init 100 (display format), Max 1000 (display format)
    FT_PARAMS = TokenParams(
        token_name="AirdropToken",
        token_symbol="DROP",
        decimals=2,
        initial_supply=100000,
        max_supply=1000000,
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


async def create_airdrop_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client,
    ft_params: TokenParams,
):
    treasury_pubkey = executor_client.operator_private_key.public_key()
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


async def create_recipient_account(wrapper: HederaOperationsWrapper) -> str:
    key = PrivateKey.generate_ed25519()
    resp = await wrapper.create_account(
        CreateAccountParametersNormalised(key=key.public_key(), initial_balance=Hbar(0))
    )
    return str(resp.account_id)


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    return tool_calls[0] if tool_calls else None


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_airdrop_single_recipient(setup_environment):
    env = setup_environment
    executor_client = env["executor_client"]
    executor_wrapper = env["executor_wrapper"]
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    ft_params = env["FT_PARAMS"]
    executor_account_id = env["executor_account_id"]

    token_id = await create_airdrop_token(executor_wrapper, executor_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    recipient_id = await create_recipient_account(executor_wrapper)
    input_text = f"Airdrop 50 of token {token_id_str} from {executor_account_id} to {recipient_id}"

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})
    assert "successfully airdropped" in human_message
    assert raw_data.get("status") == "SUCCESS"

    await wait(MIRROR_NODE_WAITING_TIME)
    pending = await executor_wrapper.get_pending_airdrops(str(recipient_id))
    assert len(pending.get("airdrops", [])) > 0


@pytest.mark.asyncio
async def test_airdrop_multiple_recipients(setup_environment):
    env = setup_environment
    executor_client = env["executor_client"]
    executor_wrapper = env["executor_wrapper"]
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    ft_params = env["FT_PARAMS"]
    executor_account_id = env["executor_account_id"]

    token_id = await create_airdrop_token(executor_wrapper, executor_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    recipient1 = await create_recipient_account(executor_wrapper)
    recipient2 = await create_recipient_account(executor_wrapper)

    input_text = (
        f"Airdrop 10 of token {token_id_str} from {executor_account_id} to {recipient1} "
        f"and 20 to {recipient2}"
    )

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})
    assert "successfully airdropped" in human_message
    assert raw_data.get("status") == "SUCCESS"

    await wait(MIRROR_NODE_WAITING_TIME)
    pending1 = await executor_wrapper.get_pending_airdrops(str(recipient1))
    pending2 = await executor_wrapper.get_pending_airdrops(str(recipient2))
    assert len(pending1.get("airdrops", [])) > 0
    assert len(pending2.get("airdrops", [])) > 0
