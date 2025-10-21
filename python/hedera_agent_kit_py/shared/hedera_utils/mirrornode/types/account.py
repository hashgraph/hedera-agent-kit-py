from decimal import Decimal
from typing import TypedDict, Optional, List, Dict

from .common import MirrornodeKeyInfo
from .token import TokenBalance

class AccountBalanceResponse(TypedDict):
    balance: Decimal
    timestamp: str
    tokens: List[TokenBalance]


class AccountResponse(TypedDict):
    account_id: str
    account_public_key: str
    balance: AccountBalanceResponse
    evm_address: str


class AccountAPIResponse(TypedDict):
    account: str
    key: MirrornodeKeyInfo
    balance: AccountBalanceResponse
    evm_address: str


class AccountTokenBalancesQueryParams(TypedDict, total=False):
    accountId: str
    tokenId: Optional[str]


class NftBalance(TypedDict):
    account_id: str
    created_timestamp: str
    delegating_spender: Optional[str]
    deleted: bool
    metadata: str
    modified_timestamp: str
    serial_number: int
    spender: Optional[str]
    token_id: str


class NftBalanceResponse(TypedDict):
    nfts: List[NftBalance]
    links: Dict[str, Optional[str]]
