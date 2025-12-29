"""End-to-end tests for update token tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
    TokenId,
    SupplyType,
    TokenType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from test.utils.usd_to_hbar_service import UsdToHbarService
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
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(10)),
            key=executor_key.public_key(),
        )
    )
    executor_account_id: AccountId = executor_resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=executor_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture(scope="module")
def executor_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["executor_account_id"],
        res["executor_key"],
        res["executor_client"],
        res["executor_wrapper"],
    )


@pytest.fixture(scope="module")
def executor_wrapper(setup_module_resources):
    return setup_module_resources["executor_wrapper"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]

@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "update_topic_e2e"})


@pytest.fixture
async def test_token(
    executor_wrapper, executor_account
) -> AsyncGenerator[TokenId, None]:
    """Creates a fungible token with admin and supply keys set to the executor's key.

    This corresponds to the `beforeEach` setup in the TS tests.
    """
    _, _, executor_client, _ = executor_account
    admin_key = executor_client.operator_private_key.public_key()

    token_params = TokenParams(
        token_name="E2EUpdatableToken",
        token_symbol="E2EUPD",
        decimals=0,
        initial_supply=100,
        treasury_account_id=executor_client.operator_account_id,
        supply_type=SupplyType.FINITE,
        max_supply=1000,
        token_type=TokenType.FUNGIBLE_COMMON,
        auto_renew_account_id=executor_client.operator_account_id,
        memo="initial-token-memo",
    )

    token_keys = TokenKeys(admin_key=admin_key, supply_key=admin_key)

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=token_keys,
    )

    resp = await executor_wrapper.create_fungible_token(create_params)

    assert resp.token_id is not None
    print(f"Created token {resp.token_id}")
    await wait(MIRROR_NODE_WAITING_TIME)

    yield resp.token_id


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
        raise ValueError("No tool calls found in agent result.")
    return tool_calls[0]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_update_token_name_e2e(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test updating token name via natural language."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    input_text = f'Update token {token_id_str} name to "AgentUpdatedName"'

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "AgentUpdatedName"


@pytest.mark.asyncio
async def test_update_token_symbol_e2e(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test updating token symbol via natural language."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    input_text = f'Update token {token_id_str} symbol to "AGSYM"'

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.symbol == "AGSYM"


@pytest.mark.asyncio
async def test_update_token_memo_e2e(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test updating token memo via natural language."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    input_text = f"For token {token_id_str}, set the memo to 'E2E updated memo'"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.memo == "E2E updated memo"

# FIXME: This test fails because the token's keys in update transaction are only accepted only as Private keys
@pytest.mark.asyncio
async def test_update_token_supply_key_with_my_key(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test changing token supply key using 'my key' (default/operator key)."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    input_text = f"For token {token_id_str}, change the supply key to my key"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain - supply key should be the executor's key
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert str(token_info.supply_key.to_string()) == str(
        executor_client.operator_private_key.public_key().to_string()
    )

# FIXME: This test fails because the token's keys in update transaction are only accepted only as Private keys
@pytest.mark.asyncio
async def test_update_token_supply_key_with_explicit_key(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test changing token supply key using explicitly provided key."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    # Generate a new key
    new_supply_key = PrivateKey.generate_ed25519().public_key()
    new_supply_key_str = new_supply_key.to_string()

    input_text = (
        f"For token {token_id_str}, change the supply key to: {new_supply_key_str}"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.supply_key.to_string() == new_supply_key.to_string()


@pytest.mark.asyncio
async def test_fail_update_key_that_doesnt_exist(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test failure when updating a key that was not set during token creation."""
    _, _, executor_client, _ = executor_account
    admin_key = executor_client.operator_private_key.public_key()

    # Create a token without a freeze key
    token_params = TokenParams(
        token_name="NoFreezeE2E",
        token_symbol="NFRE2E",
        decimals=0,
        initial_supply=100,
        treasury_account_id=executor_client.operator_account_id,
        supply_type=SupplyType.FINITE,
        max_supply=1000,
        token_type=TokenType.FUNGIBLE_COMMON,
        auto_renew_account_id=executor_client.operator_account_id,
    )

    token_keys = TokenKeys(admin_key=admin_key)  # Only admin key, no freeze key

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=token_keys,
    )

    resp = await executor_wrapper.create_fungible_token(create_params)
    token_without_freeze_id = str(resp.token_id)
    await wait(MIRROR_NODE_WAITING_TIME)

    # Attempt to add a freeze key
    input_text = f"For token {token_without_freeze_id}, change the freeze key to my key"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # Verification
    human_message = tool_call.parsedData["humanMessage"]
    raw_error = tool_call.parsedData["raw"].get("error", "")

    expected_error_substr = (
        "Cannot update freeze_key: token was created without a freeze_key"
    )

    assert expected_error_substr in human_message or expected_error_substr in raw_error
    assert "Failed to update token" in human_message


@pytest.mark.asyncio
async def test_reject_unauthorized_update(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    operator_wrapper: HederaOperationsWrapper,
    operator_client,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test that updates are rejected if the agent does not hold the admin key."""

    # 1. Create a secondary "outsider" account
    outsider_key = PrivateKey.generate_ed25519()
    outsider_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5), key=outsider_key.public_key()
        )
    )
    outsider_id = outsider_resp.account_id
    outsider_client = get_custom_client(outsider_id, outsider_key)
    outsider_wrapper = HederaOperationsWrapper(outsider_client)

    # 2. Outsider creates a token (Admin Key = Outsider Key)
    token_params = TokenParams(
        token_name="OutsiderToken",
        token_symbol="OUTR",
        decimals=0,
        initial_supply=100,
        treasury_account_id=outsider_id,
        supply_type=SupplyType.FINITE,
        max_supply=1000,
        token_type=TokenType.FUNGIBLE_COMMON,
        auto_renew_account_id=outsider_id,
    )

    token_keys = TokenKeys(admin_key=outsider_key.public_key())

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=token_keys,
    )

    resp = await outsider_wrapper.create_fungible_token(create_params)
    outsider_token_id = str(resp.token_id)
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Agent (Executor) tries to update the outsider's token
    # Agent signs with Executor Key, but Token requires Outsider Key
    input_text = f'For token {outsider_token_id}, change the name to "Hacked"'

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 4. Verification
    human_message = tool_call.parsedData["humanMessage"]
    raw_error = tool_call.parsedData["raw"].get("error", "")

    # The tool logic explicitly checks permissions in check_validity_of_updates
    expected_msg = "You do not have permission to update this token"

    assert expected_msg in human_message or expected_msg in raw_error

    # Cleanup outsider
    await return_hbars_and_delete_account(
        outsider_wrapper, outsider_id, operator_client.operator_account_id
    )


@pytest.mark.asyncio
async def test_update_multiple_fields_at_once(
    agent_executor,
    executor_wrapper: HederaOperationsWrapper,
    executor_account,
    test_token: TokenId,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test updating multiple token fields in a single request."""
    _, _, executor_client, _ = executor_account
    token_id_str = str(test_token)

    input_text = f'Update token {token_id_str} name to "MultiUpdated" and symbol to "MULT" and memo to "Combined update"'

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert "successfully updated" in tool_call.parsedData["humanMessage"]

    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain
    token_info = executor_wrapper.get_token_info(token_id_str)
    assert token_info.name == "MultiUpdated"
    assert token_info.symbol == "MULT"
    assert token_info.memo == "Combined update"
