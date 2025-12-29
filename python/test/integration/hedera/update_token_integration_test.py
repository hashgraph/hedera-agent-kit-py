"""Integration tests for update token tool.

This module tests the UpdateTokenTool directly with real Hedera transactions.
"""

from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    SupplyType,
    TokenType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_token_plugin import UpdateTokenTool
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
    UpdateTokenParameters,
    CreateFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(8)),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_key": executor_key_pair,
        "context": context,
    }

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()


async def create_updatable_token(
    wrapper: HederaOperationsWrapper, client: Client
) -> str:
    """Create a fungible token with an admin key so it can be updated."""
    admin_key = client.operator_private_key.public_key()

    token_params = TokenParams(
        token_name="UpdatableToken",
        token_symbol="UPD",
        decimals=0,
        initial_supply=100,
        treasury_account_id=client.operator_account_id,
        supply_type=SupplyType.FINITE,
        max_supply=1000,
        token_type=TokenType.FUNGIBLE_COMMON,
        auto_renew_account_id=client.operator_account_id,
        memo="Original Memo",
    )

    token_keys = TokenKeys(admin_key=admin_key, supply_key=admin_key)

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=token_keys,
    )

    resp = await wrapper.create_fungible_token(create_params)
    await wait(MIRROR_NODE_WAITING_TIME)

    return str(resp.token_id)


@pytest.mark.asyncio
async def test_update_token_name(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        token_name="NewTokenName",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Token successfully updated" in result.human_message
    assert exec_result.raw.status == "SUCCESS"

    # Verify on-chain state
    token_info = executor_wrapper.get_token_info(token_id)
    assert token_info.name == "NewTokenName"


@pytest.mark.asyncio
async def test_update_token_symbol(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        token_symbol="NEWSYM",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"

    # Verify on-chain state
    token_info = executor_wrapper.get_token_info(token_id)
    assert token_info.symbol == "NEWSYM"


@pytest.mark.asyncio
async def test_update_token_memo(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        token_memo="Updated Token Memo",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"

    # Verify on-chain state
    token_info = executor_wrapper.get_token_info(token_id)
    assert token_info.memo == "Updated Token Memo"

# FIXME: This test fails because the token's keys in update transaction are only accepted only as Private keys
@pytest.mark.asyncio
async def test_update_supply_key(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    # Generate a new key for the supply key
    new_supply_key = PrivateKey.generate_ecdsa().public_key()

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        supply_key=new_supply_key.to_string(),
    )

    print(token_id)

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert exec_result.raw.status == "SUCCESS"

    # Wait for mirror node to sync
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify on-chain state
    token_info = executor_wrapper.get_token_info(token_id)
    assert token_info.supply_key.to_string() == new_supply_key.to_string()


@pytest.mark.asyncio
async def test_fail_update_immutable_token(setup_accounts):
    """Test updating a token that has no admin key (immutable)."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    # Create immutable token (no admin key)
    token_params = TokenParams(
        token_name="ImmutableToken",
        token_symbol="IMM",
        decimals=0,
        initial_supply=100,
        treasury_account_id=executor_client.operator_account_id,
        supply_type=SupplyType.FINITE,
        max_supply=1000,
        token_type=TokenType.FUNGIBLE_COMMON,
        auto_renew_account_id=executor_client.operator_account_id,
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=None,  # No admin key - immutable
    )

    resp = await executor_wrapper.create_fungible_token(create_params)
    token_id = str(resp.token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        token_name="Should Fail",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    # The tool's pre-check should detect no admin key
    assert (
        "transaction failed with status: token_is_immutable" in result.human_message.lower()
    )


@pytest.mark.asyncio
async def test_fail_invalid_token_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id="0.0.999999999",
        token_name="Fail",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    # The tool returns HTTP 404 error for non-existent tokens
    assert "Not found" in result.human_message or "404" in result.human_message


@pytest.mark.asyncio
async def test_fail_update_key_that_doesnt_exist(setup_accounts):
    """Test failure when trying to update a key that wasn't set on creation."""
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    # Create token with only admin key (no freeze key)
    admin_key = executor_client.operator_private_key.public_key()

    token_params = TokenParams(
        token_name="NoFreezeKeyToken",
        token_symbol="NFK",
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
    token_id = str(resp.token_id)

    await wait(MIRROR_NODE_WAITING_TIME)

    # Try to update freeze_key which wasn't set
    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        freeze_key=True,  # Try to add freeze key
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Cannot update freeze_key" in result.human_message
