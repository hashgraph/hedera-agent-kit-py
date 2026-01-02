"""Integration tests for GetPendingAirdropQueryTool.

This test verifies pending airdrop querying via Hedera mirror node using
the Hedera Agent Kit. It covers successful airdrop retrieval and error handling.
"""

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar, SupplyType

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from hiero_sdk_python.tokens.token_transfer import TokenTransfer

from hedera_agent_kit.plugins.core_token_query_plugin.get_pending_airdrop_query import (
    GetPendingAirdropQueryTool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    AirdropFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    PendingAirdropQueryParameters,
)
from test import HederaOperationsWrapper
from test.utils import wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_environment(operator_client, operator_wrapper):
    """Setup operator and executor clients for pending airdrop query tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
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

    # Create FT
    ft_params = TokenParams(
        token_name="AirdropQueryToken",
        token_symbol="ADQ",
        initial_supply=100000,
        decimals=2,
        max_supply=500000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
        auto_renew_account_id=executor_account_id,
    )
    ft_keys = TokenKeys(
        supply_key=executor_client.operator_private_key.public_key(),
        admin_key=executor_client.operator_private_key.public_key(),
    )

    params_obj = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=ft_keys
    )
    token_resp = await executor_wrapper.create_fungible_token(params_obj)
    token_id_ft = token_resp.token_id

    # Create a recipient with 0 auto-associations
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(0),
            max_automatic_token_associations=0,
        )
    )
    recipient_id = recipient_resp.account_id

    airdrop_params = AirdropFungibleTokenParametersNormalised(
        token_transfers=[
            TokenTransfer(token_id=token_id_ft, account_id=recipient_id, amount=100),
            TokenTransfer(
                token_id=token_id_ft, account_id=executor_account_id, amount=-100
            ),
        ]
    )

    # Airdrop tokens
    await executor_wrapper.airdrop_token(airdrop_params)

    await wait(MIRROR_NODE_WAITING_TIME)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_id": recipient_id,
        "token_id_ft": token_id_ft,
        "context": context,
    }

    # Cleanup
    await return_hbars_and_delete_account(
        account_wrapper=executor_wrapper,
        account_to_delete=recipient_id,
        account_to_return=operator_client.operator_account_id,
    )
    await return_hbars_and_delete_account(
        account_wrapper=executor_wrapper,
        account_to_delete=executor_account_id,
        account_to_return=operator_client.operator_account_id,
    )

    executor_client.close()


@pytest.mark.asyncio
async def test_get_pending_airdrop_for_recipient(setup_environment):
    """Test retrieving pending airdrops for a specific account."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    recipient_id = setup_environment["recipient_id"]

    params = PendingAirdropQueryParameters(account_id=str(recipient_id))
    tool = GetPendingAirdropQueryTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert f"pending airdrops for account **{recipient_id}**" in result.human_message
    assert len(result.extra["pending_airdrops"]["airdrops"]) > 0
    assert not result.error


@pytest.mark.asyncio
async def test_get_pending_airdrop_non_existent_account(setup_environment):
    """Test querying a non-existent account."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    non_existent_account_id = "0.0.999999999"
    params = PendingAirdropQueryParameters(account_id=non_existent_account_id)
    tool = GetPendingAirdropQueryTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "No pending airdrops found for account" in result.human_message
