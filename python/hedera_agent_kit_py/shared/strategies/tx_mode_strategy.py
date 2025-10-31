from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict

from hiero_sdk_python import (
    Client,
    AccountId,
    TransactionId,
    TransactionReceipt,
)
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import AgentMode, Context
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
    ReturnBytesToolResponse,
    ToolResponse,
)


class TxModeStrategy(ABC):
    @abstractmethod
    async def handle(
        self,
        tx: Transaction,
        client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> ToolResponse:
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
    ) -> ExecutedTransactionToolResponse:
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
        return ExecutedTransactionToolResponse(
            raw=raw_transaction_response,
            human_message=post_process(raw_transaction_response),
        )


class ReturnBytesStrategy(TxModeStrategy):
    async def handle(
        self,
        tx: Transaction,
        _client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> ReturnBytesToolResponse:
        if not context.account_id:
            raise ValueError("Context account_id is required for RETURN_BYTES mode")
        tx_id = TransactionId.generate(AccountId.from_string(context.account_id))
        # tx.set_transaction_id(tx_id).freeze() # FIXME: Transaction.freeze() is not yet implemented in the SDK
        # return {"bytes": tx.to_bytes()} FIXME: Transaction.to_bytes() is not yet implemented in the SDK
        return ReturnBytesToolResponse(bytes_data=b"bytes")  # temporary placeholder


def get_strategy_from_context(context: Context) -> TxModeStrategy:
    if context.mode == AgentMode.RETURN_BYTES:
        return ReturnBytesStrategy()
    return ExecuteStrategy()


async def handle_transaction(
    tx: Transaction,
    client: Client,
    context: Context,
    post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
) -> ToolResponse:
    strategy = get_strategy_from_context(context)
    return await strategy.handle(tx, client, context, post_process)
