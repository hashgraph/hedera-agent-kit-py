"""Integration tests for delete NFT allowance tool."""
from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    TokenId,
    TokenNftAllowance,
    SupplyType,
    TokenType,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from hedera_agent_kit.plugins.core_token_plugin import DeleteNonFungibleTokenAllowanceTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
    DeleteNonFungibleTokenAllowanceParameters,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    """
    Setup accounts and NFT token:
    1. Owner: Owns the NFT and grants allowance.
    2. Spender: Given allowance for owner's NFT.
    3. NFT Token: A non-fungible token with serials.
    """
    # 1. Create Owner Account
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(2.0)),
            key=owner_key.public_key(),
        )
    )
    owner_account_id = owner_resp.account_id
    owner_client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # 2. Create Spender Account
    spender_key = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
            key=spender_key.public_key(),
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    # 3. Create NFT Token
    token_keys = TokenKeys(
        supply_key=owner_key.public_key(),
        admin_key=owner_key.public_key(),
    )
    nft_params = TokenParams(
        token_name="DeleteAllowanceNFT",
        token_symbol="DANFT",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        supply_type=SupplyType.FINITE,
        max_supply=10,
        treasury_account_id=owner_account_id,
    )
    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=token_keys
    )
    token_resp = await owner_wrapper.create_non_fungible_token(create_params)
    nft_token_id = token_resp.token_id

    # 4. Mint NFTs (serials 1 and 2)
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=nft_token_id,
            metadata=[
                bytes("ipfs://meta-1.json", "utf-8"),
                bytes("ipfs://meta-2.json", "utf-8"),
            ],
        )
    )

    # 5. Associate spender with the NFT token
    await spender_wrapper.associate_token(
        {"accountId": str(spender_account_id), "tokenId": str(nft_token_id)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(owner_account_id))

    yield {
        "operator_client": operator_client,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "owner_account_id": owner_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "nft_token_id": nft_token_id,
        "context": context,
    }

    # Teardown
    await return_hbars_and_delete_account(
        owner_wrapper, owner_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        spender_wrapper, spender_account_id, operator_client.operator_account_id
    )

    owner_client.close()
    spender_client.close()


@pytest.mark.asyncio
async def test_deletes_nft_allowance_with_explicit_owner(setup_accounts):
    owner_client: Client = setup_accounts["owner_client"]
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    nft_token_id: TokenId = setup_accounts["nft_token_id"]
    context: Context = setup_accounts["context"]

    # 1. Approve allowance first
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(
            nft_allowances=[
                TokenNftAllowance(
                    token_id=nft_token_id,
                    spender_account_id=spender_account_id,
                    serial_numbers=[1],
                    approved_for_all=False,
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Delete allowance explicitly
    params = DeleteNonFungibleTokenAllowanceParameters(
        owner_account_id=str(owner_account_id),
        token_id=str(nft_token_id),
        serial_numbers=[1],
    )

    tool = DeleteNonFungibleTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(owner_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "NFT allowance(s) deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_deletes_nft_allowance_with_default_owner(setup_accounts):
    owner_client: Client = setup_accounts["owner_client"]
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    nft_token_id: TokenId = setup_accounts["nft_token_id"]
    context: Context = setup_accounts["context"]

    # 1. Re-approve allowance (since previous test might have deleted it)
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(
            nft_allowances=[
                TokenNftAllowance(
                    token_id=nft_token_id,
                    spender_account_id=spender_account_id,
                    serial_numbers=[2],
                    approved_for_all=False,
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Delete allowance relying on context owner ID
    params = DeleteNonFungibleTokenAllowanceParameters(
        token_id=str(nft_token_id),
        serial_numbers=[2],
    )

    tool = DeleteNonFungibleTokenAllowanceTool(context)
    result: ToolResponse = await tool.execute(owner_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "NFT allowance(s) deleted successfully" in result.human_message
    assert exec_result.raw.status == "SUCCESS"
    assert exec_result.raw.transaction_id is not None
