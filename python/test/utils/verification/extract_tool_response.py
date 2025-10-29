import json
from typing import Any, Dict
from hedera_agent_kit_py.shared.strategies import RawTransactionResponse

def extract_tool_response(response: Dict[str, Any], tool_name: str) -> RawTransactionResponse:
    """
    Extracts and parses a tool's response from an agent executor output.

    Works with LangChain-style messages (HumanMessage, AIMessage, ToolMessage).

    Args:
        response (Dict[str, Any]): The raw agent_executor response.
        tool_name (str): The name of the tool (e.g., "transfer_hbar_tool").

    Returns:
        RawTransactionResponse: Parsed domain object containing the tool's result.

    Raises:
        AssertionError: If no matching tool message or valid content is found.
        ValueError: If JSON decoding fails.
    """
    messages = response.get("messages", [])
    assert messages, "Response contains no messages"

    # Extract ToolMessage by name
    tool_messages = []
    for m in messages:
        # Check if the object has the attribute 'name' and it matches our tool
        if hasattr(m, "name") and getattr(m, "name") == tool_name:
            tool_messages.append(m)

    assert tool_messages, f"No tool message found for '{tool_name}' in response"

    tool_message = tool_messages[0]
    tool_content = getattr(tool_message, "content", None)
    assert tool_content, f"Tool message for '{tool_name}' has no content"

    # Parse JSON safely
    try:
        parsed = json.loads(tool_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse tool message content as JSON: {e}\nContent: {tool_content}")

    # Expecting structure like {"raw": {...}, "human_message": "..."}
    raw_section = parsed.get("raw")
    assert raw_section, f"Missing 'raw' key in tool message for '{tool_name}'"

    return RawTransactionResponse.from_dict(raw_section)
