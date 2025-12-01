from typing import cast

import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    AccountId,
    SupplyType,
    TokenAllowance,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_plugin.transfer_fungible_token_with_allowance import (
    TransferFungibleTokenWithAllowanceTool,
)
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    ApproveTokenAllowanceParametersNormalised,
    TransferFungibleTokenWithAllowanceParameters,
    SchedulingParams,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import TokenTransferEntry
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


async def create_test_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client: Client,
    treasury_account_id: AccountId,
    ft_params: TokenParams,
):
    # Keys can be the treasury's key (operator of the client passed in)
    treasury_public_key = executor_client.operator_private_key.public_key()

    keys: TokenKeys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )

    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


@pytest.mark.asyncio
class TestTransferFungibleTokenWithAllowanceIntegration:
    @pytest.fixture(scope="class")
    async def setup_accounts(self):
        operator_client = get_operator_client_for_tests()
        operator_wrapper = HederaOperationsWrapper(operator_client)

        # 1. Setup Executor (Token Owner / Treasury)
        executor_key = PrivateKey.generate_ed25519()
        executor_resp = await operator_wrapper.create_account(
            CreateAccountParametersNormalised(
                key=executor_key.public_key(), initial_balance=Hbar(50)
            )
        )
        executor_account_id = executor_resp.account_id
        executor_client = get_custom_client(executor_account_id, executor_key)
        executor_wrapper = HederaOperationsWrapper(executor_client)

        # 2. Setup Spender Account
        spender_key = PrivateKey.generate_ed25519()
        spender_resp = await operator_wrapper.create_account(
            CreateAccountParametersNormalised(
                key=spender_key.public_key(), initial_balance=Hbar(10)
            )
        )
        spender_account_id = spender_resp.account_id
        spender_client = get_custom_client(spender_account_id, spender_key)
        spender_wrapper = HederaOperationsWrapper(spender_client)

        # 3. Setup Receiver Account
        receiver_key = PrivateKey.generate_ed25519()
        receiver_resp = await operator_wrapper.create_account(
            CreateAccountParametersNormalised(
                key=receiver_key.public_key(), initial_balance=Hbar(10)
            )
        )
        receiver_account_id = receiver_resp.account_id
        receiver_client = get_custom_client(receiver_account_id, receiver_key)
        receiver_wrapper = HederaOperationsWrapper(receiver_client)

        context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

        await wait(MIRROR_NODE_WAITING_TIME)

        # 4. Create Fungible Token
        ft_params = TokenParams(
            token_name="IntegrationAllowanceToken",
            token_symbol="IAT",
            memo="FT for integration allowance tests",
            initial_supply=1000,
            decimals=0,
            max_supply=10000,
            supply_type=SupplyType.FINITE,
            treasury_account_id=executor_account_id,
            auto_renew_account_id=executor_account_id,
        )

        token_id = await create_test_token(
            executor_wrapper, executor_client, executor_account_id, ft_params
        )

        # 5. Associate Token to Spender and Receiver
        await spender_wrapper.associate_token(
            {"accountId": str(spender_account_id), "tokenId": str(token_id)}
        )
        await receiver_wrapper.associate_token(
            {"accountId": str(receiver_account_id), "tokenId": str(token_id)}
        )

        # 6. Approve Allowance (Executor approves Spender)
        await executor_wrapper.approve_token_allowance(
            ApproveTokenAllowanceParametersNormalised(
                token_allowances=[
                    TokenAllowance(
                        token_id=token_id,
                        owner_account_id=executor_account_id,
                        spender_account_id=spender_account_id,
                        amount=200,
                    )
                ]
            )
        )

        yield {
            "operator_client": operator_client,
            "executor_client": executor_client,
            "executor_wrapper": executor_wrapper,
            "executor_account_id": executor_account_id,
            "spender_client": spender_client,
            "spender_wrapper": spender_wrapper,
            "spender_account_id": spender_account_id,
            "receiver_client": receiver_client,
            "receiver_wrapper": receiver_wrapper,
            "receiver_account_id": receiver_account_id,
            "token_id": token_id,
            "context": context,
        }

        # Teardown
        if spender_account_id:
            await return_hbars_and_delete_account(
                spender_wrapper, spender_account_id, executor_account_id
            )
        spender_client.close()

        if receiver_account_id:
            await return_hbars_and_delete_account(
                receiver_wrapper, receiver_account_id, executor_account_id
            )
        receiver_client.close()

        if executor_account_id:
            await return_hbars_and_delete_account(
                executor_wrapper,
                executor_account_id,
                operator_client.operator_account_id,
            )
        executor_client.close()

        operator_client.close()

    async def test_transfer_to_self_with_allowance(self, setup_accounts):
        spender_client = setup_accounts["spender_client"]
        spender_wrapper = setup_accounts["spender_wrapper"]
        spender_account_id = setup_accounts["spender_account_id"]
        executor_account_id = setup_accounts["executor_account_id"]
        token_id = setup_accounts["token_id"]
        context = setup_accounts["context"]

        tool = TransferFungibleTokenWithAllowanceTool(context)

        params = TransferFungibleTokenWithAllowanceParameters(
            token_id=str(token_id),
            source_account_id=str(executor_account_id),
            transfers=[
                TokenTransferEntry(account_id=str(spender_account_id), amount=50)
            ],
        )

        result = await tool.execute(spender_client, context, params)
        exec_result = cast(ExecutedTransactionToolResponse, result)

        assert (
            "Fungible tokens successfully transferred with allowance"
            in result.human_message
        )
        assert exec_result.raw.status == "SUCCESS"

        await wait(MIRROR_NODE_WAITING_TIME)

        spender_balance = (
            await spender_wrapper.get_account_token_balance_from_mirrornode(
                str(spender_account_id), str(token_id)
            )
        )
        assert spender_balance["balance"] == 50

    async def test_transfer_to_multiple_recipients(self, setup_accounts):
        spender_client = setup_accounts["spender_client"]
        spender_wrapper = setup_accounts["spender_wrapper"]
        spender_account_id = setup_accounts["spender_account_id"]
        receiver_wrapper = setup_accounts["receiver_wrapper"]
        receiver_account_id = setup_accounts["receiver_account_id"]
        executor_account_id = setup_accounts["executor_account_id"]
        token_id = setup_accounts["token_id"]
        context = setup_accounts["context"]

        tool = TransferFungibleTokenWithAllowanceTool(context)

        params = TransferFungibleTokenWithAllowanceParameters(
            token_id=str(token_id),
            source_account_id=str(executor_account_id),
            transfers=[
                TokenTransferEntry(account_id=str(spender_account_id), amount=30),
                TokenTransferEntry(account_id=str(receiver_account_id), amount=70),
            ],
        )

        result = await tool.execute(spender_client, context, params)
        exec_result = cast(ExecutedTransactionToolResponse, result)

        assert (
            "Fungible tokens successfully transferred with allowance"
            in result.human_message
        )
        assert exec_result.raw.status == "SUCCESS"

        await wait(MIRROR_NODE_WAITING_TIME)

        spender_balance = (
            await spender_wrapper.get_account_token_balance_from_mirrornode(
                str(spender_account_id), str(token_id)
            )
        )
        receiver_balance = (
            await receiver_wrapper.get_account_token_balance_from_mirrornode(
                str(receiver_account_id), str(token_id)
            )
        )

        # 50 from the previous test + 30 = 80
        assert spender_balance["balance"] == 80
        assert receiver_balance["balance"] == 70

    async def test_schedule_transfer_with_allowance(self, setup_accounts):
        spender_client = setup_accounts["spender_client"]
        spender_account_id = setup_accounts["spender_account_id"]
        executor_account_id = setup_accounts["executor_account_id"]
        token_id = setup_accounts["token_id"]
        context = setup_accounts["context"]

        tool = TransferFungibleTokenWithAllowanceTool(context)

        params = TransferFungibleTokenWithAllowanceParameters(
            token_id=str(token_id),
            source_account_id=str(executor_account_id),
            transfers=[
                TokenTransferEntry(account_id=str(spender_account_id), amount=10),
            ],
            scheduling_params=SchedulingParams(
                is_scheduled=True, wait_for_expiry=False, admin_key=False
            ),
        )

        result = await tool.execute(spender_client, context, params)
        exec_result = cast(ExecutedTransactionToolResponse, result)

        assert "Scheduled allowance transfer created successfully" in result.human_message
        assert exec_result.raw.status == "SUCCESS"

    async def test_fail_exceed_allowance(self, setup_accounts):
        spender_client = setup_accounts["spender_client"]
        spender_account_id = setup_accounts["spender_account_id"]
        executor_account_id = setup_accounts["executor_account_id"]
        token_id = setup_accounts["token_id"]
        context = setup_accounts["context"]

        tool = TransferFungibleTokenWithAllowanceTool(context)

        params = TransferFungibleTokenWithAllowanceParameters(
            token_id=str(token_id),
            source_account_id=str(executor_account_id),
            transfers=[TokenTransferEntry(account_id=str(spender_account_id), amount=300)],
        )

        result = await tool.execute(spender_client, context, params)

        assert (
            "Failed to transfer fungible token with allowance" in result.human_message
        )
        assert "AMOUNT_EXCEEDS_ALLOWANCE" in result.human_message