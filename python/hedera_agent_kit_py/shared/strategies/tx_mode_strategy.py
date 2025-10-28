from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict

from hiero_sdk_python import (
    Client,
    AccountId,
    TransactionId,
    TokenId,
    TopicId,
    TransactionReceipt,
)
from hiero_sdk_python.schedule.schedule_id import ScheduleId
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import AgentMode, Context


class RawTransactionResponse:
    def __init__(
        self,
        status: str,
        account_id: Optional[AccountId],
        token_id: Optional[TokenId],
        transaction_id: str,
        topic_id: Optional[TopicId],
        schedule_id: Optional[ScheduleId],
    ):
        self.status = status
        self.account_id = account_id
        self.token_id = token_id
        self.transaction_id = transaction_id
        self.topic_id = topic_id
        self.schedule_id = schedule_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": str(self.status),
            "accountId": str(self.account_id),
            "tokenId": str(self.token_id),
            "transactionId": str(self.transaction_id),
            "topicId": str(self.topic_id),
            "scheduleId": str(self.schedule_id),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RawTransactionResponse:
        return cls(
            status=data.get("status"),
            account_id=AccountId.from_string(data["accountId"]) if data.get("accountId") and data["accountId"] != "None" else None,
            token_id=TokenId.from_string(data["tokenId"]) if data.get("tokenId") and data["tokenId"] != "None" else None,
            transaction_id=data.get("transactionId"),
            topic_id=TopicId.from_string(data["topicId"]) if data.get("topicId") and data["topicId"] != "None" else None,
            schedule_id=ScheduleId.from_string(data["scheduleId"]) if data.get("scheduleId") and data["scheduleId"] != "None" else None,
        )


class TxModeStrategy(ABC):
    @abstractmethod
    async def handle(
        self,
        tx: Transaction,
        client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> Any:
        pass


class ExecuteStrategy(TxModeStrategy):
    def default_post_process(self, response: RawTransactionResponse) -> str:
        import json

        return json.dumps(response.to_dict(), indent=2)

    async def handle(
        self,
        tx: Transaction,
        client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> Dict[str, Any]:
        post_process = post_process or self.default_post_process
        receipt: TransactionReceipt = tx.execute(client)

        raw_transaction_response = RawTransactionResponse(
            status=str(receipt.status),
            account_id=getattr(receipt, "account_id", None),
            token_id=getattr(receipt, "token_id", None),
            transaction_id=getattr(receipt, "transaction_id", None),
            topic_id=getattr(receipt, "topic_id", None),
            schedule_id=getattr(receipt, "schedule_id", None),
        )

        return {
            "raw": raw_transaction_response.to_dict(), # python cannot serialize the object
            "humanMessage": post_process(raw_transaction_response),
        }


class ReturnBytesStrategy(TxModeStrategy):
    async def handle(
        self,
        tx: Transaction,
        _client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> Dict[str, bytes]:
        if not context.account_id:
            raise ValueError("Context account_id is required for RETURN_BYTES mode")
        tx_id = TransactionId.generate(AccountId.from_string(context.account_id))
        # tx.set_transaction_id(tx_id).freeze() FIXME: Transaction.freeze() is not yet implemented in the SDK
        # return {"bytes": tx.to_bytes()} FIXME: Transaction.to_bytes() is not yet implemented in the SDK
        return {
            "bytes": b"bytes"
        }  # TODO: Remove this placeholder once the above methods are implemented


def get_strategy_from_context(context: Context) -> TxModeStrategy:
    if context.mode == AgentMode.RETURN_BYTES:
        return ReturnBytesStrategy()
    return ExecuteStrategy()


async def handle_transaction(
    tx: Transaction,
    client: Client,
    context: Context,
    post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
) -> Any:
    strategy = get_strategy_from_context(context)
    return await strategy.handle(tx, client, context, post_process)
