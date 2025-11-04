import json
from typing import Any, Dict, Union

from hedera_agent_kit_py.shared.models import (
    ReturnBytesToolResponse,
    ToolResponse,
    ExecutedTransactionToolResponse,
)


def extract_tool_response(
    response: Dict[str, Any], tool_name: str
) -> Union[ToolResponse, ReturnBytesToolResponse, ExecutedTransactionToolResponse]:
    """Extracts and parses a tool's response from an agent executor output."""
    messages = response.get("messages", [])
    assert messages, "Response contains no messages"

    # Find the ToolMessage that matches the tool name
    tool_message = next(
        (m for m in messages if getattr(m, "name", None) == tool_name), None
    )
    assert tool_message, f"No tool message found for '{tool_name}' in response"

    tool_content = getattr(tool_message, "content", None)
    assert tool_content, f"Tool message for '{tool_name}' has no content"

    # Parse content JSON
    try:
        parsed = json.loads(tool_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in tool message: {e}\nContent: {tool_content}")

    # Detect type
    response_type = parsed.get("type")
    if response_type == "executed_transaction":
        return ExecutedTransactionToolResponse.from_dict(parsed)
    elif response_type == "return_bytes":
        return ReturnBytesToolResponse.from_dict(parsed)
    else:
        return ToolResponse.from_dict(parsed)
