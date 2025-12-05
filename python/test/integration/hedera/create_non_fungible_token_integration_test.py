import time
from typing import cast

import pytest
from hiero_sdk_python import SupplyType, TokenType

from hedera_agent_kit_py.plugins.core_token_plugin.create_non_fungible_token import (
    CreateNonFungibleTokenTool,
)
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateNonFungibleTokenParameters,
    SchedulingParams,
)
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests


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
async def test_create_nft_with_minimal_params(setup_client):
    """Test creating NFT with minimal params defaults to FINITE supply."""
    client, hedera_operations_wrapper, context = setup_client

    params = CreateNonFungibleTokenParameters(token_name="TestNFT", token_symbol="TNFT")

    tool = CreateNonFungibleTokenTool(context)
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
    assert token_info.token_type == TokenType.NON_FUNGIBLE_UNIQUE

    # Updated expectation: Default is now FINITE when supply_type is not specified
    assert token_info.supply_type == SupplyType.FINITE
    assert token_info.max_supply == 100  # Default max supply


@pytest.mark.asyncio
async def test_create_nft_explicit_infinite_supply(setup_client):
    """Test explicitly creating an NFT with infinite supply."""
    client, hedera_operations_wrapper, context = setup_client

    params = CreateNonFungibleTokenParameters(
        token_name="InfiniteNFT",
        token_symbol="INFT",
        supply_type=0,  # Explicitly INFINITE
    )

    tool = CreateNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert token_info.name == "InfiniteNFT"
    assert token_info.supply_type == SupplyType.INFINITE


@pytest.mark.asyncio
async def test_create_nft_with_max_supply(setup_client):
    client, hedera_operations_wrapper, context = setup_client

    params = CreateNonFungibleTokenParameters(
        token_name="MaxSupplyNFT",
        token_symbol="MAX",
        max_supply=500,
    )

    tool = CreateNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert token_info.name == params.token_name
    assert token_info.supply_type == SupplyType.FINITE
    assert token_info.max_supply == 500


@pytest.mark.asyncio
async def test_create_nft_with_explicit_finite_supply_type(setup_client):
    """Test creating NFT with explicit FINITE supply type and custom max_supply."""
    client, hedera_operations_wrapper, context = setup_client

    params = CreateNonFungibleTokenParameters(
        token_name="ExplicitFiniteNFT",
        token_symbol="EFNFT",
        supply_type=1,  # Explicitly FINITE
        max_supply=250,
    )

    tool = CreateNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert token_info.name == "ExplicitFiniteNFT"
    assert token_info.symbol == "EFNFT"
    assert token_info.supply_type == SupplyType.FINITE
    assert token_info.max_supply == 250



@pytest.mark.asyncio
async def test_create_nft_with_treasury_account(setup_client):
    client, hedera_operations_wrapper, context = setup_client

    params = CreateNonFungibleTokenParameters(
        token_name="TreasuryNFT",
        token_symbol="TRSY",
        treasury_account_id=context.account_id,
    )

    tool = CreateNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    token_id_str = str(exec_result.raw.token_id)

    token_info = hedera_operations_wrapper.get_token_info(token_id_str)

    assert str(token_info.treasury) == params.treasury_account_id
    # Supply key should be the operator's public key (default behavior when treasury is operator)
    assert str(token_info.supply_key) == str(client.operator_private_key.public_key())


@pytest.mark.asyncio
async def test_schedule_creation_of_nft(setup_client):
    client, _, context = setup_client
    date = time.time()

    params = CreateNonFungibleTokenParameters(
        token_name=f"ScheduledNFT-{str(date)}",
        token_symbol="SCHED",
        scheduling_params=SchedulingParams(
            is_scheduled=True, admin_key=False, wait_for_expiry=False
        ),
    )

    tool = CreateNonFungibleTokenTool(context)
    result: ToolResponse = await tool.execute(client, context, params)
    exec_result = cast(ExecutedTransactionToolResponse, result)

    assert result.error is None
    assert "Scheduled transaction created successfully" in result.human_message
    assert exec_result.raw.schedule_id is not None
    assert exec_result.raw.transaction_id is not None
