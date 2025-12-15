from typing import Optional, List, Union, Annotated

from hiero_sdk_python import AccountId, PublicKey, TokenAllowance, HbarAllowance, Hbar
from hiero_sdk_python.account.account_update_transaction import AccountUpdateParams
from hiero_sdk_python.schedule.schedule_id import ScheduleId
from pydantic import Field

# Local import avoids circular import
from hedera_agent_kit.shared.parameter_schemas.common_schema import (
    OptionalScheduledTransactionParams,
    BaseModelWithArbitraryTypes,
    OptionalScheduledTransactionParamsNormalised,
)


class TransferHbarEntry(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="Recipient account ID")
    amount: float = Field(
        description="Amount of HBAR to transfer. Given in display units."
    )


class TransferHbarParameters(
    OptionalScheduledTransactionParams, BaseModelWithArbitraryTypes
):
    transfers: Annotated[
        List[TransferHbarEntry],
        Field(
            min_length=1,
            description=(
                "An array of HBAR transfers. Each transfer object in the array must "
                "specify an 'account_id' and an 'amount'. "
                "Example: [{'account_id': '0.0.123', 'amount': 10.5}]"
            ),
        ),
    ]
    source_account_id: Annotated[
        Optional[str],
        Field(
            description="Account ID of the HBAR owner — the balance will be deducted from this account"
        ),
    ] = None
    transaction_memo: Annotated[
        Optional[str], Field(description="Memo to include with the transaction")
    ] = None


class TransferHbarParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    hbar_transfers: dict["AccountId", int]  # tinybars
    transaction_memo: Optional[str] = None


class CreateAccountParameters(OptionalScheduledTransactionParams):
    public_key: Annotated[
        Optional[str],
        Field(
            description="Account public key. If not provided, the operator's public key will be used."
        ),
    ] = None
    account_memo: Annotated[
        Optional[str],
        Field(
            description="Optional memo for the account. Can be up to 100 characters long. Too long memos will be handled in params normalization"
        ),
    ] = None
    initial_balance: Annotated[
        float,
        Field(description="Initial HBAR balance to fund the account (defaults to 0)."),
    ] = 0
    max_automatic_token_associations: Annotated[
        int, Field(description="Max automatic token associations (-1 for unlimited).")
    ] = -1


class CreateAccountParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    memo: Optional[str] = None
    initial_balance: Union[Hbar] = Hbar(0)
    key: Optional[PublicKey] = None
    max_automatic_token_associations: Optional[int] = None


class DeleteAccountParameters(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to delete.")
    transfer_account_id: Annotated[
        Optional[str],
        Field(
            description="Account to transfer remaining funds to. Defaults to operator account if omitted."
        ),
    ] = None


class DeleteAccountParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: AccountId
    transfer_account_id: AccountId


class UpdateAccountParameters(OptionalScheduledTransactionParams):
    account_id: Annotated[
        Optional[str],
        Field(description="Account ID to update. Defaults to operator account ID."),
    ] = None
    max_automatic_token_associations: Annotated[
        Optional[int],
        Field(
            description="Max automatic token associations, positive, zero, or -1 for unlimited."
        ),
    ] = None
    staked_account_id: Optional[str] = None
    account_memo: Optional[str] = None
    decline_staking_reward: Optional[bool] = None


class UpdateAccountParametersNormalised(OptionalScheduledTransactionParamsNormalised):
    account_params: AccountUpdateParams


class AccountQueryParameters(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to query.")


class AccountQueryParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: str


class AccountBalanceQueryParameters(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        Optional[str], Field(description="The account ID to query.")
    ] = None


class AccountBalanceQueryParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: str = Field(description="The account ID to query.")


class AccountTokenBalancesQueryParameters(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        Optional[str], Field(description="The account ID to query.")
    ] = None
    token_id: Annotated[Optional[str], Field(description="The token ID to query.")] = (
        None
    )


class AccountTokenBalancesQueryParametersNormalised(BaseModelWithArbitraryTypes):
    account_id: str
    token_id: Optional[str] = None


class SignScheduleTransactionToolParameters(BaseModelWithArbitraryTypes):
    """Tool input parameters for signing a scheduled transaction (LLM-facing)."""

    schedule_id: str = Field(
        description="The ID of the scheduled transaction to sign."
    )


class SignScheduleTransactionParametersNormalised(BaseModelWithArbitraryTypes):
    """Normalised parameters for signing a scheduled transaction (SDK-facing)."""

    schedule_id: ScheduleId = Field(
        description="The ID of the scheduled transaction to sign."
    )


# Legacy alias for backward compatibility with HederaBuilder
SignScheduleTransactionParameters = SignScheduleTransactionParametersNormalised


class ScheduleDeleteTransactionParameters(BaseModelWithArbitraryTypes):
    schedule_id: str = Field(
        description="The ID of the scheduled transaction to delete."
    )


class ScheduleDeleteTransactionParametersNormalised(BaseModelWithArbitraryTypes):
    schedule_id: ScheduleId = Field(
        description="The ID of the scheduled transaction to delete."
    )


class ApproveHbarAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Annotated[
        Optional[str],
        Field(
            description="Owner account ID (defaults to operator account ID if omitted)"
        ),
    ] = None
    spender_account_id: str = Field(description="Spender account ID")
    amount: Annotated[
        float, Field(ge=0, description="Amount of HBAR to approve as allowance")
    ]
    transaction_memo: Annotated[
        Optional[str], Field(description="Memo to include with the transaction")
    ] = None


class ApproveHbarAllowanceParametersNormalised(BaseModelWithArbitraryTypes):
    hbar_allowances: List[HbarAllowance]
    transaction_memo: Optional[str] = None


class TokenApproval(BaseModelWithArbitraryTypes):
    token_id: str = Field(description="Token ID")
    amount: Annotated[
        float,
        Field(
            ge=0,
            description="Amount of tokens to approve (must be positive number). Given in display units",
        ),
    ]


class ApproveTokenAllowanceParameters(BaseModelWithArbitraryTypes):
    owner_account_id: Optional[str] = None
    spender_account_id: str
    token_approvals: Annotated[
        List[TokenApproval],
        Field(min_length=1, description="Required list of token allowances to approve"),
    ]
    transaction_memo: Optional[str] = None


class ApproveTokenAllowanceParametersNormalised(BaseModelWithArbitraryTypes):
    token_allowances: List[TokenAllowance]
    transaction_memo: Optional[str] = None


class TransferHbarWithAllowanceParameters(TransferHbarParameters):
    """Same as TransferHbarParameters — used when allowance applies."""


class TransferHbarWithAllowanceParametersNormalised(
    OptionalScheduledTransactionParamsNormalised
):
    hbar_approved_transfers: dict["AccountId", int] = Field(
        description="Owner account ID and HBAR amount approved for transfer (tinybars)"
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
