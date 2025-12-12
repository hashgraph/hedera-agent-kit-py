"""
End-to-end tests for dissociate token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

import pytest
from typing import Any
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    TokenId,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import (
    TokenParams,
    TokenKeys,
    SupplyType,
)
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
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

    # 1. Executor Account (The Agent) - Needs HBAR to pay for dissociation
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75))
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Token Creator Account (Treasury) - Mints the tokens we will test with
    creator_key = PrivateKey.generate_ed25519()
    creator_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=creator_key.public_key(), initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75))
        )
    )
    creator_account_id = creator_resp.account_id
    creator_client = get_custom_client(creator_account_id, creator_key)
    creator_wrapper = HederaOperationsWrapper(creator_client)

    # 3. LangChain Setup
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(
        configurable={"thread_id": "dissociate_token_e2e"}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # Base Token Params
    FT_PARAMS = TokenParams(
        token_name="DissocToken",
        token_symbol="DISS",
        decimals=0,
        initial_supply=1000,
        max_supply=5000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=creator_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "creator_client": creator_client,
        "creator_wrapper": creator_wrapper,
        "creator_account_id": creator_account_id,
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
        creator_wrapper, creator_account_id, operator_client.operator_account_id
    )
    creator_client.close()

    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_token(
    creator_wrapper: HederaOperationsWrapper,
    creator_client,
    ft_params: TokenParams,
) -> TokenId:
    """Helper to create a token using the Creator account."""
    treasury_pubkey = creator_client.operator_private_key.public_key()
    keys = TokenKeys(supply_key=treasury_pubkey, admin_key=treasury_pubkey)
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )
    resp = await creator_wrapper.create_fungible_token(create_params)
    return resp.token_id


async def check_token_is_associated(
    wrapper: HederaOperationsWrapper, account_id: str, token_id_str: str
) -> bool:
    """Checks if a specific token ID is present in the account's balances."""
    balances = wrapper.get_account_balances(account_id)
    if balances.token_balances:
        # Check if the token ID string exists in the token_balances dictionary keys
        for t_id in balances.token_balances.keys():
            if str(t_id) == token_id_str:
                return True
    return False


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
async def test_dissociate_single_token(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    executor_key = setup_environment["executor_key"]
    creator_client = setup_environment["creator_client"]
    creator_wrapper = setup_environment["creator_wrapper"]

    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Setup: Create Token
    token_id = await create_test_token(creator_wrapper, creator_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Setup: Associate Token manually
    await executor_wrapper.associate_token(
        {"accountId": str(executor_account_id), "tokenId": str(token_id)}
    )
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify association before test
    is_associated = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str
    )
    assert is_associated, "Setup failed: Token was not associated"

    # 3. Agent Execution
    input_text = f"Dissociate {token_id_str} from my account"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 4. Verify Response
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_data = tool_call.parsedData.get("raw", {})

    assert "successfully dissociated" in human_message
    assert raw_data.get("status") == "SUCCESS"

    # 5. Verify On-Chain (Dissociation)
    await wait(MIRROR_NODE_WAITING_TIME)

    is_still_associated = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str
    )
    assert not is_still_associated, "Token should be dissociated but is still found"


@pytest.mark.asyncio
async def test_dissociate_multiple_tokens(setup_environment):
    executor_client = setup_environment["executor_client"]
    executor_wrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    executor_key = setup_environment["executor_key"]
    creator_client = setup_environment["creator_client"]
    creator_wrapper = setup_environment["creator_wrapper"]

    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Setup: Create 2 Tokens
    # We modify params slightly for distinct tokens, though mostly relevant for logging
    params_1 = (
        ft_params  # clone not strictly necessary if we don't change mutable fields
    )
    params_2 = ft_params

    token_id_1 = await create_test_token(creator_wrapper, creator_client, params_1)
    token_id_2 = await create_test_token(creator_wrapper, creator_client, params_2)

    t1_str = str(token_id_1)
    t2_str = str(token_id_2)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Setup: Associate Both
    await executor_wrapper.associate_token(
        {"accountId": str(executor_account_id), "tokenId": str(token_id_1)}
    )
    await executor_wrapper.associate_token(
        {"accountId": str(executor_account_id), "tokenId": str(token_id_2)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify association
    assert await check_token_is_associated(
        executor_wrapper, str(executor_account_id), t1_str
    )
    assert await check_token_is_associated(
        executor_wrapper, str(executor_account_id), t2_str
    )

    # 3. Agent Execution
    input_text = f"Dissociate tokens {t1_str} and {t2_str} from my account"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 4. Verify Response
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    assert "successfully dissociated" in human_message

    # 5. Verify On-Chain
    await wait(MIRROR_NODE_WAITING_TIME)

    assert not await check_token_is_associated(
        executor_wrapper, str(executor_account_id), t1_str
    )
    assert not await check_token_is_associated(
        executor_wrapper, str(executor_account_id), t2_str
    )


@pytest.mark.asyncio
async def test_fail_dissociate_not_associated_token(setup_environment):
    executor_wrapper = setup_environment["executor_wrapper"]
    executor_account_id = setup_environment["executor_account_id"]
    creator_client = setup_environment["creator_client"]
    creator_wrapper = setup_environment["creator_wrapper"]

    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]
    ft_params: TokenParams = setup_environment["FT_PARAMS"]

    # 1. Create token BUT DO NOT ASSOCIATE
    token_id = await create_test_token(creator_wrapper, creator_client, ft_params)
    token_id_str = str(token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify NOT associated
    is_associated = await check_token_is_associated(
        executor_wrapper, str(executor_account_id), token_id_str
    )
    assert not is_associated

    # 2. Agent Execution
    input_text = f"Dissociate {token_id_str} from my account"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    # 3. Verify Failure
    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")
    raw_error = tool_call.parsedData.get("raw", {}).get("error", "")

    assert "Failed to dissociate" in human_message
    assert (
        "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in raw_error or "failed" in raw_error.lower()
    )


@pytest.mark.asyncio
async def test_fail_dissociate_non_existent_token(setup_environment):
    agent_executor = setup_environment["agent_executor"]
    response_parser = setup_environment["response_parser"]
    config = setup_environment["langchain_config"]

    fake_token_id = "0.0.999999999"

    input_text = f"Dissociate token {fake_token_id} from my account"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    human_message = tool_call.parsedData.get("humanMessage", "")

    assert "Failed to dissociate" in human_message
