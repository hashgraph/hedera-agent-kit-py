import time
from typing import cast
from decimal import Decimal

import pytest
from hiero_sdk_python import SupplyType

from hedera_agent_kit_py.plugins.core_token_plugin import CreateFungibleTokenTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateFungibleTokenParameters,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests


def to_display_unit(amount: int, decimals: int) -> Decimal:
    """Helper to convert token supply/max supply from smallest unit to display unit (Decimal)."""
    divisor = Decimal(10**decimals)
    display_amount = Decimal(amount) / divisor
    return display_amount


@pytest.fixture(scope="module")
async def setup_client():
    """Setup operator client and context for tests."""
    client = get_operator_client_for_tests()
    hedera_operations_wrapper = HederaOperationsWrapper(client)

    context = Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(client.operator_account_id)
    )

    yield client, hedera_operations_wrapper, context

    if client:
        client.close()


@pytest.mark.asyncio
async def test_create_token_with_minimal_params(setup_client):
    client, hedera_operations_wrapper, context = setup_client

    params = CreateFungibleTokenParameters(token_name="TestToken", token_symbol="TTK")

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Token created successfully" in result.human_message
    assert exec_result.raw.transaction_id is not None
    assert exec_result.raw.token_id is not None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert token_info.name == params.token_name
    assert token_info.symbol == params.token_symbol
    assert token_info.decimals == 0
    assert token_info.supply_type == SupplyType.FINITE
    assert (
        token_info.total_supply == 1
    )  # NOTE: SDK forces non-zero supply for FINITE supply type


@pytest.mark.asyncio
async def test_create_token_with_supply_decimals_and_finite_type(setup_client):
    client, hedera_operations_wrapper, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="GoldCoin",
        token_symbol="GLD",
        initial_supply=1000,
        decimals=2,
        supply_type=1,
        max_supply=5000,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert token_info.name == params.token_name
    assert token_info.decimals == params.decimals
    assert token_info.supply_type == SupplyType.FINITE

    # Check total supply: 1000 units with 2 decimals => 1000 * 10^2 in tiny units
    assert to_display_unit(token_info.total_supply, token_info.decimals) == Decimal(
        params.initial_supply
    )
    # Check max supply: 5000 units with 2 decimals => 5000 * 10^2 in tiny units
    assert to_display_unit(token_info.max_supply, token_info.decimals) == Decimal(
        params.max_supply
    )


@pytest.mark.asyncio
async def test_create_token_with_treasury_account_and_supply_key(setup_client):
    client, hedera_operations_wrapper, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="SupplyToken",
        token_symbol="SUP",
        treasury_account_id=context.account_id,
        is_supply_key=True,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert "Token created successfully" in result.human_message
    assert str(token_info.treasury) == params.treasury_account_id
    # Supply key should be the operator's public key
    assert str(token_info.supply_key) == str(client.operator_private_key.public_key())


@pytest.mark.asyncio
async def test_schedule_creation_of_fungible_token(setup_client):
    client, _, context = setup_client
    date = time.time()

    params = CreateFungibleTokenParameters(
        token_name=f"ScheduledToken-{str(date)}",
        token_symbol="SCHED",
        is_supply_key=False,
        scheduling_params=SchedulingParams(
            is_scheduled=True, admin_key=False, wait_for_expiry=False
        ),
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Scheduled transaction created successfully" in result.human_message
    assert exec_result.raw.schedule_id is not None
    assert exec_result.raw.transaction_id is not None


@pytest.mark.asyncio
async def test_fail_when_max_supply_is_less_than_initial_supply(setup_client):
    client, _, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="BadToken",
        token_symbol="BAD",
        initial_supply=2000,
        supply_type=1,
        max_supply=1000,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)

    assert result.error is not None
    assert "Failed to create fungible token" in result.human_message
    assert "cannot exceed max" in result.error


@pytest.mark.asyncio
async def test_fail_decimals_are_negative(setup_client):
    client, _, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="BadToken",
        token_symbol="BAD",
        initial_supply=2000,
        decimals=-2,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)

    assert result.error is not None
    assert (
        "Failed to create fungible token: Decimals must be a non-negative integer"
        in result.human_message
    )


@pytest.mark.asyncio
async def test_fail_when_max_supply_is_set_along_infinite_supply_amount(setup_client):
    client, _, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="BadToken",
        token_symbol="BAD",
        initial_supply=5,
        max_supply=1000,
        supply_type=0,  # inifinite
        decimals=2,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)

    assert result.error is not None
    assert "Failed to create fungible token" in result.human_message
    assert "Cannot set max supply and INFINITE supply type" in result.error


@pytest.mark.asyncio
async def test_fail_when_negative_initial_supply(setup_client):
    client, _, context = setup_client

    params = CreateFungibleTokenParameters(
        token_name="BadToken",
        token_symbol="BAD",
        initial_supply=-5,
        max_supply=1000,
        decimals=2,
    )

    tool = CreateFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)

    assert result.error is not None
    assert "Failed to create fungible token" in result.human_message
    assert "Initial supply must be a non-negative integer" in result.error
