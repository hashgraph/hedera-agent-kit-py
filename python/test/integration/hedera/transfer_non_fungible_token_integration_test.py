from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    SupplyType,
    TokenType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit.plugins.core_token_plugin.transfer_non_fungible_token import (
    TransferNonFungibleTokenTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import NftBalanceResponse
from hedera_agent_kit.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParametersNormalised,
    TransferNonFungibleTokenParameters,
    NftTransfer,
    MintNonFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account
from test.utils.usd_to_hbar_service import UsdToHbarService


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    """Setup accounts and NFT token for integration tests."""

    # Setup owner account (NFT treasury / sender)
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=owner_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    owner_account_id = owner_resp.account_id
    owner_client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # Setup receiver account
    receiver_key = PrivateKey.generate_ecdsa()
    receiver_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=receiver_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(0.25)),
        )
    )
    receiver_account_id = receiver_resp.account_id
    receiver_client = get_custom_client(receiver_account_id, receiver_key)
    receiver_wrapper = HederaOperationsWrapper(receiver_client)

    # Context for tool execution (an owner executes key)
    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(owner_account_id))

    # Create NFT token
    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="TestNFT",
        token_symbol="TNFT",
        memo="Transfer integration",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        supply_type=SupplyType.FINITE,
        max_supply=10,
        treasury_account_id=owner_account_id,
    )
    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=keys
    )
    token_resp = await owner_wrapper.create_non_fungible_token(create_params)
    token_id = token_resp.token_id

    # Mint a few NFTs
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=token_id,
            metadata=[
                bytes("ipfs://meta-a.json", "utf-8"),
            ],
        )
    )

    # Associate receiver with token
    await receiver_wrapper.associate_token(
        {"accountId": str(receiver_account_id), "tokenId": str(token_id)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "owner_account_id": owner_account_id,
        "receiver_client": receiver_client,
        "receiver_wrapper": receiver_wrapper,
        "receiver_account_id": receiver_account_id,
        "context": context,
        "token_id": token_id,
    }

    # Teardown
    try:
        await return_hbars_and_delete_account(
            owner_wrapper,
            receiver_account_id,
            operator_client.operator_account_id,
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup receiver account: {e}")

    receiver_client.close()

    try:
        await return_hbars_and_delete_account(
            owner_wrapper,
            owner_account_id,
            operator_client.operator_account_id,
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup owner account: {e}")

    owner_client.close()


@pytest.mark.asyncio
async def test_transfer_nft_tool(setup_accounts):
    """Test transferring NFT via tool."""
    owner_client: Client = setup_accounts["owner_client"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    receiver_wrapper: HederaOperationsWrapper = setup_accounts["receiver_wrapper"]
    receiver_account_id: AccountId = setup_accounts["receiver_account_id"]
    context: Context = setup_accounts["context"]
    token_id: AccountId = setup_accounts["token_id"]

    # Transfer NFT using the tool
    params = TransferNonFungibleTokenParameters(
        source_account_id=str(owner_account_id),
        token_id=str(token_id),
        recipients=[NftTransfer(recipient=str(receiver_account_id), serial_number=1)],
        transaction_memo="NFT transfer tool test",
    )

    tool = TransferNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(owner_client, context, params)

    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert "Non-fungible tokens successfully transferred" in result.human_message

    # Verify the NFT was transferred to the receiver
    await wait(MIRROR_NODE_WAITING_TIME)
    receiver_nfts: NftBalanceResponse = await receiver_wrapper.get_account_nfts(
        str(receiver_account_id)
    )

    # Check if the receiver now owns the NFT
    found_nft = False
    for nft in receiver_nfts.get("nfts"):
        if nft.get("token_id") == str(token_id) and nft.get("serial_number") == 1:
            found_nft = True
            break

    assert found_nft, "NFT serial 1 not found in receiver's account"
