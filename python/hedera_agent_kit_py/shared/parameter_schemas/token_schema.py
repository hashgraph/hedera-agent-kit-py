from typing import Optional, List, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, TokenType, SupplyType, TokenId
from hiero_sdk_python.tokens.token_create_transaction import TokenParams, TokenKeys
from hiero_sdk_python.tokens.token_transfer import TokenTransfer
from pydantic import BaseModel, Field

from hedera_agent_kit_py.shared.parameter_schemas import (
    OptionalScheduledTransactionParams,
    OptionalScheduledTransactionParamsNormalised,
)


class AirdropRecipient(BaseModel):
    account_id: Annotated[str, Field(description='Recipient account ID (e.g., "0.0.xxxx").')]
    amount: Annotated[Union[int, float, str], Field(description="Amount in base unit.")]


class CreateFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token.")]
    token_symbol: Annotated[str, Field(description="The symbol of the token.")]
    initial_supply: Annotated[int, Field(default=0, description="The initial supply of the token.")]
    supply_type: Annotated[
        int, Field(default=1, description="Supply type of the token. 0 for infinite, 1 for finite.")]
    max_supply: Optional[Annotated[int, Field(description="The maximum supply of the token.")]] = None
    decimals: Annotated[int, Field(default=0, description="The number of decimals.")]
    treasury_account_id: Optional[Annotated[str, Field(description="The treasury account of the token.")]] = None
    is_supply_key: Optional[
        Annotated[bool, Field(description="Determines if the token supply key should be set.")]] = None

class CreateFungibleTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_params: TokenParams
    keys: Optional[TokenKeys] = None


class AirdropFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the token.")]
    source_account_id: Optional[Annotated[str, Field(description="The account to airdrop the token from.")]] = None
    recipients: Annotated[List[AirdropRecipient], Field(min_length=1, description="Array of recipients.")] = Field(...)


## TODO: adapt to the Python SDK Transaction Constructor impl
class AirdropFungibleTokenParametersNormalised(BaseModel):
    token_transfers: Annotated[
        List[TokenTransfer], Field(description="Array of token transfers constructed from recipients.")]


class MintFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the token.")]
    amount: Annotated[float, Field(description="Amount of tokens to mint.")]


## TODO: adapt to the Python SDK Transaction Constructor impl
class MintFungibleTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: Annotated[str, Field(description="The id of the token.")]
    amount: Annotated[float, Field(description="Amount of tokens to mint.")]


class MintNonFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The id of the NFT class.")]
    uris: Annotated[List[str], Field(max_length=10, description="An array of URIs hosting NFT metadata.")] = Field(...)


## TODO: adapt to the Python SDK Transaction Constructor impl
class MintNonFungibleTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: Annotated[str, Field(description="The id of the NFT class.")]
    metadata: Optional[Annotated[List[bytes], Field(description="NFT metadata in bytes.")]] = None


class TransferNonFungibleTokenWithAllowanceParameters(OptionalScheduledTransactionParams):
    source_account_id: Annotated[str, Field(description="Account ID of the token owner.")]
    token_id: Annotated[str, Field(description="The NFT token ID.")]
    recipients: Annotated[List[dict], Field(min_length=1, description="Array of recipient and NFT serial pairs.")]
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo.")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferNonFungibleTokenWithAllowanceParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    source_account_id: Annotated[AccountId, Field(description="Resolved account ID of token owner.")]
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo.")]] = None
    transfers: Annotated[List[dict], Field(description="List of NFT ID and receiver pairs.")] = Field(...)


class TransferFungibleTokenWithAllowanceParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="Token ID to transfer.")]
    source_account_id: Annotated[str, Field(description="Account ID of the token owner.")]
    transfers: Annotated[List[dict], Field(min_length=1, description="Array of recipient transfers.")] = Field(...)
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo.")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferFungibleTokenWithAllowanceParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: Annotated[TokenId, Field(description="Token ID to transfer.")]
    token_transfers: Annotated[
        List[TokenTransfer], Field(description="Resolved token transfers.")] = Field(...)
    approved_transfer: Annotated[dict, Field(description="Approved owner account and amount.")] = Field(...)
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo.")]] = None


class DissociateTokenParameters(OptionalScheduledTransactionParams):
    token_ids: Annotated[List[str], Field(description="List of Hedera token IDs to dissociate")]
    account_id: Optional[Annotated[str, Field(description="Account to dissociate from, defaults to operator")]] = None
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class DissociateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_ids: Annotated[List[TokenId], Field(description="Resolved Hedera Token IDs")]
    account_id: Annotated[AccountId, Field(description="Resolved account ID")]


class UpdateTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="Token ID to update")]
    token_name: Optional[Annotated[str, Field(description="New token name")]] = None
    token_symbol: Optional[Annotated[str, Field(description="New token symbol")]] = None
    token_memo: Optional[Annotated[str, Field(description="New token memo")]] = None
    metadata: Optional[Annotated[bytes, Field(description="New token metadata")]] = None
    treasury_account_id: Optional[Annotated[str, Field(description="New treasury account ID")]] = None
    auto_renew_account_id: Optional[Annotated[str, Field(description="Auto renew account ID")]] = None
    admin_key: Optional[Annotated[PublicKey, Field(description="Admin key")]] = None
    supply_key: Optional[Annotated[PublicKey, Field(description="Supply key")]] = None
    wipe_key: Optional[Annotated[PublicKey, Field(description="Wipe key")]] = None
    freeze_key: Optional[Annotated[PublicKey, Field(description="Freeze key")]] = None
    kyc_key: Optional[Annotated[PublicKey, Field(description="KYC key")]] = None
    fee_schedule_key: Optional[Annotated[PublicKey, Field(description="Fee schedule key")]] = None
    pause_key: Optional[Annotated[PublicKey, Field(description="Pause key")]] = None
    metadata_key: Optional[Annotated[PublicKey, Field(description="Metadata key")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class UpdateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: Annotated[TokenId, Field(description="Resolved Token ID")]
    token_name: Optional[Annotated[str, Field(description="New token name")]] = None
    token_symbol: Optional[Annotated[str, Field(description="New token symbol")]] = None
    token_memo: Optional[Annotated[str, Field(description="New token memo")]] = None
    metadata: Optional[Annotated[bytes, Field(description="New token metadata")]] = None
    treasury_account_id: Optional[Annotated[AccountId, Field(description="Resolved treasury account ID")]] = None
    auto_renew_account_id: Optional[Annotated[AccountId, Field(description="Resolved auto renew account ID")]] = None
    admin_key: Optional[Annotated[PublicKey, Field(description="Admin key")]] = None
    supply_key: Optional[Annotated[PublicKey, Field(description="Supply key")]] = None
    wipe_key: Optional[Annotated[PublicKey, Field(description="Wipe key")]] = None
    freeze_key: Optional[Annotated[PublicKey, Field(description="Freeze key")]] = None
    kyc_key: Optional[Annotated[PublicKey, Field(description="KYC key")]] = None
    fee_schedule_key: Optional[Annotated[PublicKey, Field(description="Fee schedule key")]] = None
    pause_key: Optional[Annotated[PublicKey, Field(description="Pause key")]] = None
    metadata_key: Optional[Annotated[PublicKey, Field(description="Metadata key")]] = None


class CreateNonFungibleTokenParameters(OptionalScheduledTransactionParams):
    token_name: Annotated[str, Field(description="The name of the token")]
    token_symbol: Annotated[str, Field(description="The symbol of the token")]
    max_supply: Annotated[int, Field(default=100, description="Maximum supply of NFTs")]
    treasury_account_id: Optional[Annotated[str, Field(description="Treasury account ID")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class CreateNonFungibleTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_name: Annotated[str, Field(description="The name of the token")]
    token_symbol: Annotated[str, Field(description="The symbol of the token")]
    max_supply: Annotated[int, Field(description="Maximum supply of NFTs")]
    treasury_account_id: Annotated[str, Field(description="Resolved treasury account ID")]
    auto_renew_account_id: Annotated[str, Field(description="Resolved auto renew account ID")]
    supply_key: Annotated[PublicKey, Field(description="Supply key")]
    supply_type: Annotated[int, Field(default=1, description="Must be finite for NFT")]
    token_type: Annotated[int, Field(default=2, description="Non-fungible unique")]
    admin_key: Optional[Annotated[PublicKey, Field(description="Admin key")]] = None
    kyc_key: Optional[Annotated[PublicKey, Field(description="KYC key")]] = None
    freeze_key: Optional[Annotated[PublicKey, Field(description="Freeze key")]] = None
    wipe_key: Optional[Annotated[PublicKey, Field(description="Wipe key")]] = None
    pause_key: Optional[Annotated[PublicKey, Field(description="Pause key")]] = None
    token_memo: Optional[Annotated[str, Field(description="Optional token memo")]] = None


class AssociateTokenParameters(OptionalScheduledTransactionParams):
    account_id: Optional[Annotated[str, Field(description="Account to associate tokens with")]] = None
    token_ids: Annotated[List[str], Field(description="Token IDs to associate")] = Field(..., min_length=1)


## TODO: adapt to the Python SDK Transaction Constructor impl
class AssociateTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    account_id: Annotated[AccountId, Field(description="Resolved account ID")]
    token_ids: Annotated[List[TokenId], Field(description="Resolved token IDs")]


class ApproveNftAllowanceParameters(OptionalScheduledTransactionParams):
    owner_account_id: Optional[Annotated[str, Field(description="Owner account ID")]] = None
    spender_account_id: Annotated[str, Field(description="Spender account ID")]
    token_id: Annotated[str, Field(description="NFT token ID")]
    all_serials: Optional[Annotated[bool, Field(default=False, description="Approve all serials")]] = False
    serial_numbers: Optional[Annotated[List[int], Field(description="Serial numbers to approve")]] = None
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo")]] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class ApproveNftAllowanceParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    nft_approvals: Optional[Annotated[List[dict], Field(description="Resolved NFT approvals")]] = None
    transaction_memo: Optional[Annotated[str, Field(description="Optional transaction memo")]] = None


class DeleteTokenParameters(OptionalScheduledTransactionParams):
    token_id: Annotated[str, Field(description="The ID of the token to delete")]


## TODO: adapt to the Python SDK Transaction Constructor impl
class DeleteTokenParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    token_id: Annotated[TokenId, Field(description="Resolved Token ID to delete")]
