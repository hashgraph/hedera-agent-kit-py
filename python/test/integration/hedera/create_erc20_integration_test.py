"""Hedera integration tests for create ERC20 tool.

This module tests the ERC20 creation tool by calling it directly with parameters,
omitting the LLM and focusing on testing logic and on-chain execution.
"""

import time
from pprint import pprint
from typing import cast

import pytest
from hiero_sdk_python import PrivateKey, Hbar, Client
from pydantic import ValidationError

from hedera_agent_kit_py.plugins.core_evm_plugin import CreateERC20Tool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateERC20Parameters,
    DeleteAccountParametersNormalised,
    CreateAccountParametersNormalised,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client


@pytest.fixture(scope="module")
async def setup_environment():
    """Set up Hedera operator client and context for tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(20, in_tinybars=False),  # 20 Hbar for EVM operations
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
    operator_client.close()


@pytest.mark.asyncio
async def test_deploy_erc20_minimal_params(setup_environment):
    """Test deploying an ERC20 contract with minimal params."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateERC20Parameters(token_name="TestERC20", token_symbol="TERC")
    tool = CreateERC20Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "ERC20 token created successfully" in result.human_message
    assert "erc20_address" in exec_result.extra
    assert exec_result.extra["erc20_address"].startswith("0x")

    contract_info = await wrapper.get_contract_info(exec_result.extra["erc20_address"])
    assert contract_info is not None
    assert contract_info.contract_id is not None
    assert contract_info.admin_key is not None


@pytest.mark.asyncio
async def test_deploy_erc20_with_supply_and_decimals(setup_environment):
    """Test deploying an ERC20 contract with supply and decimals."""
    client: Client = setup_environment["executor_client"]
    wrapper: HederaOperationsWrapper = setup_environment["executor_wrapper"]
    context: Context = setup_environment["context"]

    params = CreateERC20Parameters(
        token_name="GoldERC20",
        token_symbol="GLD",
        initial_supply=5000,
        decimals=8,
    )
    tool = CreateERC20Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "ERC20 token created successfully" in result.human_message
    assert "erc20_address" in exec_result.extra
    assert exec_result.extra["erc20_address"].startswith("0x")

    contract_info = await wrapper.get_contract_info(exec_result.extra["erc20_address"])
    assert contract_info is not None
    assert contract_info.contract_id is not None


@pytest.mark.asyncio
async def test_schedule_deploy_erc20(setup_environment):
    """Test scheduling the deployment of an ERC20 contract."""
    client: Client = setup_environment["executor_client"]
    context: Context = setup_environment["context"]

    params = CreateERC20Parameters(
        token_name=f"ScheduledERC20-{int(time.time())}",
        token_symbol="SERC",
        scheduling_params=SchedulingParams(is_scheduled=True),
    )
    tool = CreateERC20Tool(context)

    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert "Scheduled creation of ERC20 successfully" in result.human_message
    assert exec_result.raw.schedule_id is not None
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_deploy_erc20_invalid_decimals():
    """Test failure when decimals are invalid (e.g., negative)."""
    with pytest.raises(ValidationError) as e:
        CreateERC20Parameters(
            token_name="BadDecimals", token_symbol="BD", decimals=-5, initial_supply=0
        )

    error_str = str(e.value)
    assert "decimals" in error_str
    assert "Input should be greater than or equal to 0" in error_str
