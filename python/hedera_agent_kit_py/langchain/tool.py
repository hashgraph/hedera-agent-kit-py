# ./langchain/tool.py

from typing import Any, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel


class HederaAgentKitTool(StructuredTool):
    def __init__(
        self,
        hedera_api: Any,
        method: str,
        description: str,
        schema: Type[BaseModel],
    ):
        # Keep reference to API and metadata
        self.hedera_api = hedera_api
        self.method = method
        self.schema = schema
        self.description = description

        # Initialize the StructuredTool
        super().__init__(
            name=method,
            description=description,
            args_schema=schema,
            func=self._run,  # main callable
        )

    def  _run(self, **kwargs) -> Any:
        return self.hedera_api.run(self.method, kwargs)
