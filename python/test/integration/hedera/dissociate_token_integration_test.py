from typing import cast, List

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    TokenId,
    SupplyType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_plugin import DissociateTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    DissociateTokenParameters,
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
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

    # 1. Create Executor Account (The one associating/dissociating)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # 2. Create Token Creator Account (Treasury)
    token_creator_key = PrivateKey.generate_ed25519()
    token_creator_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=token_creator_key.public_key(), initial_balance=Hbar(50)
        )
    )
    token_creator_account_id = token_creator_resp.account_id
    token_creator_client = get_custom_client(
        token_creator_account_id, token_creator_key
    )
    token_creator_wrapper = HederaOperationsWrapper(token_creator_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # 3. Deploy Tokens
    # Common keys
    creator_public_key = token_creator_client.operator_private_key.public_key()
    token_keys = TokenKeys(
        supply_key=creator_public_key,
        admin_key=creator_public_key,
    )

    # FT Params
    ft_params = TokenParams(
        token_name="DissociateTokenFT",
        token_symbol="DISS",
        memo="FT-DISSOCIATE",
        initial_supply=1000,
        decimals=2,
        max_supply=5000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=token_creator_account_id,
    )

    # Create FT
    ft_resp = await token_creator_wrapper.create_fungible_token(
        CreateFungibleTokenParametersNormalised(token_params=ft_params, keys=token_keys)
    )
    token_id_ft = ft_resp.token_id

    # NFT Params (reusing Fungible creation logic as per TS test logic, but keeping 0 initial supply)
    nft_params = TokenParams(
        token_name="GoldNFT",
        token_symbol="GLD",
        memo="NFT-DISSOCIATE",
        initial_supply=1,
        decimals=2,
        max_supply=5000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=token_creator_account_id,
    )

    # Create "NFT" (represented here as another FT for dissociation logic consistency)
    nft_resp = await token_creator_wrapper.create_fungible_token(
        CreateFungibleTokenParametersNormalised(
            token_params=nft_params, keys=token_keys
        )
    )
    token_id_nft = nft_resp.token_id

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "token_creator_client": token_creator_client,
        "token_creator_wrapper": token_creator_wrapper,
        "token_creator_account_id": token_creator_account_id,
        "context": context,
        "token_id_ft": token_id_ft,
        "token_id_nft": token_id_nft,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()

    await return_hbars_and_delete_account(
        token_creator_wrapper,
        token_creator_account_id,
        operator_client.operator_account_id,
    )
    token_creator_client.close()

    operator_client.close()


async def associate_tokens(
    executor_wrapper: HederaOperationsWrapper,
    account_id: str,
    token_ids: List[TokenId],
):
    """Helper to associate tokens before testing dissociation."""
    for token_id in token_ids:
        await executor_wrapper.associate_token(
            {"accountId": account_id, "tokenId": str(token_id)}
        )


@pytest.mark.asyncio
async def test_dissociate_single_token_successfully(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    executor_account_id = str(setup_environment["executor_account_id"])
    context: Context = setup_environment["context"]
    token_id_ft: TokenId = setup_environment["token_id_ft"]

    # Setup: Associate first
    await associate_tokens(executor_wrapper, executor_account_id, [token_id_ft])

    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id_ft)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "successfully dissociated" in result.human_message

    # Verify balance is gone (or association removed)
    balances = executor_wrapper.get_account_balances(executor_account_id)
    # SDK usually returns None or omits the key if not associated/zero balance depending on query
    is_associated = balances.token_balances.get(token_id_ft) is not None
    assert is_associated is False


@pytest.mark.asyncio
async def test_dissociate_multiple_tokens_at_once(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    executor_account_id = str(setup_environment["executor_account_id"])
    context: Context = setup_environment["context"]
    token_id_ft: TokenId = setup_environment["token_id_ft"]
    token_id_nft: TokenId = setup_environment["token_id_nft"]

    # Setup: Associate both
    await associate_tokens(
        executor_wrapper, executor_account_id, [token_id_ft, token_id_nft]
    )

    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id_ft), str(token_id_nft)])

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"
    assert "successfully dissociated" in result.human_message

    # Verify both removed
    balances = executor_wrapper.get_account_balances(executor_account_id)
    assert balances.token_balances.get(token_id_ft) is None
    assert balances.token_balances.get(token_id_nft) is None


@pytest.mark.asyncio
async def test_fail_dissociating_token_not_associated(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    token_id_ft: TokenId = setup_environment["token_id_ft"]

    # Note: We do NOT associate here.

    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=[str(token_id_ft)])

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to dissociate token" in result.human_message
    assert (
        "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in result.error
        or "INVALID_TRANSACTION" in result.error
    )


@pytest.mark.asyncio
async def test_fail_dissociating_non_existent_token(setup_environment):
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    tool = DissociateTokenTool(context)
    params = DissociateTokenParameters(token_ids=["0.0.9999999"])

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to dissociate token" in result.human_message
    assert "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in (result.error or "")
