from decimal import Decimal
from typing import Optional, List, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, Hbar, TokenAllowance, HbarAllowance
from pydantic import BaseModel, Field

from hedera_agent_kit_py.shared.parameter_schemas import OptionalScheduledTransactionParams


class TransferHbarEntry(BaseModel):
    account_id: str = Field(description="Recipient account ID")
    amount: float = Field(description="Amount of HBAR to transfer. Given in display units.")


class TransferHbarParameters(OptionalScheduledTransactionParams):
    transfers: Annotated[
        List[TransferHbarEntry],
        Field(min_length=1, description="Array of HBAR transfers (in display units)")
    ]
    source_account_id: Optional[str] = Field(
        default=None,
        description="Account ID of the HBAR owner — the balance will be deducted from this account",
    )
    transaction_memo: Optional[str] = Field(
        default=None,
        description="Memo to include with the transaction",
    )


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarEntryNormalised(BaseModel):
    account_id: AccountId
    amount: Hbar

## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarParametersNormalised(OptionalScheduledTransactionParams):
    hbar_transfers: List[TransferHbarEntryNormalised]
    transaction_memo: Optional[str] = None


class CreateAccountParameters(OptionalScheduledTransactionParams):
    public_key: Optional[str] = Field(
        None,
        description="Account public key. If not provided, the operator’s public key will be used.",
    )
    account_memo: Optional[str] = Field(None, description="Optional memo for the account.")
    initial_balance: float = Field(0, description="Initial HBAR balance to fund the account (defaults to 0).")
    max_automatic_token_associations: int = Field(
        -1,
        description="Max automatic token associations (-1 for unlimited).",
    )


## TODO: adapt to the Python SDK Transaction Constructor impl
class CreateAccountParametersNormalised(OptionalScheduledTransactionParams):
    account_memo: Optional[str] = None
    initial_balance: Optional[Union[str, float]] = None
    key: Optional[PublicKey] = None
    max_automatic_token_associations: Optional[Union[int, Decimal]] = None


class DeleteAccountParameters(BaseModel):
    account_id: str = Field(description="The account ID to delete.")
    transfer_account_id: Optional[str] = Field(
        None,
        description="Account to transfer remaining funds to. Defaults to operator account if omitted.",
    )


## TODO: adapt to the Python SDK Transaction Constructor impl
class DeleteAccountParametersNormalised(BaseModel):
    account_id: AccountId
    transfer_account_id: AccountId


class UpdateAccountParameters(OptionalScheduledTransactionParams):
    account_id: Optional[str] = Field(
        None,
        description="Account ID to update. Defaults to operator account ID.",
    )
    max_automatic_token_associations: Optional[int] = Field(
        None,
        description="Max automatic token associations, positive, zero, or -1 for unlimited.",
    )
    staked_account_id: Optional[str] = None
    account_memo: Optional[str] = None
    decline_staking_reward: Optional[bool] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class UpdateAccountParametersNormalised(OptionalScheduledTransactionParams):
    account_id: AccountId
    max_automatic_token_associations: Optional[Union[int, Decimal]] = None
    staked_account_id: Optional[Union[str, AccountId]] = None
    account_memo: Optional[str] = None
    decline_staking_reward: Optional[bool] = None


class AccountQueryParameters(BaseModel):
    account_id: str = Field(description="The account ID to query.")


class AccountBalanceQueryParameters(BaseModel):
    account_id: Optional[str] = Field(None, description="The account ID to query.")


## TODO: adapt to the Python SDK Transaction Constructor impl
class AccountBalanceQueryParametersNormalised(BaseModel):
    account_id: str = Field(description="The account ID to query.")


class AccountTokenBalancesQueryParameters(BaseModel):
    account_id: Optional[str] = Field(None, description="The account ID to query.")
    token_id: Optional[str] = Field(None, description="The token ID to query.")


## TODO: adapt to the Python SDK Transaction Constructor impl
class AccountTokenBalancesQueryParametersNormalised(BaseModel):
    account_id: str
    token_id: Optional[str] = None


class SignScheduleTransactionParameters(BaseModel):
    schedule_id: str = Field(description="The ID of the scheduled transaction to sign.")


class ScheduleDeleteTransactionParameters(BaseModel):
    schedule_id: str = Field(description="The ID of the scheduled transaction to delete.")


class ApproveHbarAllowanceParameters(BaseModel):
    owner_account_id: Optional[str] = Field(
        None,
        description="Owner account ID (defaults to operator account ID if omitted)",
    )
    spender_account_id: str = Field(description="Spender account ID")
    amount: Annotated[float, Field(ge=0, description="Amount of HBAR to approve as allowance")]
    transaction_memo: Optional[str] = Field(
        None,
        description="Memo to include with the transaction",
    )


## TODO: adapt to the Python SDK Transaction Constructor impl
class ApproveHbarAllowanceParametersNormalised(BaseModel):
    hbar_approvals: Optional[List[HbarAllowance]] = None
    transaction_memo: Optional[str] = None


class TokenApproval(BaseModel):
    token_id: str = Field(description="Token ID")
    amount: Annotated[int, Field(ge=0, description="Amount of tokens to approve (must be positive integer)")]


class ApproveTokenAllowanceParameters(BaseModel):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    token_approvals: Annotated[
        List[TokenApproval],
        Field(min_length=1, description="List of token allowances to approve"),
    ]
    transaction_memo: Optional[str] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class ApproveTokenAllowanceParametersNormalised(BaseModel):
    token_approvals: Optional[List[TokenAllowance]] = None
    transaction_memo: Optional[str] = None


class TransferHbarWithAllowanceParameters(TransferHbarParameters):
    """Same as TransferHbarParameters — used when allowance applies."""


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarWithAllowanceParametersNormalised(BaseModel):
    hbar_transfers: List[TransferHbarEntryNormalised]
    hbar_approved_transfer: dict = Field(
        description="Owner account ID and HBAR amount approved for transfer"
    )
    transaction_memo: Optional[str] = None


class DeleteHbarAllowanceParameters(BaseModel):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    transaction_memo: Optional[str] = None


class DeleteTokenAllowanceParameters(BaseModel):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    token_ids: List[str]
    transaction_memo: Optional[str] = None
