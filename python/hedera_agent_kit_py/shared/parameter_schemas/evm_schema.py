from typing import Optional, Annotated

from hiero_sdk_python.contract.contract_id import ContractId
from pydantic import Field
from hedera_agent_kit_py.shared.parameter_schemas import (
    OptionalScheduledTransactionParams,
    OptionalScheduledTransactionParamsNormalised,
    BaseModelWithArbitraryTypes,
)


class ContractExecuteTransactionParametersNormalised(
    OptionalScheduledTransactionParamsNormalised,
    BaseModelWithArbitraryTypes,
):
    contract_id: ContractId
    function_parameters: bytes
    gas: int


class TransferERC20Parameters(OptionalScheduledTransactionParams):
    contract_id: Annotated[
        str,
        Field(
            description="The id of the ERC20 contract. This can be the EVM address or the Hedera account id."
        ),
    ]
    recipient_address: Annotated[
        str,
        Field(
            description="The EVM or Hedera address to which the tokens will be transferred. This can be the EVM address or the Hedera account id."
        ),
    ]
    amount: Annotated[int, Field(description="The amount to be transferred.")]


class CreateERC721Parameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token.")]
    token_symbol: Annotated[str, Field(description="The symbol of the token.")]
    base_uri: Annotated[str, Field(description="The base URI for token metadata.")] = ""


class CreateERC20Parameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token.")]
    token_symbol: Annotated[str, Field(description="The symbol of the token.")]
    decimals: Annotated[
        int,
        Field(ge=0, description="The number of decimals the token supports."),
    ] = 18
    initial_supply: Annotated[
        int,
        Field(ge=0, description="The initial supply of the token."),
    ] = 0


class TransferERC721Parameters(OptionalScheduledTransactionParams):
    contract_id: Annotated[str, Field(description="The id of the ERC721 contract.")]
    from_address: Annotated[
        Optional[str],
        Field(
            description="Address from which the token wContractExecuteTransactionParametersNormalisedill be transferred."
        ),
    ] = None
    to_address: Annotated[
        str, Field(description="Address to which the token will be transferred.")
    ]
    token_id: Annotated[int, Field(description="The ID of the token to transfer.")]


class MintERC721Parameters(OptionalScheduledTransactionParams):
    contract_id: Annotated[str, Field(description="The id of the ERC721 contract.")]
    to_address: Annotated[
        Optional[str],
        Field(description="Address to which the token will be minted."),
    ] = None


class EvmContractCallParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    contract_id: Annotated[str, Field(description="The ID of the contract to call.")]
    function_parameters: Annotated[
        bytes,
        Field(description="The parameters of the function to execute."),
    ]
    gas: Annotated[int, Field(description="The gas limit for the contract call.")]


class ContractInfoQueryParameters(BaseModelWithArbitraryTypes):
    contract_id: Annotated[str, Field(description="The token ID to query.")]
