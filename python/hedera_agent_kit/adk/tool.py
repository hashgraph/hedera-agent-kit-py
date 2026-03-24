"""ADK tool wrapper for exposing Hedera Agent Kit tools.

This module provides a HederaAdkTool class that subclasses Google ADK's BaseTool,
building a FunctionDeclaration directly from the Pydantic schema. This gives full
control over nested types, field descriptions, and required/optional fields — without
relying on ADK's function introspection heuristics.
"""

from __future__ import annotations

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel

from hedera_agent_kit import HederaAgentAPI
from hedera_agent_kit.shared import Tool
from hedera_agent_kit.shared.models import ToolResponse


class HederaAdkTool(BaseTool):
    """Google ADK BaseTool wrapper for a Hedera Agent Kit tool.

    Builds the FunctionDeclaration directly from the tool's Pydantic parameter
    schema, preserving:
    - Nested model structures (e.g. List[TransferHbarEntry])
    - Field descriptions from Field(description=...)
    - Required vs optional distinction
    - Recursive nesting (models inside models)
    """

    def __init__(self, hedera_api: HederaAgentAPI, tool: Tool) -> None:
        super().__init__(name=tool.method, description=tool.description)
        self._hedera_api = hedera_api
        self._tool = tool
        self._schema = tool.parameters
        self._declaration = _build_function_declaration(
            tool.method, tool.description, tool.parameters
        )

    # ADK calls this to get the FunctionDeclaration sent to Gemini
    def _get_declaration(self) -> genai_types.FunctionDeclaration:
        return genai_types.FunctionDeclaration(
            name=self._tool.method,
            description=self._tool.description,
            parameters_json_schema=self._schema.model_json_schema(),
        )

    async def run_async(
        self,
        *,
        args: Dict[str, Any],
        tool_context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the Hedera tool, coercing raw ADK args through Pydantic first."""
        # Coerce plain dicts / primitives from Gemini into validated Pydantic model
        validated: BaseModel = self._schema.model_validate(args)
        result: ToolResponse = await self._hedera_api.run(
            self._tool.method, validated.model_dump()
        )
        return result.to_dict()


# ---------------------------------------------------------------------------
# FunctionDeclaration builder
# ---------------------------------------------------------------------------


def _build_function_declaration(
    name: str,
    description: str,
    schema: Type[BaseModel],
) -> genai_types.FunctionDeclaration:
    """Build an ADK FunctionDeclaration from a Pydantic BaseModel schema."""
    parameters_schema = _pydantic_model_to_genai_schema(schema)
    return genai_types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=parameters_schema,
    )


def _pydantic_model_to_genai_schema(model: Type[BaseModel]) -> genai_types.Schema:
    """Recursively convert a Pydantic model to a genai OBJECT Schema.

    Walks the model's fields (including inherited ones from parent models),
    preserving descriptions and required/optional status.
    """
    properties: Dict[str, genai_types.Schema] = {}
    required: List[str] = []

    try:
        hints = get_type_hints(model)
    except Exception:
        hints = {}

    # model_fields includes inherited fields from parent BaseModel classes
    for field_name, field_info in model.model_fields.items():
        raw_type = hints.get(field_name, Any)
        field_schema = _python_type_to_genai_schema(
            raw_type,
            description=field_info.description,
        )
        properties[field_name] = field_schema

        # A field is required if it has no default and is not Optional
        if field_info.is_required():
            required.append(field_name)

    return genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties=properties,
        required=required if required else None,
    )


def _python_type_to_genai_schema(
    tp: Any,
    description: Optional[str] = None,
) -> genai_types.Schema:
    """Recursively map a Python / Pydantic type to a genai Schema node.

    Handles:
    - Primitives: str, int, float, bool
    - Optional[X]  (Union[X, None])
    - List[X]
    - Nested Pydantic BaseModel subclasses
    - Any / unknown -> STRING fallback
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # ------------------------------------------------------------------
    # Optional[X]  ->  unwrap and recurse (genai has no nullable wrapper)
    # ------------------------------------------------------------------
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_genai_schema(non_none[0], description=description)
        # True union of multiple types — fall back to STRING
        return genai_types.Schema(type=genai_types.Type.STRING, description=description)

    # ------------------------------------------------------------------
    # List[X]
    # ------------------------------------------------------------------
    if origin is list:
        item_type = args[0] if args else Any
        item_schema = _python_type_to_genai_schema(item_type)
        return genai_types.Schema(
            type=genai_types.Type.ARRAY,
            items=item_schema,
            description=description,
        )

    # ------------------------------------------------------------------
    # Nested Pydantic model  ->  recurse into OBJECT
    # ------------------------------------------------------------------
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        nested = _pydantic_model_to_genai_schema(tp)
        # Attach the field-level description to the outer OBJECT node
        if description:
            nested = genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties=nested.properties,
                required=nested.required,
                description=description,
            )
        return nested

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------
    primitive_map = {
        str: genai_types.Type.STRING,
        int: genai_types.Type.INTEGER,
        float: genai_types.Type.NUMBER,
        bool: genai_types.Type.BOOLEAN,
    }
    if tp in primitive_map:
        return genai_types.Schema(
            type=primitive_map[tp],
            description=description,
        )

    # Fallback — unknown / Any
    return genai_types.Schema(type=genai_types.Type.STRING, description=description)
