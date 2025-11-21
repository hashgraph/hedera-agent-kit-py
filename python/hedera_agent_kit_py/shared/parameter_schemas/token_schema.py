from typing import Optional, List, Union, Annotated, Dict, Tuple

from hiero_sdk_python import AccountId, PublicKey, TokenId, TokenNftAllowance
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from hiero_sdk_python.tokens.token_transfer import TokenTransfer
from pydantic import Field

from hedera_agent_kit_py.shared.parameter_schemas import (
    OptionalScheduledTransactionParams,
    OptionalScheduledTransactionParamsNormalised,
    BaseModelWithArbitraryTypes,
)


class AirdropRecipient(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        str, Field(description='Recipient account ID (e.g., "0.0.xxxx").')
    ]
    amount: Annotated[Union[int, float, str], Field(description="Amount in base unit.")]


class CreateFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token.")]
    token_symbol: Annotated[str, Field(description="The symbol of the token.")]
    initial_supply: Annotated[
        int, Field(description="The initial supply of the token.")
    ] = 0
    supply_type: Annotated[
        int,
        Field(description="Supply type of the token. 0 for infinite, 1 for finite."),
    ] = 1
    max_supply: Annotated[
        Optional[int], Field(description="The maximum supply of the token.")
    ] = None
    decimals: Annotated[int, Field(description="The number of decimals.")] = 0
    treasury_account_id: Annotated[
        Optional[str], Field(description="The treasury account of the token.")
    ] = None
    is_supply_key: Annotated[
        Optional[bool],
        Field(description="Determines if the token supply key should be set."),
    ] = None


class CreateFungibleTokenParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    token_params: TokenParams
    keys: Optional[TokenKeys] = None


class AirdropFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the token.")]
    source_account_id: Annotated[
        Optional[str], Field(description="The account to airdrop the token from.")
    ] = None
    recipients: Annotated[
        List[AirdropRecipient], Field(min_length=1, description="Array of recipients.")
    ]


class AirdropFungibleTokenParametersNormalised(BaseModelWithArbitraryTypes):
    token_transfers: List[TokenTransfer]


class MintFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the token.")]
    amount: Annotated[float, Field(description="Amount of tokens to mint.")]


class MintFungibleTokenParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    token_id: TokenId
    amount: int


class MintNonFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the NFT class.")]
    uris: Annotated[
        List[str],
        Field(max_length=10, description="An array of URIs hosting NFT metadata."),
    ]


class MintNonFungibleTokenParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    token_id: TokenId
    metadata: Optional[List[bytes]] = None


class TransferNonFungibleTokenWithAllowanceParameters(
    OptionalScheduledTransactionParams
):
    source_account_id: Annotated[
        str, Field(description="Account ID of the token owner.")
    ]
    token_id: Annotated[str, Field(description="The NFT token ID.")]
    recipients: Annotated[
        List[dict],
        Field(min_length=1, description="Array of recipient and NFT serial pairs."),
    ]
    transaction_memo: Annotated[
        Optional[str], Field(description="Optional transaction memo.")
    ] = None


class TransferNonFungibleTokenWithAllowanceParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    nft_approved_transfer: Dict[TokenId, List[Tuple[AccountId, AccountId, int, bool]]]
    transaction_memo: Optional[str] = None


class TransferFungibleTokenWithAllowanceParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="Token ID to transfer.")]
    source_account_id: Annotated[
        str, Field(description="Account ID of the token owner.")
    ]
    transfers: Annotated[
        List[dict], Field(min_length=1, description="Array of recipient transfers.")
    ]
    transaction_memo: Annotated[
        Optional[str], Field(description="Optional transaction memo.")
    ] = None


class TransferFungibleTokenWithAllowanceParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    ft_approved_transfer: Dict[TokenId, Dict[AccountId, int]]
    transaction_memo: Optional[str] = None


class TransferFungibleTokenParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    ft_transfers: Dict[TokenId, Dict[AccountId, int]]
    transaction_memo: Optional[str] = None


class DissociateTokenParameters(OptionalScheduledTransactionParams):
    token_ids: Annotated[
        List[str], Field(description="List of Hedera token IDs to dissociate")
    ]
    account_id: Annotated[
        Optional[str],
        Field(description="Account to dissociate from, defaults to operator"),
    ] = None
    transaction_memo: Annotated[
        Optional[str], Field(description="Optional transaction memo")
    ] = None


class DissociateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_ids: List[TokenId]
    account_id: AccountId
    transaction_memo: Optional[str] = None


class UpdateTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="Token ID to update")]
    token_name: Annotated[Optional[str], Field(description="New token name")] = None
    token_symbol: Annotated[Optional[str], Field(description="New token symbol")] = None
    token_memo: Annotated[Optional[str], Field(description="New token memo")] = None
    metadata: Annotated[Optional[bytes], Field(description="New token metadata")] = None
    treasury_account_id: Annotated[
        Optional[str], Field(description="New treasury account ID")
    ] = None
    auto_renew_account_id: Annotated[
        Optional[str], Field(description="Auto renew account ID")
    ] = None
    admin_key: Annotated[Optional[PublicKey], Field(description="Admin key")] = None
    supply_key: Annotated[Optional[PublicKey], Field(description="Supply key")] = None
    wipe_key: Annotated[Optional[PublicKey], Field(description="Wipe key")] = None
    freeze_key: Annotated[Optional[PublicKey], Field(description="Freeze key")] = None
    kyc_key: Annotated[Optional[PublicKey], Field(description="KYC key")] = None
    fee_schedule_key: Annotated[
        Optional[PublicKey], Field(description="Fee schedule key")
    ] = None
    pause_key: Annotated[Optional[PublicKey], Field(description="Pause key")] = None
    metadata_key: Annotated[Optional[PublicKey], Field(description="Metadata key")] = (
        None
    )


class UpdateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_keys: Optional[TokenKeys] = None
    token_params: Optional[TokenParams] = None
    token_id: TokenId


class CreateNonFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token")]
    token_symbol: Annotated[str, Field(description="The symbol of the token")]
    max_supply: Annotated[int, Field(description="Maximum supply of NFTs")] = 100
    treasury_account_id: Annotated[
        Optional[str], Field(description="Treasury account ID")
    ] = None


class CreateNonFungibleTokenParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    token_params: TokenParams
    keys: Optional[TokenKeys] = None


class AssociateTokenParameters(OptionalScheduledTransactionParams):
    account_id: Annotated[
        Optional[str], Field(description="Account to associate tokens with")
    ] = None
    token_ids: Annotated[
        List[str], Field(min_length=1, description="Token IDs to associate")
    ]


class AssociateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    account_id: AccountId
    token_ids: List[TokenId]


class ApproveNftAllowanceParameters(OptionalScheduledTransactionParams):
    owner_account_id: Annotated[
        Optional[str], Field(description="Owner account ID")
    ] = None
    spender_account_id: Annotated[str, Field(description="Spender account ID")]
    token_id: Annotated[str, Field(description="NFT token ID")]
    all_serials: Annotated[bool, Field(description="Approve all serials")] = False
    serial_numbers: Annotated[
        Optional[List[int]], Field(description="Serial numbers to approve")
    ] = None
    transaction_memo: Annotated[
        Optional[str], Field(description="Optional transaction memo")
    ] = None


class ApproveNftAllowanceParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    nft_allowances: List[TokenNftAllowance]
    transaction_memo: Optional[str] = None


class DeleteTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The ID of the token to delete")]


class DeleteTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: TokenId


class GetTokenInfoParameters(BaseModelWithArbitraryTypes):
    token_id: Annotated[
        Optional[str], Field(description="The token ID to query (e.g., 0.0.12345).")
    ] = None
