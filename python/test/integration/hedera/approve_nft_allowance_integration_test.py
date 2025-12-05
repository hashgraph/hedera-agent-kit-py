from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    SupplyType,
    TokenId,
    TokenType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit.plugins.core_account_plugin.approve_non_fungible_token_allowance import (
    ApproveNftAllowanceTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    ApproveNftAllowanceParameters,
    CreateNonFungibleTokenParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    """Setup accounts and NFT token for integration tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Setup executor account (the NFT owner/treasury)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(35)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)

    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Set up spender account (the one receiving allowance)
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=spender_key.public_key(), initial_balance=Hbar(20)
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Create an NFT token where executor is treasury
    treasury_public_key = executor_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="AK-NFT",
        token_symbol="AKN",
        memo="Approve allowance integration",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        supply_type=SupplyType.FINITE,
        max_supply=100,
        treasury_account_id=executor_account_id,
    )
    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=keys
    )
    token_resp = await executor_wrapper.create_non_fungible_token(create_params)
    token_id = token_resp.token_id

    # Mint a few NFTs so we have serial numbers to approve
    await executor_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=token_id,
            metadata=[
                bytes("ipfs://meta-a.json", "utf-8"),
                bytes("ipfs://meta-b.json", "utf-8"),
                bytes("ipfs://meta-c.json", "utf-8"),
            ],
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # Associate spender with the NFT token
    await spender_wrapper.associate_token(
        {"accountId": str(spender_account_id), "tokenId": str(token_id)}
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "context": context,
        "token_id": token_id,
    }

    # Teardown

    await return_hbars_and_delete_account(
        spender_wrapper,
        spender_account_id,
        operator_client.operator_account_id,
    )

    spender_client.close()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )

    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_approves_nft_allowance_with_explicit_owner_and_memo_single_serial(
    setup_accounts,
):
    """Test approving NFT allowance with an explicit owner and memo for a single serial."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_account_id: AccountId = setup_accounts["executor_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]
    token_id: TokenId = setup_accounts["token_id"]

    params = ApproveNftAllowanceParameters(
        owner_account_id=str(executor_account_id),
        spender_account_id=str(spender_account_id),
        token_id=str(token_id),
        serial_numbers=[1],
        transaction_memo="Approve NFT allowance (single) integration test",
    )

    tool = ApproveNftAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "NFT allowance approved successfully" in result.human_message
    assert "Transaction ID:" in result.human_message


@pytest.mark.asyncio
async def test_approves_nft_allowance_with_default_owner_multiple_serials(
    setup_accounts,
):
    """Test approving NFT allowance using a default owner for multiple serials."""
    executor_client: Client = setup_accounts["executor_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]
    token_id: TokenId = setup_accounts["token_id"]

    params = ApproveNftAllowanceParameters(
        spender_account_id=str(spender_account_id),
        token_id=str(token_id),
        serial_numbers=[2, 3],
    )

    tool = ApproveNftAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "NFT allowance approved successfully" in result.human_message


@pytest.mark.asyncio
async def test_approves_nft_allowance_all_serials(
    setup_accounts,
):
    """Test approving NFT allowance for ALL serials via the all_serials flag."""
    executor_client: Client = setup_accounts["executor_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    context: Context = setup_accounts["context"]
    token_id: TokenId = setup_accounts["token_id"]

    # Use all_serials=True instead of specifying serial_numbers
    params = ApproveNftAllowanceParameters(
        spender_account_id=str(spender_account_id),
        token_id=str(token_id),
        all_serials=True,
        transaction_memo="Approve ALL serials allowance integration test",
    )

    tool = ApproveNftAllowanceTool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "NFT allowance approved successfully" in result.human_message
