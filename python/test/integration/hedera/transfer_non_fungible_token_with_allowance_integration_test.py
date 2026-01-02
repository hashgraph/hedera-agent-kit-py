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
    TokenNftAllowance,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit.plugins.core_token_plugin.transfer_non_fungible_token_with_allowance import (
    TransferNftWithAllowanceTool,
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
    TransferNonFungibleTokenWithAllowanceParameters,
    NftApprovedTransfer,
    MintNonFungibleTokenParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    """Setup accounts and NFT token for integration tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Setup owner account (NFT treasury)
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=owner_key.public_key(),
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])
            ),
        )
    )
    owner_account_id = owner_resp.account_id
    owner_client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # Setup spender account (the one using the allowance)
    spender_key = PrivateKey.generate_ecdsa()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=spender_key.public_key(),
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])
            ),
        )
    )
    spender_account_id = spender_resp.account_id
    spender_client = get_custom_client(spender_account_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    # Context for tool execution (spender executes)
    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(spender_account_id))

    # Create NFT token
    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="TestNFT",
        token_symbol="TNFT",
        memo="Transfer allowance integration",
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

    # Mint a few NFTs so we have serial numbers to approve
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=token_id,
            metadata=[
                bytes("ipfs://meta-a.json", "utf-8"),
                bytes("ipfs://meta-b.json", "utf-8"),
                bytes("ipfs://meta-c.json", "utf-8"),
            ],
        )
    )

    # Associate spender with token
    await spender_wrapper.associate_token(
        {"accountId": str(spender_account_id), "tokenId": str(token_id)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "owner_account_id": owner_account_id,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "spender_account_id": spender_account_id,
        "context": context,
        "token_id": token_id,
    }

    # Teardown
    try:
        await return_hbars_and_delete_account(
            owner_wrapper,
            spender_account_id,
            operator_client.operator_account_id,
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup spender account: {e}")

    spender_client.close()

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
async def test_transfer_nft_via_approved_allowance(setup_accounts):
    """Test transferring NFT via approved allowance."""
    owner_client: Client = setup_accounts["owner_client"]
    owner_wrapper: HederaOperationsWrapper = setup_accounts["owner_wrapper"]
    owner_account_id: AccountId = setup_accounts["owner_account_id"]
    spender_client: Client = setup_accounts["spender_client"]
    spender_account_id: AccountId = setup_accounts["spender_account_id"]
    spender_wrapper: HederaOperationsWrapper = setup_accounts["spender_wrapper"]
    context: Context = setup_accounts["context"]
    token_id: TokenId = setup_accounts["token_id"]

    # Approve NFT allowance using SDK
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(
            nft_allowances=[
                TokenNftAllowance(
                    token_id=token_id,
                    spender_account_id=spender_account_id,
                    serial_numbers=[1],
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # Transfer NFT using allowance via the tool
    params = TransferNonFungibleTokenWithAllowanceParameters(
        source_account_id=str(owner_account_id),
        token_id=str(token_id),
        recipients=[
            NftApprovedTransfer(recipient=str(spender_account_id), serial_number=1)
        ],
        transaction_memo="NFT allowance transfer",
    )

    tool = TransferNftWithAllowanceTool(context)
    result: ToolResponse = await tool.execute(spender_client, context, params)

    # Safety assertion to debug failures before casting
    assert result.error is None, f"Tool execution failed: {result.error}"

    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result is not None
    assert exec_result.raw.status == "SUCCESS"
    assert (
        "Non-fungible tokens successfully transferred with allowance"
        in result.human_message
    )
    assert "Transaction ID:" in result.human_message

    # Verify the NFT was transferred to the spender
    await wait(MIRROR_NODE_WAITING_TIME)
    spender_nfts: NftBalanceResponse = await spender_wrapper.get_account_nfts(
        str(spender_account_id)
    )

    # Check if the spender now owns the NFT
    found_nft = False
    for nft in spender_nfts.get("nfts"):
        if nft.get("token_id") == str(token_id) and nft.get("serial_number") == 1:
            found_nft = True
            break

    assert found_nft, "NFT serial 1 not found in spender's account"
