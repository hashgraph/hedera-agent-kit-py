"""Integration tests for GetTokenBalancesTool.

This test verifies on-chain token balance querying via Hedera mirror node using
the Hedera Agent Kit. It covers successful balance retrieval, default account
fallback, and error handling.
"""

import pytest

from hiero_sdk_python import Client, PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from hedera_agent_kit.plugins.core_account_query_plugin import GetTokenBalancesTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    AccountTokenBalancesQueryParameters,
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenParametersNormalised,
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
    """Setup operator and executor clients for token balance query tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
    executor_key = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Create a fungible token
    token_resp = await operator_wrapper.create_fungible_token(
        CreateFungibleTokenParametersNormalised(
            token_params=TokenParams(
                token_name="Integration Test Token",
                token_symbol="ITT",
                decimals=2,
                initial_supply=1000,
                treasury_account_id=operator_client.operator_account_id,
            ),
            keys=TokenKeys(
                admin_key=operator_client.operator_private_key.public_key(),
                supply_key=operator_client.operator_private_key.public_key(),
            ),
        )
    )
    token_id = token_resp.token_id
    assert token_id is not None

    # Associate token with executor
    await executor_wrapper.associate_token(
        {"accountId": str(executor_account_id), "tokenId": str(token_id)}
    )

    # Transfer tokens to executor
    await operator_wrapper.transfer_fungible(
        TransferFungibleTokenParametersNormalised(
            ft_transfers={
                token_id: {
                    executor_account_id: 50,
                    operator_client.operator_account_id: -50,
                }
            },
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "operator_wrapper": operator_wrapper,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "token_id": token_id,
        "context": context,
    }

    # Cleanup: delete executor
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )

    executor_client.close()


@pytest.mark.asyncio
async def test_get_token_balances_for_account(setup_environment):
    """Test retrieving token balances for a specific account."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    executor_account_id = setup_environment["executor_account_id"]
    token_id = setup_environment["token_id"]

    params = AccountTokenBalancesQueryParameters(account_id=str(executor_account_id))
    tool = GetTokenBalancesTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Token Balances" in result.human_message
    assert str(token_id) in result.human_message
    assert "Balance: 0.5" in result.human_message  # token has 2 decimals
    assert not result.error


@pytest.mark.asyncio
async def test_get_token_balances_default_account(setup_environment):
    """Test querying token balances with no account_id provided (uses default)."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    token_id = setup_environment["token_id"]

    params = AccountTokenBalancesQueryParameters()
    tool = GetTokenBalancesTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Token Balances" in result.human_message
    assert str(token_id) in result.human_message
    assert "Balance: 0.5" in result.human_message  # token has 2 decimals
    assert not result.error


@pytest.mark.asyncio
async def test_get_token_balances_specific_token(setup_environment):
    """Test querying balance for a specific token ID."""
    executor_client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]
    executor_account_id = setup_environment["executor_account_id"]
    token_id = setup_environment["token_id"]

    params = AccountTokenBalancesQueryParameters(
        account_id=str(executor_account_id), token_id=str(token_id)
    )
    tool = GetTokenBalancesTool(context)

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert "Token Balances" in result.human_message
    assert str(token_id) in result.human_message
    assert "Balance: 0.5" in result.human_message  # token has 2 decimals
    assert not result.error
