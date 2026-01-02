"""Utilities for querying Hedera topic messages via the Agent Kit.

This module exposes:
- get_topic_messages_query_prompt: Generate a prompt/description for the get topic messages query tool.
- get_topic_messages_query: Execute a topic messages query.
- GetTopicMessagesQueryTool: Tool wrapper exposing the topic messages query operation to the runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import (
    TopicMessagesQueryParams,
    TopicMessagesResponse,
)
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import TopicMessagesQueryParameters
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.tool import Tool


def get_topic_messages_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get topic messages query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.
    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""  
{context_snippet}  

This tool will return the messages for a given Hedera topic.  

Parameters:  
- topic_id (str, required): The topic ID to query  
- start_time (datetime, optional): The start datetime to query. If set, the messages will be returned after this datetime  
- end_time (datetime, optional): The end datetime to query. If set, the messages will be returned before this datetime  
- limit: (Optional) Max number of messages to return. Defaults to 100. Max value is 100.
{usage_instructions}  

Note: When limit is set, the most recent messages up to the limit will be returned within the specified time range.
"""


def post_process(messages: List[Dict[str, Any]], topic_id: str) -> str:
    """Produce a human-readable summary for a list of topic messages.

    Args:
        messages: List of message dictionaries returned by the mirrornode service (already decoded).
        topic_id: The topic ID that was queried.
    Returns:
         A formatted string displaying the messages."""
    if not messages:
        return f"No messages found for topic {topic_id}."

    messages_text_list = []
    for message in messages:
        content = message.get("message", "")
        consensus_timestamp = message.get("consensus_timestamp", "N/A")
        messages_text_list.append(
            f"{content} - posted at: {consensus_timestamp}\n"
        )

    messages_text = "".join(messages_text_list)

    return f"""Messages for topic {topic_id}:  
  --- Messages ---  {messages_text}  
  """

async def get_topic_messages_query(
    client: Client,
    context: Context,
    params: TopicMessagesQueryParameters,
) -> ToolResponse:
    """Execute a topic messages query using the mirrornode service.

    Args:
        client: Hedera client used to determine network/ledger ID.
        context: Runtime context providing configuration and defaults.
        params: Query parameters containing the topic ID and optional filters.
    Returns:
        A ToolResponse wrapping the raw messages and a human-friendly
        message indicating success or failure.
    """
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Prepare params for the service call (handling timestamp conversion)
        parsed_params: TopicMessagesQueryParams = (
            HederaParameterNormaliser.normalise_get_topic_messages(params)
        )

        result: TopicMessagesResponse = await mirrornode_service.get_topic_messages(
            parsed_params
        )

        topic_id = result.get("topic_id")
        messages_list = result.get("messages")

        return ToolResponse(
            human_message=post_process(messages_list, topic_id),
            extra={
                "topicId": topic_id,
                "messages": messages_list,
            },
        )

    except Exception as e:
        message: str = f"Failed to get topic messages: {str(e)}"
        print("[get_topic_messages_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_TOPIC_MESSAGES_QUERY_TOOL: str = "get_topic_messages_query_tool"


class GetTopicMessagesQueryTool(Tool):
    """Tool wrapper that exposes the topic messages query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_TOPIC_MESSAGES_QUERY_TOOL
        self.name: str = "Get Topic Messages"
        self.description: str = get_topic_messages_query_prompt(context)
        self.parameters: type[TopicMessagesQueryParameters] = (
            TopicMessagesQueryParameters
        )
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: TopicMessagesQueryParameters
    ) -> ToolResponse:
        """Execute the topic messages query using the provided client, context, and params.

        Args:
             client: Hedera client used to determine network/ledger ID.
             context: Runtime context providing configuration and defaults.
             params: Topic messages query parameters accepted by this tool.
        Returns:
            The result of the query as a ToolResponse."""
        return await get_topic_messages_query(client, context, params)
