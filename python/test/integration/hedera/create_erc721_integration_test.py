"""Hedera integration tests for create ERC721 tool.

This module tests the ERC721 creation tool by calling it directly with parameters,
omitting the LLM and focusing on testing logic and on-chain execution.
"""

import time
from typing import cast

import pytest
from hiero_sdk_python import PrivateKey, Hbar, Client

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_evm_plugin import CreateERC721Tool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateERC721Parameters,
    DeleteAccountParametersNormalised,
    CreateAccountParametersNormalised,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_custom_client


@pytest.fixture(scope="module")
async def setup_environment(operator_client, operator_wrapper):
    """Set up Hedera operator client and context for tests."""
    # operator_client and operator_wrapper are provided by conftest.py (session scope)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    yield {
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "context": context,
    }

    # Teardown: Delete an executor account
    await executor_wrapper.delete_account(
        DeleteAccountParametersNormalised(
            account_id=executor_account_id,
            transfer_account_id=operator_client.operator_account_id,
        )
    )
    executor_client.close()


@pytest.mark.asyncio
async def test_deploy_erc721_minimal_params(setup_environment):
    """Test deploying an ERC721 contract with minimal params."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateERC721Parameters(token_name="TestERC721", token_symbol="TNFT")
    tool = CreateERC721Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "ERC721 token created successfully" in result.human_message
    assert "erc721_address" in exec_result.extra
    assert exec_result.extra["erc721_address"].startswith("0x")

    contract_info = await wrapper.get_contract_info(exec_result.extra["erc721_address"])
    assert contract_info is not None
    assert contract_info.contract_id is not None
    assert contract_info.admin_key is not None


@pytest.mark.asyncio
async def test_deploy_erc721_with_base_uri(setup_environment):
    """Test deploying an ERC721 contract with a custom base URI."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateERC721Parameters(
        token_name="ArtCollection",
        token_symbol="ART",
        base_uri="https://example.com/metadata/",
    )
    tool = CreateERC721Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "ERC721 token created successfully" in result.human_message
    assert "erc721_address" in exec_result.extra
    assert exec_result.extra["erc721_address"].startswith("0x")

    contract_info = await wrapper.get_contract_info(exec_result.extra["erc721_address"])
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_schedule_deploy_erc721(setup_environment):
    """Test scheduling the deployment of an ERC721 contract."""
    client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    params = CreateERC721Parameters(
        token_name=f"ScheduledERC721-{int(time.time())}",
        token_symbol="SNFT",
        base_uri="ipfs://example/",
        scheduling_params=SchedulingParams(is_scheduled=True),
    )
    tool = CreateERC721Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Scheduled creation of ERC721 successfully" in result.human_message
    assert exec_result.raw.schedule_id is not None
    assert exec_result.raw.transaction_id is not None
