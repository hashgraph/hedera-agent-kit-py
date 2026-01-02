"""ADK tool factory for generating Python functions from Hedera Agent Kit tools.

This module provides utilities to transform Hedera tools into async Python functions
that Google ADK can automatically wrap as FunctionTools.
"""

from __future__ import annotations


from typing import Any, Callable, Coroutine, Dict, get_type_hints

from pydantic import BaseModel

from hedera_agent_kit import HederaAgentAPI
from hedera_agent_kit.shared import Tool
from hedera_agent_kit.shared.models import ToolResponse


def create_adk_tool_function(
    hedera_api: HederaAgentAPI,
    tool: Tool,
) -> Callable[..., Coroutine[Any, Any, Dict[str, Any]]]:
    """Create an async function from a Hedera tool for use with Google ADK.

    The generated function:
    - Uses the tool's method name as the function name
    - Uses the tool's description as the docstring
    - Extracts parameter types from the Pydantic schema
    - Returns results as a dictionary

    Args:
        hedera_api: A configured HederaAgentAPI instance.
        tool: The Hedera tool to wrap.

    Returns:
        An async function compatible with Google ADK's FunctionTool.
    """

    # Build parameter docstring from Pydantic schema
    schema: type[BaseModel] = tool.parameters
    param_docs = _build_param_docstring(schema)

    # Create the docstring
    docstring = f"{tool.description}\n\nArgs:\n{param_docs}"

    async def tool_function(**kwargs: Any) -> Dict[str, Any]:
        """Dynamically generated ADK tool function."""
        result: ToolResponse = await hedera_api.run(tool.method, kwargs)
        return result.to_dict()

    # Set function metadata for ADK introspection
    tool_function.__name__ = tool.method
    tool_function.__qualname__ = tool.method
    tool_function.__doc__ = docstring

    # Create proper annotations from Pydantic schema
    tool_function.__annotations__ = _extract_annotations(schema)
    tool_function.__annotations__["return"] = Dict[str, Any]

    return tool_function


def _build_param_docstring(schema: type[BaseModel]) -> str:
    """Build parameter documentation from a Pydantic schema.

    Args:
        schema: Pydantic model class defining the parameters.

    Returns:
        A formatted string with parameter descriptions.
    """
    lines = []
    for field_name, field_info in schema.model_fields.items():
        field_type = _get_field_type_name(schema, field_name)
        description = field_info.description or "No description provided."
        lines.append(f"    {field_name} ({field_type}): {description}")
    return "\n".join(lines) if lines else "    None"


def _get_field_type_name(schema: type[BaseModel], field_name: str) -> str:
    """Get a human-readable type name for a field.

    Args:
        schema: Pydantic model class.
        field_name: Name of the field.

    Returns:
        String representation of the field type.
    """
    try:
        hints = get_type_hints(schema)
        if field_name in hints:
            type_hint = hints[field_name]
            if hasattr(type_hint, "__name__"):
                return type_hint.__name__
            return str(type_hint)
    except Exception:
        pass
    return "Any"


def _extract_annotations(schema: type[BaseModel]) -> Dict[str, Any]:
    """Extract type annotations from a Pydantic schema.

    Args:
        schema: Pydantic model class defining the parameters.

    Returns:
        Dictionary mapping parameter names to their types.
    """
    annotations = {}
    try:
        hints = get_type_hints(schema)
        for field_name in schema.model_fields.keys():
            if field_name in hints:
                annotations[field_name] = hints[field_name]
            else:
                annotations[field_name] = Any
    except Exception:
        # Fallback to Any if type extraction fails
        for field_name in schema.model_fields.keys():
            annotations[field_name] = Any
    return annotations
