import json
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from hedera_agent_kit_py import HederaAgentAPI
from hedera_agent_kit_py.shared.models import ToolResponse


class HederaAgentKitTool(BaseTool):
    """Custom LangChain tool that wraps Hedera Agent Kit API methods."""

    hedera_api: HederaAgentAPI = Field(exclude=True)
    method: str

    def __init__(
        self,
        hedera_api: HederaAgentAPI,
        method: str,
        schema: Type[BaseModel],
        description: str,
        name: str,
    ):
        super().__init__(
            name=name,
            description=description,
            args_schema=schema,
            hedera_api=hedera_api,
            method=method,
        )

    async def _run(self, **kwargs: Any) -> str:
        """Run the Hedera API method synchronously."""
        result: ToolResponse = await self.hedera_api.run(self.method, kwargs)
        return json.dumps(result.to_dict(), indent=2)

    async def _arun(self, **kwargs: Any) -> str:
        """Run the Hedera API method asynchronously (optional)."""
        result: ToolResponse = await self.hedera_api.run(self.method, kwargs)
        return json.dumps(result.to_dict(), indent=2)
