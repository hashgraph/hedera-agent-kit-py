from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    TokenId,
    TokenType,
    SupplyType,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit.plugins.core_token_plugin import MintNonFungibleTokenTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    MintNonFungibleTokenParameters,
    CreateAccountParametersNormalised,
    CreateNonFungibleTokenParametersNormalised,
    SchedulingParams,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_environment(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Setup executor account (Treasury & Supply Key holder)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Define NFT Params
    nft_params = TokenParams(
        token_name="MintableNFT",
        token_symbol="MNFT",
        memo="NFT",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        supply_type=SupplyType.FINITE,
        max_supply=100,
        treasury_account_id=executor_account_id,
    )

    # Create Token
    keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )
    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=keys
    )

    token_resp = await executor_wrapper.create_non_fungible_token(create_params)
    token_id = token_resp.token_id

    # Wait for Mirror Node to ingest token creation
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


@pytest.mark.asyncio
async def test_mint_single_nft(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    # Check supply before
    token_info_before = executor_wrapper.get_token_info(str(token_id))
    supply_before = token_info_before.total_supply

    # Execute Tool
    tool = MintNonFungibleTokenTool(context)
    params = MintNonFungibleTokenParameters(
        token_id=str(token_id), uris=["ipfs://metadata1.json"]
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    # Wait for update
    await wait(MIRROR_NODE_WAITING_TIME)

    # Check supply after
    token_info_after = executor_wrapper.get_token_info(str(token_id))
    supply_after = token_info_after.total_supply

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "Token successfully minted" in result.human_message
    assert supply_after == supply_before + 1


@pytest.mark.asyncio
async def test_mint_multiple_nfts(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    # Check supply before
    token_info_before = executor_wrapper.get_token_info(str(token_id))
    supply_before = token_info_before.total_supply

    uris = ["ipfs://meta1.json", "ipfs://meta2.json", "ipfs://meta3.json"]

    # Execute Tool
    tool = MintNonFungibleTokenTool(context)
    params = MintNonFungibleTokenParameters(token_id=str(token_id), uris=uris)

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    # Wait for update
    await wait(MIRROR_NODE_WAITING_TIME)

    # Check supply after
    token_info_after = executor_wrapper.get_token_info(str(token_id))
    supply_after = token_info_after.total_supply

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "Token successfully minted" in result.human_message
    assert supply_after == supply_before + len(uris)


@pytest.mark.asyncio
async def test_schedule_minting_nft(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    token_id: TokenId = setup_environment["token_id"]

    tool = MintNonFungibleTokenTool(context)
    params = MintNonFungibleTokenParameters(
        token_id=str(token_id),
        uris=["ipfs://scheduled.json"],
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
async def test_fail_non_existent_token(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    tool = MintNonFungibleTokenTool(context)
    params = MintNonFungibleTokenParameters(
        token_id="0.0.999999999", uris=["ipfs://meta.json"]
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to mint non-fungible token" in result.human_message
    assert "INVALID_TOKEN_ID" in result.human_message
