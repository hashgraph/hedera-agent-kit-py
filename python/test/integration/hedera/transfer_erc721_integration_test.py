"""Integration tests for transfer_erc721 tool with Hedera network."""

import pytest
from typing import cast
from hiero_sdk_python import PrivateKey, Hbar

from hedera_agent_kit.plugins.core_evm_plugin import TransferERC721Tool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferERC721Parameters,
    CreateERC721Parameters,
    MintERC721Parameters,
    SchedulingParams,
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
async def setup_transfer_erc721():
    """Setup test environment with ERC721 token and accounts."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account (token creator and sender)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Create a recipient account
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(5)
        )
    )
    recipient_account_id = recipient_resp.account_id

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Create test ERC721 token
    create_params = CreateERC721Parameters(
        token_name="TestNFT",
        token_symbol="TNFT",
        base_uri="https://example.com/metadata/",
    )

    create_result = await executor_wrapper.create_erc721(create_params)

    if not create_result.get("erc721_address"):
        raise Exception("Failed to create test ERC721 token")

    test_token_address = create_result["erc721_address"]

    print(f"Test ERC721 token address: {test_token_address}")

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_account_id": recipient_account_id,
        "context": context,
        "test_token_address": test_token_address,
        "next_token_id": 0,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        recipient_account_id,
        operator_client.operator_account_id,
    )
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


async def mint_token_for_transfer(setup_env):
    """Helper to mint a new NFT for transfer tests."""
    wrapper = setup_env["executor_wrapper"]
    token_address = setup_env["test_token_address"]
    executor_account_id = setup_env["executor_account_id"]
    token_id = setup_env["next_token_id"]

    mint_params = MintERC721Parameters(
        contract_id=token_address,
        to_address=str(executor_account_id),
    )

    await wrapper.mint_erc721(mint_params)
    await wait(MIRROR_NODE_WAITING_TIME)

    setup_env["next_token_id"] += 1
    return token_id


@pytest.mark.asyncio
async def test_transfer_token_to_another_account_using_hedera_addresses(
    setup_transfer_erc721,
):
    """Test transferring ERC721 token using Hedera account IDs."""
    env = setup_transfer_erc721
    token_id = await mint_token_for_transfer(env)

    params = TransferERC721Parameters(
        contract_id=env["test_token_address"],
        from_address=str(env["executor_account_id"]),
        to_address=str(env["recipient_account_id"]),
        token_id=token_id,
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    exec_result = cast(ExecutedTransactionToolResponse, result)
    assert exec_result.raw.transaction_id is not None
    assert "ERC721 token transferred successfully" in result.human_message


@pytest.mark.asyncio
async def test_transfer_token_using_evm_addresses(setup_transfer_erc721):
    """Test transferring ERC721 token using EVM addresses."""
    env = setup_transfer_erc721
    token_id = await mint_token_for_transfer(env)

    # Get EVM address for recipient
    recipient_info = await env["executor_wrapper"].get_account_info_mirrornode(
        str(env["recipient_account_id"])
    )
    recipient_evm_address = recipient_info.get("evm_address")

    params = TransferERC721Parameters(
        contract_id=env["test_token_address"],
        from_address=str(env["executor_account_id"]),
        to_address=recipient_evm_address or str(env["recipient_account_id"]),
        token_id=token_id,
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    exec_result = cast(ExecutedTransactionToolResponse, result)
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_handle_transfer_without_explicit_from_address(setup_transfer_erc721):
    """Test transferring ERC721 token without explicit fromAddress (defaults to operator)."""
    env = setup_transfer_erc721
    token_id = await mint_token_for_transfer(env)

    params = TransferERC721Parameters(
        contract_id=env["test_token_address"],
        to_address=str(env["recipient_account_id"]),
        token_id=token_id,
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    exec_result = cast(ExecutedTransactionToolResponse, result)
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_schedule_transfer_of_erc721_token(setup_transfer_erc721):
    """Test scheduling a transfer of ERC721 token."""
    env = setup_transfer_erc721
    token_id = await mint_token_for_transfer(env)

    params = TransferERC721Parameters(
        contract_id=env["test_token_address"],
        from_address=str(env["executor_account_id"]),
        to_address=str(env["recipient_account_id"]),
        token_id=token_id,
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    exec_result = cast(ExecutedTransactionToolResponse, result)
    assert "Scheduled transfer of ERC721 successfully" in result.human_message
    assert exec_result.raw.schedule_id is not None
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_fail_with_invalid_contract_id(setup_transfer_erc721):
    """Test that transfer fails with invalid contract ID."""
    env = setup_transfer_erc721

    params = TransferERC721Parameters(
        contract_id="invalid-id",
        to_address=str(env["recipient_account_id"]),
        token_id=1,
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    assert "Failed to transfer ERC721" in result.human_message


@pytest.mark.asyncio
async def test_fail_when_transferring_non_existent_token(setup_transfer_erc721):
    """Test that transfer fails when transferring non-existent token."""
    env = setup_transfer_erc721

    params = TransferERC721Parameters(
        contract_id=env["test_token_address"],
        from_address=str(env["executor_account_id"]),
        to_address=str(env["recipient_account_id"]),
        token_id=999999,
    )

    tool = TransferERC721Tool(env["context"])
    result: ToolResponse = await tool.execute(
        env["executor_client"], env["context"], params
    )

    assert "Failed to transfer ERC721" in result.human_message
