"""Unit tests for transfer_erc721 parameter normalization."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from hiero_sdk_python.contract.contract_id import ContractId
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.constants.contracts import (
    ERC721_TRANSFER_FUNCTION_ABI,
    ERC721_TRANSFER_FUNCTION_NAME,
)
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import TransferERC721Parameters
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_encodes_function_call_with_all_parameters(
    mock_get_account_id, mock_get_evm_address, mock_resolve, mock_parse, mock_web3
):
    """Test that the function call is encoded with all parameters correctly."""
    mock_context = Context(account_id="0.0.1234")
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        from_address="0.0.1234",
        to_address="0x2222222222222222222222222222222222222222",
        token_id=1,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_resolve.return_value = "0.0.1234"
    mock_get_evm_address.side_effect = [
        "0x1111111111111111111111111111111111111111",  # from_address
        "0x2222222222222222222222222222222222222222",  # to_address
    ]
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x1234abcd"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.side_effect = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    ]

    result = await HederaParameterNormaliser.normalise_transfer_erc721_params(
        params,
        ERC721_TRANSFER_FUNCTION_ABI,
        ERC721_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify encoding was called with correct parameters
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC721_TRANSFER_FUNCTION_NAME,
        args=[
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            1,
        ],
    )

    # Verify result
    assert isinstance(result.contract_id, ContractId)
    assert str(result.contract_id) == "0.0.5678"
    assert result.gas == 100_000
    assert isinstance(result.function_parameters, bytes)


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_resolves_from_address_using_account_resolver_pattern(
    mock_get_account_id, mock_get_evm_address, mock_resolve, mock_parse, mock_web3
):
    """Test that fromAddress is resolved using AccountResolver pattern."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        from_address="0.0.9999",
        to_address="0.0.8888",
        token_id=2,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_resolve.return_value = "0.0.9999"
    mock_get_evm_address.side_effect = [
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ]
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3 encoding and checksum conversion
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xabcd1234"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.side_effect = [
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ]

    await HederaParameterNormaliser.normalise_transfer_erc721_params(
        params,
        ERC721_TRANSFER_FUNCTION_ABI,
        ERC721_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify resolve_account was called
    mock_resolve.assert_called_once_with("0.0.9999", mock_context, mock_client)

    # Verify get_hedera_evm_address was called for both addresses
    assert mock_get_evm_address.call_count == 2
    mock_get_evm_address.assert_any_call("0.0.9999", mock_mirror_node)
    mock_get_evm_address.assert_any_call("0.0.8888", mock_mirror_node)

    # Verify encoding
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC721_TRANSFER_FUNCTION_NAME,
        args=[
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            2,
        ],
    )


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_resolves_evm_address_to_hedera_for_contract(
    mock_get_account_id, mock_get_evm_address, mock_resolve, mock_parse, mock_web3
):
    """Test that EVM addresses are resolved to Hedera account IDs for contracts."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0x1111111111111111111111111111111111111111",
        from_address="0.0.1234",
        to_address="0.0.5678",
        token_id=0,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_resolve.return_value = "0.0.1234"
    mock_get_evm_address.side_effect = [
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
    ]
    mock_get_account_id.return_value = "0.0.8888"

    # Mock Web3
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x12345678"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.side_effect = [
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
    ]

    result = await HederaParameterNormaliser.normalise_transfer_erc721_params(
        params,
        ERC721_TRANSFER_FUNCTION_ABI,
        ERC721_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify get_hedera_account_id was called with EVM address
    mock_get_account_id.assert_called_once_with(
        "0x1111111111111111111111111111111111111111", mock_mirror_node
    )

    # Verify result has correct contract ID
    assert str(result.contract_id) == "0.0.8888"


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_handles_optional_from_address_by_resolving_from_context(
    mock_get_account_id, mock_get_evm_address, mock_resolve, mock_parse, mock_web3
):
    """Test that optional fromAddress is resolved from context."""
    mock_context = Context(account_id="0.0.1234")
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        to_address="0.0.8888",
        token_id=3,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_resolve.return_value = "0.0.1234"  # Defaults to operator
    mock_get_evm_address.side_effect = [
        "0x5555555555555555555555555555555555555555",
        "0x6666666666666666666666666666666666666666",
    ]
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xabcdef12"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.side_effect = [
        "0x5555555555555555555555555555555555555555",
        "0x6666666666666666666666666666666666666666",
    ]

    await HederaParameterNormaliser.normalise_transfer_erc721_params(
        params,
        ERC721_TRANSFER_FUNCTION_ABI,
        ERC721_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify resolve_account was called with None (defaults to operator)
    mock_resolve.assert_called_once_with(None, mock_context, mock_client)

    # Verify encoding
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC721_TRANSFER_FUNCTION_NAME,
        args=[
            "0x5555555555555555555555555555555555555555",
            "0x6666666666666666666666666666666666666666",
            3,
        ],
    )


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_handles_large_token_id_values(
    mock_get_account_id, mock_get_evm_address, mock_resolve, mock_parse, mock_web3
):
    """Test that large tokenId values are handled correctly."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        from_address="0.0.1234",
        to_address="0x2222222222222222222222222222222222222222",
        token_id=999_999_999,
    )
    mock_parse.return_value = params

    # Mock address resolution
    mock_resolve.return_value = "0.0.1234"
    mock_get_evm_address.side_effect = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    ]
    mock_get_account_id.return_value = "0.0.5678"

    # Mock Web3
    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x99999999"
    mock_web3.return_value.eth.contract.return_value = mock_contract
    mock_web3.return_value.to_checksum_address.side_effect = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    ]

    await HederaParameterNormaliser.normalise_transfer_erc721_params(
        params,
        ERC721_TRANSFER_FUNCTION_ABI,
        ERC721_TRANSFER_FUNCTION_NAME,
        mock_context,
        mock_mirror_node,
        mock_client,
    )

    # Verify encoding with large token ID
    mock_contract.encode_abi.assert_called_once_with(
        abi_element_identifier=ERC721_TRANSFER_FUNCTION_NAME,
        args=[
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            999_999_999,
        ],
    )


