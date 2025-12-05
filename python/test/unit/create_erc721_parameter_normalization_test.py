"""Unit tests for EVM parameter normalization (ERC20 and ERC721).

These tests validate that HederaParameterNormaliser produces correctly
encoded function parameters, contract IDs, gas values, and properly
handles scheduled transaction parameters for ERC20 and ERC721 creation.
"""

from unittest.mock import AsyncMock, patch
import pytest

from web3 import Web3
from hiero_sdk_python.contract.contract_id import ContractId
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateERC20Parameters,
    CreateERC721Parameters,
    SchedulingParams,
)
from hedera_agent_kit_py.shared.constants.contracts import (
    ERC20_FACTORY_ABI,
    ERC721_FACTORY_ABI,
)


# -----------------------------
# Helpers
# -----------------------------

TESTNET_ERC20_FACTORY = "0.0.6471814"
TESTNET_ERC721_FACTORY = "0.0.6510666"


def build_encoded_call(abi, function_name: str, args: list) -> bytes:
    w3 = Web3()
    contract = w3.eth.contract(abi=abi)
    encoded = contract.encode_abi(
        abi_element_identifier=function_name,
        args=args,
    )
    return bytes.fromhex(encoded[2:])


# -----------------------------
# ERC20 tests
# -----------------------------


@pytest.mark.asyncio
async def test_normalise_create_erc20_no_schedule_encodes_correctly():
    context = Context()
    client = AsyncMock()
    client.network = "testnet"

    params = CreateERC20Parameters(
        token_name="TestToken",
        token_symbol="TTK",
        decimals=18,
        initial_supply=1_000_000,
    )

    normalised = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        TESTNET_ERC20_FACTORY,
        ERC20_FACTORY_ABI,
        "deployToken",
        context,
        client,
    )

    # Verify contract id and gas
    assert normalised.contract_id == ContractId.from_string(TESTNET_ERC20_FACTORY)
    assert normalised.gas == 3_000_000
    assert normalised.scheduling_params is None

    expected_bytes = build_encoded_call(
        ERC20_FACTORY_ABI,
        "deployToken",
        ["TestToken", "TTK", 18, 1_000_000],
    )
    assert normalised.function_parameters == expected_bytes


@pytest.mark.asyncio
@patch.object(
    HederaParameterNormaliser,
    "normalise_scheduled_transaction_params",
    new_callable=AsyncMock,
)
async def test_normalise_create_erc20_with_schedule_calls_scheduler(mock_sched):
    context = Context()
    client = AsyncMock()
    client.network = "testnet"

    # Return a simple ScheduleCreateParams from the patched scheduler
    mock_sched.return_value = ScheduleCreateParams()

    params = CreateERC20Parameters(
        token_name="TestToken",
        token_symbol="TTK",
        decimals=8,
        initial_supply=123,
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    normalised = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        TESTNET_ERC20_FACTORY,
        ERC20_FACTORY_ABI,
        "deployToken",
        context,
        client,
    )

    mock_sched.assert_awaited_once()
    assert isinstance(normalised.scheduling_params, ScheduleCreateParams)


# -----------------------------
# ERC721 tests
# -----------------------------


@pytest.mark.asyncio
async def test_normalise_create_erc721_no_schedule_encodes_correctly():
    context = Context()
    client = AsyncMock()
    client.network = "testnet"

    params = CreateERC721Parameters(
        token_name="MyNFT",
        token_symbol="MNFT",
        base_uri="https://example.com/metadata/",
    )

    normalised = await HederaParameterNormaliser.normalise_create_erc721_params(
        params,
        TESTNET_ERC721_FACTORY,
        ERC721_FACTORY_ABI,
        "deployToken",
        context,
        client,
    )

    assert normalised.contract_id == ContractId.from_string(TESTNET_ERC721_FACTORY)
    assert normalised.gas == 3_000_000
    assert normalised.scheduling_params is None

    expected_bytes = build_encoded_call(
        ERC721_FACTORY_ABI,
        "deployToken",
        ["MyNFT", "MNFT", "https://example.com/metadata/"],
    )
    assert normalised.function_parameters == expected_bytes


@pytest.mark.asyncio
@patch.object(
    HederaParameterNormaliser,
    "normalise_scheduled_transaction_params",
    new_callable=AsyncMock,
)
async def test_normalise_create_erc721_with_schedule_calls_scheduler(mock_sched):
    context = Context()
    client = AsyncMock()
    client.network = "testnet"

    mock_sched.return_value = ScheduleCreateParams()

    params = CreateERC721Parameters(
        token_name="MyNFT",
        token_symbol="MNFT",
        base_uri="ipfs://QmHash/",
        scheduling_params=SchedulingParams(is_scheduled=True),
    )

    normalised = await HederaParameterNormaliser.normalise_create_erc721_params(
        params,
        TESTNET_ERC721_FACTORY,
        ERC721_FACTORY_ABI,
        "deployToken",
        context,
        client,
    )

    mock_sched.assert_awaited_once()
    assert isinstance(normalised.scheduling_params, ScheduleCreateParams)
