from abc import ABC, abstractmethod
from typing import Any, Type
from hiero_sdk_python import Client
from pydantic import BaseModel

from .configuration import Context


class Tool(ABC):
    """
    Abstract base class representing a Tool definition.
    """

    method: str
    name: str
    description: str
    parameters: Type[BaseModel]

    @abstractmethod
    async def execute(self, client: Client, context: Context, params: Any) -> Any:
        """
        Execute the tool’s main logic.
        Must be implemented by all subclasses.
        """
        pass
