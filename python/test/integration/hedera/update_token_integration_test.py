from typing import cast

import pytest
from hiero_sdk_python import Client, PrivateKey, Hbar, TokenType, PublicKey, SupplyType
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_plugin import UpdateTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    UpdateTokenParameters,
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


## FIXME: hiero-python-sdk does not support setting of token keys with public keys yet!
@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(50, in_tinybars=False),
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
        "context": context,
    }

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


async def create_updatable_token(
    wrapper: HederaOperationsWrapper, client: Client, kyc_key: PublicKey = None
) -> str:
    """Create a token with keys so it can be updated."""
    create_params = CreateFungibleTokenParametersNormalised(
        token_params=TokenParams(
            token_name="TestToken",
            token_symbol="TTN",
            token_type=TokenType.FUNGIBLE_COMMON,
            supply_type=SupplyType.INFINITE,
            initial_supply=1000,
            decimals=0,
            treasury_account_id=client.operator_account_id,
        ),
        keys=TokenKeys(
            admin_key=client.operator_private_key.public_key(),
            supply_key=client.operator_private_key.public_key(),
            freeze_key=client.operator_private_key.public_key(),
            kyc_key=kyc_key,
        ),
    )
    resp = await wrapper.create_fungible_token(create_params)

    await wait(MIRROR_NODE_WAITING_TIME)

    return str(resp.token_id)


@pytest.mark.asyncio
async def test_update_token_name_symbol_memo(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        token_name="UpdatedTokenName",
        token_symbol="UTN",
        token_memo="Memo updated via integration test",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Token successfully updated" in result.human_message
    assert exec_result.raw.transaction_id is not None

    # Verify on-chain state
    info = executor_wrapper.get_token_info(token_id)
    assert info.name == "UpdatedTokenName"
    assert info.symbol == "UTN"
    assert info.memo == "Memo updated via integration test"


@pytest.mark.asyncio
async def test_update_kyc_key_to_operator_key(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    # Create token with a secondary key as KYC key
    secondary_key = PrivateKey.generate_ed25519().public_key()
    token_id = await create_updatable_token(
        executor_wrapper, executor_client, kyc_key=secondary_key
    )

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        kyc_key=True,  # Set to an operator key
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert "Token successfully updated" in exec_result.human_message

    # Verify on-chain state
    info = executor_wrapper.get_token_info(token_id)
    assert (
        info.kyc_key.to_string()
        == executor_client.operator_private_key.public_key().to_string()
    )


@pytest.mark.asyncio
async def test_update_supply_key_to_new_key(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    new_supply_key = PrivateKey.generate_ed25519().public_key()

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        supply_key=new_supply_key.to_string(),
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert "Token successfully updated" in exec_result.human_message

    # Verify on-chain state
    info = executor_wrapper.get_token_info(token_id)
    assert info.supply_key.to_string() == new_supply_key.to_string()


@pytest.mark.asyncio
async def test_fail_if_token_did_not_have_metadata_key(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]

    token_id = await create_updatable_token(executor_wrapper, executor_client)

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id=token_id,
        metadata_key=True,
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert (
        "Cannot update metadata_key: token was created without a metadata_key"
        in str(result.error)
    )


@pytest.mark.asyncio
async def test_fail_invalid_token_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    tool = UpdateTokenTool(context)
    params = UpdateTokenParameters(
        token_id="0.0.999999999",
        token_name="Invalid Token",
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "Failed to update token" in str(result.error)
    assert "Failed to fetch token info" in str(result.error)
