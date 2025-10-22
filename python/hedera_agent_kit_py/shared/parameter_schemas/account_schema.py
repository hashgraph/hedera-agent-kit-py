from decimal import Decimal
from typing import Optional, List, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, Hbar, TokenAllowance, HbarAllowance
from pydantic import Field

# Local import avoids circular import
from hedera_agent_kit_py.shared.parameter_schemas.common_schema import OptionalScheduledTransactionParams, \
    BaseModelWithArbitraryTypes


class TransferHbarEntry(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="Recipient account ID")
    amount: float = Field(description="Amount of HBAR to transfer. Given in display units.")


class TransferHbarParameters(OptionalScheduledTransactionParams):
    transfers: Annotated[
        List[TransferHbarEntry],
        Field(min_length=1, description="Array of HBAR transfers (in display units)")
    ]
    source_account_id: Annotated[
        Optional[str],
        Field(description="Account ID of the HBAR owner — the balance will be deducted from this account")
    ] = None
    transaction_memo: Annotated[
        Optional[str],
        Field(description="Memo to include with the transaction")
    ] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarEntryNormalised(BaseModelWithArbitraryTypes):
    account_id: 'AccountId'
    amount: 'Hbar'

    model_config = {
        "arbitrary_types_allowed": True
    }


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarParametersNormalised(OptionalScheduledTransactionParams):
    hbar_transfers: List[TransferHbarEntryNormalised]
    transaction_memo: Optional[str] = None


class CreateAccountParameters(OptionalScheduledTransactionParams):
    public_key: Annotated[
        Optional[str],
        Field(description="Account public key. If not provided, the operator's public key will be used.")
    ] = None
    account_memo: Annotated[
        Optional[str],
        Field(description="Optional memo for the account.")
    ] = None
    initial_balance: Annotated[
        float,
        Field(description="Initial HBAR balance to fund the account (defaults to 0).")
    ] = 0
    max_automatic_token_associations: Annotated[
        int,
        Field(description="Max automatic token associations (-1 for unlimited).")
    ] = -1


## TODO: adapt to the Python SDK Transaction Constructor impl
class CreateAccountParametersNormalised(OptionalScheduledTransactionParams):
    account_memo: Optional[str] = None
    initial_balance: Optional[Union[str, float]] = None
    key: Optional[PublicKey] = None
    max_automatic_token_associations: Optional[Union[int, Decimal]] = None

    model_config = {
        "arbitrary_types_allowed": True
    }


class DeleteAccountParameters(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to delete.")
    transfer_account_id: Annotated[
        Optional[str],
        Field(description="Account to transfer remaining funds to. Defaults to operator account if omitted.")
    ] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class DeleteAccountParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: AccountId
    transfer_account_id: AccountId


class UpdateAccountParameters(OptionalScheduledTransactionParams):
    account_id: Annotated[
        Optional[str],
        Field(description="Account ID to update. Defaults to operator account ID.")
    ] = None
    max_automatic_token_associations: Annotated[
        Optional[int],
        Field(description="Max automatic token associations, positive, zero, or -1 for unlimited.")
    ] = None
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


class AccountQueryParameters(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to query.")


class AccountBalanceQueryParameters(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        Optional[str],
        Field(description="The account ID to query.")
    ] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class AccountBalanceQueryParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to query.")


class AccountTokenBalancesQueryParameters(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        Optional[str],
        Field(description="The account ID to query.")
    ] = None
    token_id: Annotated[
        Optional[str],
        Field(description="The token ID to query.")
    ] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class AccountTokenBalancesQueryParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: str
    token_id: Optional[str] = None


class SignScheduleTransactionParameters(BaseModelWithArbitraryTypes):
    schedule_id: str = Field(description="The ID of the scheduled transaction to sign.")


class ScheduleDeleteTransactionParameters(BaseModelWithArbitraryTypes):
    schedule_id: str = Field(description="The ID of the scheduled transaction to delete.")


class ApproveHbarAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Annotated[
        Optional[str],
        Field(description="Owner account ID (defaults to operator account ID if omitted)")
    ] = None
    spender_account_id: str = Field(description="Spender account ID")
    amount: Annotated[float, Field(ge=0, description="Amount of HBAR to approve as allowance")]
    transaction_memo: Annotated[
        Optional[str],
        Field(description="Memo to include with the transaction")
    ] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class ApproveHbarAllowanceParametersNormalised(BaseModelWithArbitraryTypes):
    hbar_approvals: Optional[List[HbarAllowance]] = None
    transaction_memo: Optional[str] = None


class TokenApproval(BaseModelWithArbitraryTypes):
    token_id: str = Field(description="Token ID")
    amount: Annotated[int, Field(ge=0, description="Amount of tokens to approve (must be positive integer)")]


class ApproveTokenAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    token_approvals: Annotated[
        List[TokenApproval],
        Field(min_length=1, description="List of token allowances to approve"),
    ]
    transaction_memo: Optional[str] = None


## TODO: adapt to the Python SDK Transaction Constructor impl
class ApproveTokenAllowanceParametersNormalised(BaseModelWithArbitraryTypes):
    token_approvals: Optional[List[TokenAllowance]] = None
    transaction_memo: Optional[str] = None


class TransferHbarWithAllowanceParameters(TransferHbarParameters):
    """Same as TransferHbarParameters — used when allowance applies."""


## TODO: adapt to the Python SDK Transaction Constructor impl
class TransferHbarWithAllowanceParametersNormalised(BaseModelWithArbitraryTypes):
    hbar_transfers: List[TransferHbarEntryNormalised]
    hbar_approved_transfer: dict = Field(
        description="Owner account ID and HBAR amount approved for transfer"
    )
    transaction_memo: Optional[str] = None


class DeleteHbarAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    transaction_memo: Optional[str] = None


class DeleteTokenAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    token_ids: List[str]
    transaction_memo: Optional[str] = None