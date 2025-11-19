from dataclasses import dataclass
from typing import List, Dict, Callable, Any, Union
from langchain_core.messages import BaseMessage
from hedera_agent_kit_py.langchain import HederaAgentKitTool

ParsingFunction = Callable[[str], Any]


@dataclass
class AgentResponse:
    """This data class defines the shape of the object response from the agent."""

    messages: List[BaseMessage]


@dataclass
class ParsedToolData:
    """Structure for the data returned after parsing a ToolMessage."""

    toolName: str
    toolCallId: str
    parsedData: Any


@dataclass
class ToolRequest:
    """Structure for a tool call request found in an AIMessage."""

    name: str
    args: Dict[str, Any]
    tool_call_id: str


class ResponseParserService:
    """
    Parses new ToolMessages in an AgentResponse (or dict) using a set of registered tools
    and their parsing functions.
    """

    processedMessageIds: set[str]
    tools: List[HederaAgentKitTool]
    parsingMap: Dict[str, ParsingFunction]

    def __init__(self, tools: List[HederaAgentKitTool]):
        self.tools = tools
        self.processedMessageIds = set()
        self.parsingMap = self._create_parsing_map()

    def _create_parsing_map(self) -> Dict[str, ParsingFunction]:
        """Creates a map of tool names to their respective parsing functions."""
        parsing_map = {}
        for tool in self.tools:
            # Safely check for the parsing function
            parsing_func = getattr(tool, "responseParsingFunction", None)
            if parsing_func:
                parsing_map[tool.name] = parsing_func
            else:
                print(f"Tool: {tool.name}, does not define a responseParsingFunction!")
        return parsing_map

    def _get_attr(self, item: Any, key: str, default: Any = None) -> Any:
        """
        Helper to safely get an attribute from either a Dictionary or an Object.
        """
        if isinstance(item, dict):
            return item.get(key, default)
        # Handle BaseMessage properties
        return getattr(item, key, default)

    def _is_tool_message(self, message: Union[BaseMessage, Dict[str, Any]]) -> bool:
        """
        Type guard to check if a message is a ToolMessage (or dict representation of one).
        """
        msg_type = self._get_attr(message, "type")
        tool_call_id = self._get_attr(message, "tool_call_id")
        name = self._get_attr(message, "name")

        return msg_type == "tool" and tool_call_id is not None and name is not None

    def _extract_messages_list(
        self, response: Union[AgentResponse, Dict[str, Any]]
    ) -> List[Any]:
        """Safely extracts the list of messages from the response container."""
        if isinstance(response, dict):
            return response.get("messages", [])
        elif hasattr(response, "messages"):
            return response.messages
        return []

    def get_new_tool_requests(
        self, response: Union[AgentResponse, Dict[str, Any]]
    ) -> List[ToolRequest]:
        """
        Extracts tool calls requested by the AI (found in AIMessages).
        This is typically the step that precedes tool execution.
        """
        all_requests: List[ToolRequest] = []
        messages_list = self._extract_messages_list(response)

        for message in messages_list:
            message_id = self._get_attr(message, "id")
            if not message_id or message_id in self.processedMessageIds:
                continue

            msg_type = self._get_attr(message, "type")
            tool_calls = self._get_attr(message, "tool_calls")

            # Check for new tool requests in an AIMessage
            if msg_type == "ai" and tool_calls and isinstance(tool_calls, list):
                # Mark the AIMessage as processed
                self.processedMessageIds.add(message_id)

                for call in tool_calls:
                    # 'call' is expected to be a dict: {'name': ..., 'args': ..., 'id': ...}
                    if isinstance(call, dict) and "name" in call and "id" in call:
                        all_requests.append(
                            ToolRequest(
                                name=call.get("name", ""),
                                args=call.get("args", {}),
                                tool_call_id=call.get("id", ""),
                            )
                        )

        return all_requests

    def parse_new_tool_messages(
        self, response: Union[AgentResponse, Dict[str, Any]]
    ) -> List[ParsedToolData]:
        """
        Parses all new ToolMessages (tool results) in the response.
        """
        all_parsed_data: List[ParsedToolData] = []
        messages_list = self._extract_messages_list(response)

        for message in messages_list:
            message_id = self._get_attr(message, "id")

            if not message_id:
                continue

            # Ensure we don't process messages we've already marked (e.g., in get_new_tool_requests)
            if message_id in self.processedMessageIds:
                continue

            # CRITICAL FIX: Mark any AIMessage containing tool_calls as processed,
            # even if we only care about the ToolMessage *results* here.
            # This prevents us from endlessly processing the same message ID.
            if self._get_attr(message, "type") == "ai" and self._get_attr(
                message, "tool_calls"
            ):
                self.processedMessageIds.add(message_id)
                continue

            if self._is_tool_message(message):
                # Extract fields using the safe helper
                tool_name = self._get_attr(message, "name")
                tool_call_id = self._get_attr(message, "tool_call_id")
                content = self._get_attr(message, "content")

                parsing_function = self.parsingMap.get(tool_name)

                if parsing_function:
                    self.processedMessageIds.add(message_id)

                    try:
                        parsed_data = parsing_function(content)

                        all_parsed_data.append(
                            ParsedToolData(
                                toolName=tool_name,
                                toolCallId=tool_call_id,
                                parsedData=parsed_data,
                            )
                        )
                    except Exception as error:
                        print(f"Failed to parse content for tool {tool_name}: {error}")
                else:
                    print(f"No parsing function found for tool: {tool_name}")

        return all_parsed_data
