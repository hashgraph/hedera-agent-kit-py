"""Integration tests for mint_erc721 tool with Hedera network.

This suite deploys a simple ERC721 contract and validates minting to
Hedera account IDs and EVM addresses, including scheduled transactions
and common failure modes. It mirrors the structure of transfer_erc20 tests.
"""

from typing import cast

import pytest
from hiero_sdk_python import PrivateKey, Hbar

from hedera_agent_kit.plugins.core_evm_plugin import (
    MintERC721Tool,
    CreateERC721Tool,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import AccountResponse
from hedera_agent_kit.shared.models import ToolResponse, ExecutedTransactionToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateERC721Parameters,
    MintERC721Parameters,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils import wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_mint_erc721():
    """Setup test environment with an ERC721 token contract and accounts."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account (contract deployer and minter)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Deploy ERC721 contract using the dedicated tool
    create_tool = CreateERC721Tool(context)
    create_params = CreateERC721Parameters(
        token_name="MintableNFT", token_symbol="MNFT"
    )
    create_result: ToolResponse = await create_tool.execute(
        executor_client, context, create_params
    )
    create_exec = cast(ExecutedTransactionToolResponse, create_result)

    assert create_exec.error is None, f"ERC721 deployment failed: {create_exec.error}"
    assert (
        "erc721_address" in create_exec.extra
    ), "Missing erc721_address in result.extra"
    erc721_address = create_exec.extra["erc721_address"]

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "context": context,
        "erc721_address": erc721_address,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


async def create_recipient_account(wrapper: HederaOperationsWrapper):
    """Helper to create a recipient account."""
    resp = await wrapper.create_account(
        CreateAccountParametersNormalised(
            key=wrapper.client.operator_private_key.public_key(),
            initial_balance=Hbar(5),
        )
    )
    return resp.account_id


@pytest.mark.asyncio
async def test_mint_erc721_to_hedera_id(setup_mint_erc721):
    """Mint an ERC721 token to a Hedera account ID."""
    executor_client = setup_mint_erc721["executor_client"]
    executor_wrapper = setup_mint_erc721["executor_wrapper"]
    context = setup_mint_erc721["context"]
    erc721_address = setup_mint_erc721["erc721_address"]

    # Create recipient
    recipient_account_id = await create_recipient_account(executor_wrapper)
    await wait(MIRROR_NODE_WAITING_TIME)

    params = MintERC721Parameters(
        contract_id=erc721_address,
        to_address=str(recipient_account_id),
    )

    tool = MintERC721Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert exec_result.raw.transaction_id is not None
    assert "minted" in exec_result.human_message.lower()

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_mint_erc721_to_evm_address(setup_mint_erc721):
    """Mint an ERC721 token to an EVM address."""
    executor_client = setup_mint_erc721["executor_client"]
    executor_wrapper = setup_mint_erc721["executor_wrapper"]
    context = setup_mint_erc721["context"]
    erc721_address = setup_mint_erc721["erc721_address"]

    recipient_account_id = await create_recipient_account(executor_wrapper)
    await wait(MIRROR_NODE_WAITING_TIME)

    # Resolve EVM address from mirror node
    recipient_info: AccountResponse = (
        await executor_wrapper.get_account_info_mirrornode(str(recipient_account_id))
    )
    recipient_evm = recipient_info.get("evm_address", None)
    assert recipient_evm is not None, "Failed to get EVM address for recipient"

    params = MintERC721Parameters(
        contract_id=erc721_address,
        to_address=recipient_evm,
    )

    tool = MintERC721Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert exec_result.raw.transaction_id is not None

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_schedule_mint_erc721(setup_mint_erc721):
    """Schedule an ERC721 mint transaction."""
    executor_client = setup_mint_erc721["executor_client"]
    executor_wrapper = setup_mint_erc721["executor_wrapper"]
    context = setup_mint_erc721["context"]
    erc721_address = setup_mint_erc721["erc721_address"]

    recipient_account_id = await create_recipient_account(executor_wrapper)
    await wait(MIRROR_NODE_WAITING_TIME)

    params = MintERC721Parameters(
        contract_id=erc721_address,
        to_address=str(recipient_account_id),
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    tool = MintERC721Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert exec_result.error is None
    assert "scheduled mint" in exec_result.human_message.lower()
    assert exec_result.raw.schedule_id is not None

    # Cleanup recipient
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        executor_client.operator_account_id,
    )


@pytest.mark.asyncio
async def test_fail_when_contract_id_invalid(setup_mint_erc721):
    """Mint should fail when contract_id is invalid."""
    executor_client = setup_mint_erc721["executor_client"]
    context = setup_mint_erc721["context"]

    params = MintERC721Parameters(
        contract_id="invalid-contract-id",
        to_address=str(setup_mint_erc721["executor_account_id"]),
    )

    tool = MintERC721Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed to mint erc721" in result.human_message.lower()


@pytest.mark.asyncio
async def test_fail_when_to_address_invalid(setup_mint_erc721):
    """Mint should fail when to_address is invalid."""
    executor_client = setup_mint_erc721["executor_client"]
    context = setup_mint_erc721["context"]
    erc721_address = setup_mint_erc721["erc721_address"]

    params = MintERC721Parameters(
        contract_id=erc721_address,
        to_address="0xdeadbeef",  # invalid length/address
    )

    tool = MintERC721Tool(context)
    result: ToolResponse = await tool.execute(executor_client, context, params)

    assert result.error is not None
    assert "failed to mint erc721" in result.human_message.lower()
