import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from hiero_sdk_python.contract.contract_id import ContractId
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.constants.contracts import (
    ERC20_FACTORY_ABI,
    get_erc20_factory_address,
)
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import CreateERC20Parameters
from hedera_agent_kit_py.shared.utils import LedgerId

FACTORY_ADDRESS = get_erc20_factory_address(LedgerId.TESTNET)
FUNCTION_NAME = "deployToken"


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_encodes_function_call_with_all_params(mock_parse, mock_web3):
    mock_context = Context(account_id="0.0.1234")
    mock_client = AsyncMock()

    params = CreateERC20Parameters(
        token_name="MyToken", token_symbol="MTK", decimals=8, initial_supply=1000
    )
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x1234abcd"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    result = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        FACTORY_ADDRESS,
        ERC20_FACTORY_ABI,
        FUNCTION_NAME,
        mock_context,
        mock_client,
    )

    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=FUNCTION_NAME,
        args=["MyToken", "MTK", 8, 1000],
    )

    assert isinstance(result.contract_id, ContractId)
    assert str(result.contract_id) == FACTORY_ADDRESS
    assert result.gas == 3_000_000
    assert isinstance(result.function_parameters, bytes)


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_defaults_decimals_and_supply_when_missing(mock_parse, mock_web3):
    mock_context = Context()
    mock_client = AsyncMock()

    params = CreateERC20Parameters(token_name="DefaultToken", token_symbol="DEF")
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xdeadbeef"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    result = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        FACTORY_ADDRESS,
        ERC20_FACTORY_ABI,
        FUNCTION_NAME,
        mock_context,
        mock_client,
    )

    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=FUNCTION_NAME,
        args=["DefaultToken", "DEF", 18, 0],
    )
    assert result.gas == 3_000_000
    assert isinstance(result.function_parameters, bytes)


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_handles_zero_decimals(mock_parse, mock_web3):
    mock_context = Context()
    mock_client = AsyncMock()

    params = CreateERC20Parameters(
        token_name="ZeroDecimals", token_symbol="ZDC", decimals=0, initial_supply=500
    )
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xabcdef12"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    result = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        FACTORY_ADDRESS,
        ERC20_FACTORY_ABI,
        FUNCTION_NAME,
        mock_context,
        mock_client,
    )

    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=FUNCTION_NAME,
        args=["ZeroDecimals", "ZDC", 0, 500],
    )
    assert result.gas == 3_000_000


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_large_initial_supply(mock_parse, mock_web3):
    mock_context = Context()
    mock_client = AsyncMock()

    params = CreateERC20Parameters(
        token_name="WhaleToken",
        token_symbol="WHL",
        decimals=18,
        initial_supply=1_000_000_000,
    )
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xbeef1234"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    result = await HederaParameterNormaliser.normalise_create_erc20_params(
        params,
        FACTORY_ADDRESS,
        ERC20_FACTORY_ABI,
        FUNCTION_NAME,
        mock_context,
        mock_client,
    )

    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=FUNCTION_NAME,
        args=["WhaleToken", "WHL", 18, 1_000_000_000],
    )
    assert isinstance(result.function_parameters, bytes)
    assert result.gas == 3_000_000
