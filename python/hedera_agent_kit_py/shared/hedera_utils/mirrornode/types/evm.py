from typing import TypedDict, Optional

from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types.common import (
    MirrornodeKeyInfo,
    TimestampRange,
)


class ContractInfo(TypedDict, total=False):
    admin_key: Optional[MirrornodeKeyInfo]
    auto_renew_account: Optional[str]
    auto_renew_period: Optional[int]
    contract_id: Optional[str]
    created_timestamp: Optional[str]
    deleted: Optional[bool]
    evm_address: Optional[str]
    expiration_timestamp: Optional[str]
    file_id: Optional[str]
    max_automatic_token_associations: Optional[int]
    memo: Optional[str]
    nonce: Optional[int]
    obtainer_id: Optional[str]
    permanent_removal: Optional[bool]
    proxy_account_id: Optional[str]
    timestamp: Optional[TimestampRange]
