"""Common response models used by Hedera Agent Kit tools.

This module defines abstract and concrete response types that tools return,
including executed transaction results and a bytes-returning placeholder.
All models provide `to_dict`/`from_dict` helpers for JSON-friendly transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from hiero_sdk_python import AccountId, TokenId, TopicId, TransactionId
from hiero_sdk_python.schedule.schedule_id import ScheduleId


@dataclass(kw_only=True)
class ToolResponse:
    """Base class for all tool responses.

    Attributes:
        human_message: A human-readable description of the result.
        error: Optional error message if something went wrong.
    """

    human_message: str
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the base fields for all tool responses."""
        return {
            "human_message": self.human_message,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolResponse:
        """Deserialize base fields for a tool response."""
        return cls(
            human_message=data.get("human_message", ""),
            error=data.get("error"),
        )


@dataclass(kw_only=True)
class RawTransactionResponse:
    """Represents a raw transaction result from the Hedera network."""

    status: str
    account_id: Optional[AccountId] = None
    token_id: Optional[TokenId] = None
    transaction_id: Optional[TransactionId] = None
    topic_id: Optional[TopicId] = None
    schedule_id: Optional[ScheduleId] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "status": self.status,
            "account_id": str(self.account_id) if self.account_id else None,
            "token_id": str(self.token_id) if self.token_id else None,
            "transaction_id": str(self.transaction_id) if self.transaction_id else None,
            "topic_id": str(self.topic_id) if self.topic_id else None,
            "schedule_id": str(self.schedule_id) if self.schedule_id else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawTransactionResponse:
        """Deserialize from a dictionary."""
        return cls(
            status=data.get("status", ""),
            account_id=(
                AccountId.from_string(data["account_id"])
                if data.get("account_id")
                else None
            ),
            token_id=(
                TokenId.from_string(data["token_id"]) if data.get("token_id") else None
            ),
            transaction_id=(
                TransactionId.from_string(data["transaction_id"])
                if data.get("transaction_id")
                else None
            ),
            topic_id=(
                TopicId.from_string(data["topic_id"]) if data.get("topic_id") else None
            ),
            schedule_id=(
                ScheduleId.from_string(data["schedule_id"])
                if data.get("schedule_id")
                else None
            ),
            error=data.get("error"),
        )


@dataclass(kw_only=True)
class ExecutedTransactionToolResponse(ToolResponse):
    """A tool response representing a fully executed transaction."""

    raw: RawTransactionResponse

    def to_dict(self) -> dict[str, Any]:
        """Serialize the response to a dictionary suitable for JSON output."""
        data = super().to_dict()
        data.update(
            {
                "type": "executed_transaction",
                "raw": self.raw.to_dict(),
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutedTransactionToolResponse:
        """Reconstruct an `ExecutedTransactionToolResponse` from a dictionary."""
        return cls(
            raw=RawTransactionResponse.from_dict(data["raw"]),
            human_message=data.get("human_message", ""),
            error=data.get("error"),
        )


@dataclass(kw_only=True)
class ReturnBytesToolResponse(ToolResponse):
    """A tool response representing a transaction serialized to bytes."""

    bytes_data: bytes

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "type": "return_bytes",
                "bytes_data": self.bytes_data.hex(),  # hex for JSON safety
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReturnBytesToolResponse:
        return cls(
            bytes_data=bytes.fromhex(data["bytes_data"]),
            human_message=data.get("human_message", ""),
            error=data.get("error"),
        )
