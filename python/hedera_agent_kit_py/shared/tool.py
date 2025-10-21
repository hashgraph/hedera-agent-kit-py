from abc import ABC, abstractmethod
from typing import Any
from hiero_sdk_python import Client
from .configuration import Context


class Tool(ABC):
    """
    Abstract base class representing a Tool definition.
    """

    method: str
    name: str
    description: str
    parameters: Any # TODO: define a type for this. This depends on the langchain implementation!!

    @abstractmethod
    async def execute(self, client: Client, context: Context, params: Any) -> Any:
        """
        Execute the tool’s main logic.
        Must be implemented by all subclasses.
        """
        pass
