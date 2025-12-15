import pytest
from hiero_sdk_python import PrivateKey, SupplyType, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys

from hedera_agent_kit.plugins.core_token_plugin import AirdropFungibleTokenTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    AirdropFungibleTokenParameters,
    AirdropRecipient,
    CreateFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils import wait
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_airdrop():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # ----- Executor account (airdrop sender) -----
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # ----- Deploy fungible token -----
    token_params = TokenParams(
        token_name="AirdropToken",
        token_symbol="DROP",
        decimals=2,
        initial_supply=100000,
        max_supply=500000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
        auto_renew_account_id=executor_account_id,
    )

    token_keys = TokenKeys(
        supply_key=executor_key.public_key(),
        admin_key=executor_key.public_key(),
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=token_params,
        keys=token_keys,
    )

    token_id = (await executor_wrapper.create_fungible_token(create_params)).token_id

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "context": context,
        "token_id": token_id,
    }

    # ----- Teardown -----
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


async def create_recipient_account(wrapper: HederaOperationsWrapper):
    key = PrivateKey.generate_ed25519()
    resp = await wrapper.create_account(
        CreateAccountParametersNormalised(key=key.public_key(), initial_balance=Hbar(0))
    )
    return resp.account_id


@pytest.mark.asyncio
async def test_airdrop_single_recipient(setup_airdrop):
    executor_client = setup_airdrop["executor_client"]
    executor_wrapper = setup_airdrop["executor_wrapper"]
    context = setup_airdrop["context"]
    token_id = setup_airdrop["token_id"]

    # Create recipient
    recipient_id = await create_recipient_account(executor_wrapper)

    tool = AirdropFungibleTokenTool(context)
    params = AirdropFungibleTokenParameters(
        token_id=str(token_id),
        source_account_id=context.account_id,
        recipients=[
            AirdropRecipient(account_id=str(recipient_id), amount=50),
        ],
    )

    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is None
    assert "successfully" in result.human_message.lower()

    await wait(MIRROR_NODE_WAITING_TIME)

    pending = await executor_wrapper.get_pending_airdrops(str(recipient_id))
    assert len(pending["airdrops"]) > 0
    assert pending["airdrops"][0]["token_id"] == str(token_id)


@pytest.mark.asyncio
async def test_airdrop_multiple_recipients(setup_airdrop):
    executor_client = setup_airdrop["executor_client"]
    executor_wrapper = setup_airdrop["executor_wrapper"]
    context = setup_airdrop["context"]
    token_id = setup_airdrop["token_id"]

    # Create two recipients
    r1 = await create_recipient_account(executor_wrapper)
    r2 = await create_recipient_account(executor_wrapper)

    tool = AirdropFungibleTokenTool(context)
    params = AirdropFungibleTokenParameters(
        token_id=str(token_id),
        source_account_id=context.account_id,
        recipients=[
            AirdropRecipient(account_id=str(r1), amount=10),
            AirdropRecipient(account_id=str(r2), amount=20),
        ],
    )

    result = await tool.execute(executor_client, context, params)

    assert result.error is None
    assert "successfully" in result.human_message.lower()

    await wait(MIRROR_NODE_WAITING_TIME)

    pending1 = await executor_wrapper.get_pending_airdrops(str(r1))
    pending2 = await executor_wrapper.get_pending_airdrops(str(r2))

    assert len(pending1["airdrops"]) > 0
    assert len(pending2["airdrops"]) > 0


@pytest.mark.asyncio
async def test_airdrop_nonexistent_token(setup_airdrop):
    executor_client = setup_airdrop["executor_client"]
    executor_wrapper = setup_airdrop["executor_wrapper"]
    context = setup_airdrop["context"]

    r1 = await create_recipient_account(executor_wrapper)

    tool = AirdropFungibleTokenTool(context)
    params = AirdropFungibleTokenParameters(
        token_id="0.0.999999999",  # invalid token
        source_account_id=context.account_id,
        recipients=[AirdropRecipient(account_id=str(r1), amount=5)],
    )

    result = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed" in result.human_message.lower()
