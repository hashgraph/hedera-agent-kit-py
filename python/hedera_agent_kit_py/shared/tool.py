"""Abstract tool interface for defining executable Agent Kit tools.

This module defines the base `Tool` class that all concrete tools must extend.
Each tool exposes a coroutine `execute` method that performs the tool's action
using a Hedera `Client`, the runtime `Context`, and validated parameters.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type

from hiero_sdk_python import Client
from pydantic import BaseModel

from .configuration import Context
from .models import ToolResponse


class Tool(ABC):
    """
    Abstract base class representing a Tool definition.
    """

    method: str
    name: str
    description: str
    parameters: Type[BaseModel]

    @abstractmethod
    async def execute(self, client: Client, context: Context, params: Any) -> ToolResponse:
        """
        Execute the tool’s main logic.
        Must be implemented by all subclasses.
        """
        pass
