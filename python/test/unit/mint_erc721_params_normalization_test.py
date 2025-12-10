import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hiero_sdk_python.contract.contract_id import ContractId
from hiero_sdk_python.schedule.schedule_create_transaction import (
    ScheduleCreateParams,
)

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import (
    MintERC721Parameters,
    SchedulingParams,
)


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_uses_provided_evm_to_address_as_is(mock_parse, mock_web3):
    """Should encode safeMint with provided EVM address and set contract id."""
    mock_context = Context()
    mock_client = AsyncMock()

    params = MintERC721Parameters(
        contract_id="0.0.7001", to_address="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xfaceb00c"
    # Simulate checksum conversion returning the same address for simplicity
    mock_web3.return_value.to_checksum_address.return_value = (
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )
    mock_web3.return_value.eth.contract.return_value = mock_contract

    # Provide a dummy mirrornode service (not used in this path)
    mock_mirrornode_service = MagicMock()

    result = await HederaParameterNormaliser.normalise_mint_erc721_params(
        params, mock_context, mock_mirrornode_service, mock_client
    )

    mock_contract.encode_abi.assert_called_once()
    # Ensure checksum conversion was called
    mock_web3.return_value.to_checksum_address.assert_called_once_with(
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    )
    called_kwargs = mock_contract.encode_abi.call_args.kwargs
    assert called_kwargs["abi_element_identifier"] == "safeMint"
    assert called_kwargs["args"] == [
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    ]

    assert isinstance(result.contract_id, ContractId)
    assert str(result.contract_id) == "0.0.7001"
    assert result.gas == 3_000_000
    assert isinstance(result.function_parameters, bytes)


@pytest.mark.asyncio
@patch.object(
    # patch AccountResolver.get_hedera_evm_address used inside normaliser
    __import__(
        "hedera_agent_kit.shared.utils.account_resolver",
        fromlist=["AccountResolver"],
    ).AccountResolver,
    "get_hedera_evm_address",
    new_callable=AsyncMock,
)
@patch(
    __import__(
        "hedera_agent_kit.shared.utils.account_resolver",
        fromlist=["AccountResolver"],
    ).AccountResolver.__module__
    + ".AccountResolver.get_default_account"
)
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_defaults_to_context_account_and_resolves_hedera_id(
    mock_parse,
    mock_web3,
    mock_get_default_account,
    mock_get_evm_address,
):
    """
    If to_address omitted, default account is used. If it's a Hedera ID, it should
    be resolved to an EVM address via the mirrornode service.
    """
    mock_context = Context(account_id="0.0.1234")
    mock_client = AsyncMock()

    params = MintERC721Parameters(contract_id="0.0.91011")
    mock_parse.return_value = params

    mock_get_default_account.return_value = "0.0.1234"
    mock_get_evm_address.return_value = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xabad1dea"
    # Simulate checksum conversion returning the resolved address unchanged
    mock_web3.return_value.to_checksum_address.return_value = (
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    )
    mock_web3.return_value.eth.contract.return_value = mock_contract

    mock_mirrornode_service = MagicMock()

    result = await HederaParameterNormaliser.normalise_mint_erc721_params(
        params, mock_context, mock_mirrornode_service, mock_client
    )

    mock_get_evm_address.assert_awaited_once_with(
        "0.0.1234", mock_mirrornode_service
    )

    # Ensure checksum conversion was called on the resolved EVM address
    mock_web3.return_value.to_checksum_address.assert_called_once_with(
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    )
    called_kwargs = mock_contract.encode_abi.call_args.kwargs
    assert called_kwargs["args"] == [
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    ]

    assert str(result.contract_id) == "0.0.91011"
    assert result.gas == 3_000_000


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_uses_evm_address_without_mirrornode_when_evm_given(
    mock_parse, mock_web3
):
    """When to_address is an EVM address, should not attempt to resolve via mirrornode."""
    mock_context = Context()
    mock_client = AsyncMock()

    params = MintERC721Parameters(
        contract_id="0.0.42", to_address="0x9999999999999999999999999999999999999999"
    )
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0x0ddf00d0"
    # Simulate checksum conversion returning same address
    mock_web3.return_value.to_checksum_address.return_value = (
        "0x9999999999999999999999999999999999999999"
    )
    mock_web3.return_value.eth.contract.return_value = mock_contract

    # Patch AccountResolver.get_hedera_evm_address to ensure it is not called
    with patch(
        __import__(
            "hedera_agent_kit.shared.utils.account_resolver",
            fromlist=["AccountResolver"],
        ).AccountResolver.__module__
        + ".AccountResolver.get_hedera_evm_address",
        new_callable=AsyncMock,
    ) as mock_get_evm_address:
        mock_mirrornode_service = MagicMock()
        await HederaParameterNormaliser.normalise_mint_erc721_params(
            params, mock_context, mock_mirrornode_service, mock_client
        )

        # Should not resolve via mirrornode if EVM given directly
        mock_get_evm_address.assert_not_awaited()

    # Ensure checksum conversion was called and the encoded arg is the checksummed address
    mock_web3.return_value.to_checksum_address.assert_called_once_with(
        "0x9999999999999999999999999999999999999999"
    )
    called_kwargs = mock_contract.encode_abi.call_args.kwargs
    assert called_kwargs["args"] == [
        "0x9999999999999999999999999999999999999999"
    ]


@pytest.mark.asyncio
@patch.object(
    HederaParameterNormaliser,
    "normalise_scheduled_transaction_params",
    new_callable=AsyncMock,
)
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_scheduling_params_processed_when_scheduled(
    mock_parse, mock_web3, mock_sched_norm
):
    mock_context = Context()
    mock_client = AsyncMock()

    sched_input = SchedulingParams(is_scheduled=True)
    params = MintERC721Parameters(contract_id="0.0.77", scheduling_params=sched_input)
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xdeadbabe"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    mock_sched_norm.return_value = ScheduleCreateParams(wait_for_expiry=False)

    mock_mirrornode_service = MagicMock()
    result = await HederaParameterNormaliser.normalise_mint_erc721_params(
        params, mock_context, mock_mirrornode_service, mock_client
    )

    assert isinstance(result.scheduling_params, ScheduleCreateParams)
    mock_sched_norm.assert_awaited_once_with(sched_input, mock_context, mock_client)


@pytest.mark.asyncio
@patch("hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer.Web3")
@patch.object(HederaParameterNormaliser, "parse_params_with_schema")
async def test_ignores_scheduling_when_not_scheduled(mock_parse, mock_web3):
    mock_context = Context()
    mock_client = AsyncMock()

    sched_input = SchedulingParams(is_scheduled=False)
    params = MintERC721Parameters(contract_id="0.0.88", scheduling_params=sched_input)
    mock_parse.return_value = params

    mock_contract = MagicMock()
    mock_contract.encode_abi.return_value = "0xbeaded"
    mock_web3.return_value.eth.contract.return_value = mock_contract

    with patch.object(
        HederaParameterNormaliser, "normalise_scheduled_transaction_params"
    ) as mock_sched_norm:
        mock_mirrornode_service = MagicMock()
        result = await HederaParameterNormaliser.normalise_mint_erc721_params(
            params, mock_context, mock_mirrornode_service, mock_client
        )

        mock_sched_norm.assert_not_called()
        assert result.scheduling_params is None


@pytest.mark.asyncio
async def test_invalid_contract_id_raises_value_error():
    mock_context = Context()
    mock_client = AsyncMock()

    # Provide an invalid contract id string to trigger parsing error
    params = MintERC721Parameters(contract_id="not-a-valid-id")

    # Do not patch Web3; the error should occur before encoding when ContractId is parsed
    with pytest.raises(Exception):
        mock_mirrornode_service = MagicMock()
        await HederaParameterNormaliser.normalise_mint_erc721_params(
            params, mock_context, mock_mirrornode_service, mock_client
        )
