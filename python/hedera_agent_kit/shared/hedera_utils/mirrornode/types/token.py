from typing import TypedDict, Optional, List, Any

from hedera_agent_kit.shared.hedera_utils.mirrornode.types.common import (
    MirrornodeKeyInfo,
    TimestampRange,
    Links,
)


class TokenBalance(TypedDict):
    automatic_association: bool
    created_timestamp: str
    token_id: str
    freeze_status: str
    kyc_status: str
    balance: int
    decimals: int
    symbol: str


class CustomFees(TypedDict, total=False):
    created_timestamp: str
    fixed_fees: List[Any]
    fractional_fees: List[Any]


class TokenBalancesResponse(TypedDict):
    tokens: List[TokenBalance]


class TokenInfo(TypedDict, total=False):
    token_id: Optional[str]
    name: str
    symbol: str
    type: Optional[str]
    memo: Optional[str]
    decimals: str
    initial_supply: Optional[str]
    total_supply: Optional[str]
    max_supply: Optional[str]
    supply_type: Optional[str]
    treasury_account_id: Optional[str]
    auto_renew_account: Optional[str]
    auto_renew_period: Optional[int]
    deleted: bool
    freeze_default: Optional[bool]
    pause_status: Optional[str]
    created_timestamp: Optional[str]
    modified_timestamp: Optional[str]
    expiry_timestamp: Optional[int]

    admin_key: Optional[MirrornodeKeyInfo]
    supply_key: Optional[MirrornodeKeyInfo]
    kyc_key: Optional[MirrornodeKeyInfo]
    freeze_key: Optional[MirrornodeKeyInfo]
    wipe_key: Optional[MirrornodeKeyInfo]
    pause_key: Optional[MirrornodeKeyInfo]
    fee_schedule_key: Optional[MirrornodeKeyInfo]
    metadata_key: Optional[MirrornodeKeyInfo]

    metadata: Optional[str]
    custom_fees: Optional[CustomFees]


class TokenAirdrop(TypedDict):
    amount: int
    receiver_id: Optional[str]
    sender_id: Optional[str]
    serial_number: Optional[int]
    timestamp: TimestampRange
    token_id: Optional[str]


class TokenAirdropsResponse(TypedDict):
    airdrops: List[TokenAirdrop]
    links: Links


class TokenAllowance(TypedDict):
    amount: int
    amount_granted: int
    owner: str
    spender: str
    timestamp: TimestampRange
    token_id: str


class TokenAllowanceResponse(TypedDict):
    allowances: List[TokenAllowance]
    links: Links
