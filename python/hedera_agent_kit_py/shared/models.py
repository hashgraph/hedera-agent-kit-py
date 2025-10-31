from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from hiero_sdk_python import AccountId, TokenId, TopicId, TransactionId
from hiero_sdk_python.schedule.schedule_id import ScheduleId


class ToolResponse(ABC):
    """Base class for all transaction tool responses."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolResponse:
        """Deserialize from a dictionary."""
        pass


@dataclass
class RawTransactionResponse:
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
            "error": str(self.error) if self.error else None,
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
            transaction_id=TransactionId.from_string(data.get("transaction_id")),
            topic_id=(
                TopicId.from_string(data["topic_id"]) if data.get("topic_id") else None
            ),
            schedule_id=(
                ScheduleId.from_string(data["schedule_id"])
                if data.get("schedule_id")
                else None
            ),
            error=data.get("error", ""),
        )


@dataclass
class ExecutedTransactionToolResponse(ToolResponse):
    """A tool response representing a fully executed transaction."""

    raw: RawTransactionResponse
    human_message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "executed_transaction",
            "raw": self.raw.to_dict(),
            "human_message": self.human_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutedTransactionToolResponse:
        return cls(
            raw=RawTransactionResponse.from_dict(data["raw"]),
            human_message=data.get("human_message", ""),
        )


@dataclass
class ReturnBytesToolResponse(ToolResponse):
    """A tool response representing a transaction serialized to bytes."""

    bytes_data: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "return_bytes",
            "bytes_data": self.bytes_data.hex(),  # hex for JSON safety
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReturnBytesToolResponse:
        return cls(bytes_data=bytes.fromhex(data["bytes_data"]))
