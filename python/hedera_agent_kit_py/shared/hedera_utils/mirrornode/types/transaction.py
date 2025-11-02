from typing import TypedDict, List, Optional, Any, Dict


class TransferData(TypedDict):
    account: str
    amount: int
    is_approval: bool


class TransactionData(TypedDict):
    batch_key: Optional[str]
    bytes: Optional[str]
    charged_tx_fee: int
    consensus_timestamp: str
    entity_id: str
    max_fee: str
    max_custom_fees: List[Any]
    memo_base64: str
    name: str
    nft_transfers: List[Any]
    node: str
    nonce: int
    parent_consensus_timestamp: Optional[str]
    result: str
    scheduled: bool
    staking_reward_transfers: List[Any]
    token_transfers: List[Any]
    transaction_hash: str
    transaction_id: str
    transfers: List[TransferData]
    valid_duration_seconds: str
    valid_start_timestamp: str


class TransactionDetailsResponse(TypedDict):
    transactions: List[TransactionData]


class ScheduledTransactionSignature(TypedDict):
    consensus_timestamp: str
    public_key_prefix: str
    signature: str
    type: str


class ScheduledTransactionDetailsResponse(TypedDict):
    admin_key: Optional[Dict[str, Any]]
    deleted: bool
    consensus_timestamp: str
    creator_account_id: str
    executed_timestamp: Optional[str]
    expiration_time: Optional[str]
    memo: str
    payer_account_id: str
    schedule_id: str
    signatures: List[ScheduledTransactionSignature]
    transaction_body: str
    wait_for_expiry: bool
