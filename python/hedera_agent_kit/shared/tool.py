"""Abstract tool interface for defining executable Agent Kit tools.

This module defines the base `Tool` class that all concrete tools must extend.
Each tool exposes a coroutine `execute` method that performs the tool's action
using a Hedera `Client`, the runtime `Context`, and validated parameters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type, Callable, Union, Dict, Optional

from hiero_sdk_python import Client
from pydantic import BaseModel

from .configuration import Context
from .models import ToolResponse

ParserOutput = Dict[str, Union[Any, str]]


class Tool(ABC):
    """
    Abstract base class representing a Tool definition.

    Attributes:
        method (str):
            A unique identifier for the tool's operation, typically in snake_case
            (e.g., "create_account", "transfer_hbar"). Used internally to identify
            the tool within the Agent Kit.

        name (str):
            A human-readable name for the tool (e.g., "Create Account Tool").
            This is displayed to users and used by LangChain for tool identification.

        description (str):
            A detailed description of what the tool does. This is crucial for LLM
            agents to understand when and how to use the tool. Should include:
            - What the tool accomplishes
            - When it should be used
            - Any important constraints or requirements

        parameters (Type[BaseModel]):
            A Pydantic BaseModel subclass defining the tool's input parameters.
            This schema is used for:
            - Input validation before execution
            - Generating JSON schema for LLM function calling
            - Type-safe parameter access within the execute method

        outputParser (Optional[Callable[[str], ParserOutput]]):
            An optional function for parsing the tool's stringified JSON output
            into a structured format. **Only applicable for LangChain v1 integration**.

            The parser receives the raw JSON string output from the tool and returns
            a dictionary with 'raw' (structured data) and 'humanMessage' (user-friendly
            description) keys. This enables:
            - Extracting structured data from tool responses for further processing
            - Providing human-readable summaries for the LLM context

            **Default Implementations:**
            If not specified, tools can use the default parsers from
            `hedera_agent_kit.shared.utils.default_tool_output_parsing`:

            - `transaction_tool_output_parser`: For transaction tools that return
              ExecutedTransactionToolResponse or ReturnBytesToolResponse. Handles
              RETURN_BYTES mode, EXECUTE_TRANSACTION mode, and ERROR mode.

            - `untyped_query_output_parser`: A flexible parser for both transaction
              and query tools. Handles flat structures with 'human_message' fields.

            **Custom Implementations:**
            Hedera plugins may define custom parsers for specialized output formats.
            The parser must conform to the signature: `Callable[[str], ParserOutput]`
            where `ParserOutput = Dict[str, Union[Any, str]]`.
    """

    method: str
    name: str
    description: str
    parameters: Type[BaseModel]
    outputParser: Optional[Callable[[str], ParserOutput]] = None

    @abstractmethod
    async def execute(
        self, client: Client, context: Context, params: Any
    ) -> ToolResponse:
        """
        Execute the tool’s main logic.
        Must be implemented by all subclasses.
        """
        pass