# Error handling tests
@pytest.mark.asyncio
async def test_throws_when_contract_id_is_missing():
    """Test that missing contractId throws validation error."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = {
        "from_address": "0.0.1234",
        "to_address": "0x2222222222222222222222222222222222222222",
        "token_id": 1,
    }

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "contract_id" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_throws_when_to_address_is_missing():
    """Test that missing toAddress throws validation error."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = {
        "contract_id": "0.0.5678",
        "from_address": "0.0.1234",
        "token_id": 1,
    }

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "to_address" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_throws_when_token_id_is_missing():
    """Test that missing tokenId throws validation error."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = {
        "contract_id": "0.0.5678",
        "from_address": "0.0.1234",
        "to_address": "0x2222222222222222222222222222222222222222",
    }

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "token_id" in str(exc_info.value).lower()


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
async def test_throws_when_get_hedera_evm_address_fails_for_from_address(
    mock_get_evm_address, mock_resolve
):
    """Test that errors from get_hedera_evm_address for fromAddress are propagated."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        from_address="0.0.9999",
        to_address="0.0.8888",
        token_id=1,
    )

    mock_resolve.return_value = "0.0.9999"
    mock_get_evm_address.side_effect = Exception("From account not found")

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "From account not found" in str(exc_info.value)


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
async def test_throws_when_get_hedera_evm_address_fails_for_to_address(
    mock_get_evm_address, mock_resolve
):
    """Test that errors from get_hedera_evm_address for toAddress are propagated."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0.0.5678",
        from_address="0.0.1234",
        to_address="0.0.8888",
        token_id=1,
    )

    mock_resolve.return_value = "0.0.1234"
    mock_get_evm_address.side_effect = [
        "0x1111111111111111111111111111111111111111",
        Exception("To account not found"),
    ]

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "To account not found" in str(exc_info.value)


@pytest.mark.asyncio
@patch.object(AccountResolver, "resolve_account")
@patch.object(AccountResolver, "get_hedera_evm_address")
@patch.object(AccountResolver, "get_hedera_account_id")
async def test_throws_when_get_hedera_account_id_fails(
    mock_get_account_id, mock_get_evm_address, mock_resolve
):
    """Test that errors from get_hedera_account_id are propagated."""
    mock_context = Context()
    mock_client = AsyncMock()
    mock_mirror_node = AsyncMock()

    params = TransferERC721Parameters(
        contract_id="0x1111111111111111111111111111111111111111",
        from_address="0.0.1234",
        to_address="0.0.8888",
        token_id=1,
    )

    mock_resolve.return_value = "0.0.1234"
    mock_get_evm_address.side_effect = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    ]
    mock_get_account_id.side_effect = Exception("Contract not found")

    with pytest.raises(Exception) as exc_info:
        await HederaParameterNormaliser.normalise_transfer_erc721_params(
            params,
            ERC721_TRANSFER_FUNCTION_ABI,
            ERC721_TRANSFER_FUNCTION_NAME,
            mock_context,
            mock_mirror_node,
            mock_client,
        )

    assert "Contract not found" in str(exc_info.value)
