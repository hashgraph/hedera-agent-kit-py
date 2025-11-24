from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    TokenId,
    SupplyType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_plugin import MintFungibleTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    MintFungibleTokenParameters,
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    SchedulingParams,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_environment():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Setup executor account (Treasury & Supply Key holder)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(15)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Define Token Params
    # Decimals=2 means 1 unit = 100 tiny units
    ft_params = TokenParams(
        token_name="MintableToken",
        token_symbol="MINT",
        memo="FT",
        initial_supply=100,  # 100 tiny units (1.00 display)
        decimals=2,
        max_supply=1000,  # 1000 tiny units (10.00 display)
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
    )

    # Create Token
    keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )

    token_resp = await executor_wrapper.create_fungible_token(create_params)
    token_id = token_resp.token_id

    # Wait for Mirror Node to ingest token creation so Mint tool can fetch decimals
    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "context": context,
        "token_id": token_id,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_mint_additional_supply(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    # Check supply before
    token_info_before = executor_wrapper.get_token_info(str(token_id))
    supply_before = token_info_before.total_supply

    # Execute Tool
    # Amount 5 with decimals 2 -> 500 tiny units
    tool = MintFungibleTokenTool(context)
    params = MintFungibleTokenParameters(token_id=str(token_id), amount=5)

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    # Wait for update
    await wait(MIRROR_NODE_WAITING_TIME)

    # Check supply after
    token_info_after = executor_wrapper.get_token_info(str(token_id))
    supply_after = token_info_after.total_supply

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "Tokens successfully minted" in result.human_message
    # Expected increase: 5 * 10^2 = 500
    assert supply_after == supply_before + 500


@pytest.mark.asyncio
async def test_schedule_minting_additional_supply(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    tool = MintFungibleTokenTool(context)
    params = MintFungibleTokenParameters(
        token_id=str(token_id),
        amount=5,
        scheduling_params=SchedulingParams(
            is_scheduled=True, wait_for_expiry=False, admin_key=True
        ),
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "Scheduled mint transaction created successfully" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.schedule_id is not None


@pytest.mark.asyncio
async def test_fail_minting_more_than_max_supply(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    # Max supply is 1000 tiny units (10.00).
    # Try to mint 5000.00 (500,000 tiny units), which exceeds limit significantly.
    tool = MintFungibleTokenTool(context)
    params = MintFungibleTokenParameters(token_id=str(token_id), amount=5000)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert (
        "TOKEN_MAX_SUPPLY_REACHED" in result.error
        or "TOKEN_MAX_SUPPLY_REACHED" in result.human_message
    )


@pytest.mark.asyncio
async def test_fail_non_existent_token(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    tool = MintFungibleTokenTool(context)
    params = MintFungibleTokenParameters(token_id="0.0.999999999", amount=10)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to mint fungible token" in result.human_message
    assert "Failed to fetch token info 0.0.999999999: HTTP 404" in result.human_message
