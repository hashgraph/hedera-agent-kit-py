"""Unit tests for transfer_erc20 parameter normalization."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from hiero_sdk_python.contract.contract_id import ContractId
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.constants.contracts import (
    ERC20_TRANSFER_FUNCTION_ABI,
    ERC20_TRANSFER_FUNCTION_NAME,
)
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import TransferERC20Parameters
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_encodes_function_call_with_all_parameters(
    mock_get_account_id, mock_get_evm_address, mock_parse, mock_web3
):
    """Test that the function call is encoded with all parameters correctly."""
    mock_context = Context(account_id="0.0.1234")
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0.0.5678",
        recipient_address="0x1234567890123456789012345678901234567890",
        amount=100,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_get_evm_address.return_value = "0x1234567890123456789012345678901234567890"
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x1234abcd"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.return_value = "0x1234567890123456789012345678901234567890"

    result = await HederaParameterNormaliser.normalise_transfer_erc20_params(
        params,
        ERC20_TRANSFER_FUNCTION_ABI,
        ERC20_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify encoding was called with correct parameters
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC20_TRANSFER_FUNCTION_NAME,
        args=["0x1234567890123456789012345678901234567890", 100],
    )

    # Verify result
    assert isinstance(result.contract_id, ContractId)
    assert str(result.contract_id) == "0.0.5678"
    assert result.gas == 100_000
    assert isinstance(result.function_parameters, bytes)


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_resolves_hedera_address_to_evm_for_recipient(
    mock_get_account_id, mock_get_evm_address, mock_parse, mock_web3
):
    """Test that Hedera addresses are resolved to EVM addresses for recipients."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0.0.5678", recipient_address="0.0.9999", amount=50
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_get_evm_address.return_value = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xabcd1234"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.return_value = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

    result = await HederaParameterNormaliser.normalise_transfer_erc20_params(
        params,
        ERC20_TRANSFER_FUNCTION_ABI,
        ERC20_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify address resolution was called
    mock_get_evm_address.assert_called_once_with("0.0.9999", mock_mirror_node)

    # Verify encoding was called with the resolved address
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC20_TRANSFER_FUNCTION_NAME,
        args=["0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", 50],
    )

    assert str(result.contract_id) == "0.0.5678"
    assert result.gas == 100_000


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_resolves_evm_address_to_hedera_for_contract(
    mock_get_account_id, mock_get_evm_address, mock_parse, mock_web3
):
    """Test that EVM addresses are resolved to Hedera account IDs for contracts."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0x1111111111111111111111111111111111111111",
        recipient_address="0.0.9999",
        amount=25,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_get_evm_address.return_value = "0x2222222222222222222222222222222222222222"
    mock_get_account_id.return_value = "0.0.8888"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xbeef1234"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.return_value = "0x2222222222222222222222222222222222222222"

    result = await HederaParameterNormaliser.normalise_transfer_erc20_params(
        params,
        ERC20_TRANSFER_FUNCTION_ABI,
        ERC20_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify account ID resolution was called
    mock_get_account_id.assert_called_once_with(
        "0x1111111111111111111111111111111111111111", mock_mirror_node
    )

    # Verify result uses resolved account ID
    assert str(result.contract_id) == "0.0.8888"


@pytest.mark.asyncio
@patch("hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_handles_large_amount_values(
    mock_get_account_id, mock_get_evm_address, mock_parse, mock_web3
):
    """Test that large amount values are handled correctly."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0.0.5678",
        recipient_address="0x1234567890123456789012345678901234567890",
        amount=1_000_000_000,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_get_evm_address.return_value = "0x1234567890123456789012345678901234567890"
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xdeadbeef"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.return_value = "0x1234567890123456789012345678901234567890"

    result = await HederaParameterNormaliser.normalise_transfer_erc20_params(
        params,
        ERC20_TRANSFER_FUNCTION_ABI,
        ERC20_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify encoding was called with a large amount
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC20_TRANSFER_FUNCTION_NAME,
        args=["0x1234567890123456789012345678901234567890", 1_000_000_000],
    )

    assert result.gas == 100_000

@pytest.mark.asyncio
@patch.object(AccountResolver, "get_hedera_evm_address")
async def test_throws_when_get_hedera_evm_address_fails(mock_get_evm_address):
    """Test that errors from AccountResolver.get_hedera_evm_address are propagated."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0.0.5678", recipient_address="0.0.9999", amount=100
    )

    mock_get_evm_address.side_effect = Exception("Account not found")

    with pytest.raises(Exception, match="Account not found"):
        await HederaParameterNormaliser.normalise_transfer_erc20_params(
            params,
            ERC20_TRANSFER_FUNCTION_ABI,
            ERC20_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )


@pytest.mark.asyncio
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_throws_when_get_hedera_account_id_fails(
    mock_get_account_id, mock_get_evm_address
):
    """Test that errors from AccountResolver.get_hedera_account_id are propagated."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC20Parameters(
        contract_id="0x1111111111111111111111111111111111111111",
        recipient_address="0.0.9999",
        amount=100,
    )

    mock_get_evm_address.return_value = "0x2222222222222222222222222222222222222222"
    mock_get_account_id.side_effect = Exception("Contract not found")

    with pytest.raises(Exception, match="Contract not found"):
        await HederaParameterNormaliser.normalise_transfer_erc20_params(
            params,
            ERC20_TRANSFER_FUNCTION_ABI,
            ERC20_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )
