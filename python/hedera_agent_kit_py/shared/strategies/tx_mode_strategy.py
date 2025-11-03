"""Transaction execution strategies based on agent mode.

This module defines a strategy interface and implementations that determine how
transactions are handled (executed on-chain or returned as bytes) according to
`Context.mode`. It also provides a `handle_transaction` helper.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pprint import pprint
from typing import Any, Callable, Optional, Dict

from hiero_sdk_python import (
    Client,
    AccountId,
    TransactionId,
    TransactionReceipt, ResponseCode,
)
from hiero_sdk_python.hapi.services.response_code_pb2 import ResponseCodeEnum
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import AgentMode, Context
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
    ReturnBytesToolResponse,
    ToolResponse,
)

class HederaTransactionError(Exception):
    """Raised when a Hedera transaction fails prechecking or execution."""
    pass


class TxModeStrategy(ABC):
    """Abstract strategy describing how to handle a built transaction.

    Concrete strategies decide whether to execute the transaction on-chain or
    serialize it for external signing/broadcasting (return bytes mode).
    """

    @abstractmethod
    async def handle(
        self,
        tx: Transaction,
        client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> ToolResponse:
        """Handle the transaction according to the strategy.

        Args:
            tx: The prepared transaction to handle.
            client: Hedera client used for execution where applicable.
            context: Runtime context that may influence handling mode.
            post_process: Optional callback to transform the raw response into a
                human-readable message.

        Returns:
            A `ToolResponse` reflecting the chosen handling outcome.
        """
        pass


class ExecuteStrategy(TxModeStrategy):
    def default_post_process(self, response: RawTransactionResponse) -> str:
        """Default post-processing: pretty-print the raw response as JSON.

        Args:
            response: The raw transaction response produced after execution.

        Returns:
            A JSON-formatted string with indentation.
        """
        import json

        return json.dumps(response.to_dict(), indent=2)

    async def handle(
            self,
            tx: Transaction,
            client: Client,
            context: Context,
            post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> ExecutedTransactionToolResponse:
        """Execute the transaction and construct an executed response.

        Args:
            tx: The transaction to execute.
            client: Hedera client used to submit the transaction.
            context: Runtime context (unused for direct execution).
            post_process: Optional callback to convert the raw response to text.

        Returns:
            An `ExecutedTransactionToolResponse` with raw fields and a message.
        """
        post_process = post_process or self.default_post_process
        receipt: TransactionReceipt = tx.execute(client)

        # Create a raw response object
        raw_transaction_response = RawTransactionResponse(
            status=ResponseCode(receipt.status).name,
            account_id=getattr(receipt, "account_id", None),
            token_id=getattr(receipt, "token_id", None),
            transaction_id=getattr(receipt, "transaction_id", None),
            topic_id=getattr(receipt, "topic_id", None),
            schedule_id=getattr(receipt, "schedule_id", None),
        )

        # Check for failure
        if receipt.status != ResponseCodeEnum.SUCCESS:
            raise HederaTransactionError(
                f"Transaction failed with status: {ResponseCode(receipt.status).name}. Transaction Id: {receipt.transaction_id}"
            )

        # Normal success path
        return ExecutedTransactionToolResponse(
            raw=raw_transaction_response,
            human_message=post_process(raw_transaction_response),
        )


class ReturnBytesStrategy(TxModeStrategy):
    """Strategy that returns a byte representation instead of executing.

    Note:
        The current SDK lacks `freeze()` and `to_bytes()`; a placeholder is
        returned until those APIs are available.
    """

    async def handle(
        self,
        tx: Transaction,
        _client: Client,
        context: Context,
        post_process: Optional[Callable[[RawTransactionResponse], Any]] = None,
    ) -> ReturnBytesToolResponse:
        """Prepare a transaction for external signing by returning bytes.

        Args:
            tx: The transaction to prepare.
            _client: Unused for this mode.
            context: Runtime context containing the required `account_id`.
            post_process: Unused for this mode.

        Returns:
            A `ReturnBytesToolResponse` containing the byte payload.

        Raises:
            ValueError: If `context.account_id` is missing.
        """
        if not context.account_id:
            raise ValueError("Context account_id is required for RETURN_BYTES mode")
        tx_id = TransactionId.generate(AccountId.from_string(context.account_id))
        # tx.set_transaction_id(tx_id).freeze() # FIXME: Transaction.freeze() is not yet implemented in the SDK
        # return {"bytes": tx.to_bytes()} FIXME: Transaction.to_bytes() is not yet implemented in the SDK
        return ReturnBytesToolResponse(
            bytes_data=b"bytes",
            human_message=f"Transaction bytes: <HERE PASS SOME BYTES>",
        )  # temporary placeholder


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
