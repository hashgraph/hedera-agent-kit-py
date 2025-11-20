"""Utilities for querying Hedera topic information via the Agent Kit.

This module exposes:
- get_topic_info_query_prompt: Generate a prompt/description for the get topic info query tool.
- get_topic_info_query: Execute a topic info query.
- GetTopicInfoQueryTool: Tool wrapper exposing the topic info query operation to the runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import TopicInfo
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types.common import (
    MirrornodeKeyInfo,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas.consensus_schema import (
    GetTopicInfoParameters,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def get_topic_info_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get topic info query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default network information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the information for a given Hedera topic (HCS).

Parameters:
- topic_id (str): The topic ID to query for.
{usage_instructions}
"""


def format_key(key: Optional[MirrornodeKeyInfo]) -> str:
    """Format a mirrornode key info object for display.

    Args:
        key: The key info object from the mirrornode API.

    Returns:
        A formatted string representation of the key.
    """
    if not key:
        return "Not Set"
    if key.get("_type"):
        return key.get("key", "Present")
    return "Present"


def format_timestamp(ts: Optional[str]) -> str:
    """Format a timestamp string for display.

    Args:
        ts: The timestamp string in format "seconds.nanoseconds".

    Returns:
        An ISO 8601 formatted datetime string, or "N/A" if input is None.
    """
    if not ts:
        return "N/A"
    seconds = ts.split(".")[0]
    date = datetime.fromtimestamp(int(seconds))
    return date.isoformat()


def post_process(topic: TopicInfo) -> str:
    """Produce a human-readable summary for a topic info query result.

    Args:
        topic: The topic info returned by the mirrornode API.

    Returns:
        A formatted markdown message describing the topic details.
    """
    topic_id = topic.get("topic_id", "N/A")
    memo = topic.get("memo", "N/A")
    deleted = "Yes" if topic.get("deleted") else "No"
    sequence_number = topic.get("sequence_number")
    sequence_number_str = str(sequence_number) if sequence_number is not None else "N/A"
    created_timestamp = format_timestamp(topic.get("created_timestamp"))
    auto_renew_account = topic.get("auto_renew_account", "N/A")
    auto_renew_period = topic.get("auto_renew_period")
    auto_renew_period_str = (
        str(auto_renew_period) if auto_renew_period is not None else "N/A"
    )
    admin_key = format_key(topic.get("admin_key"))
    submit_key = format_key(topic.get("submit_key"))

    return f"""Here are the details for topic **{topic_id}**:

- **Memo**: {memo}
- **Deleted**: {deleted}
- **Sequence Number**: {sequence_number_str}

**Timestamps**:
- Created: {created_timestamp}

**Entity IDs**:
- Auto Renew Account: {auto_renew_account}
- Auto Renew Period: {auto_renew_period_str}

**Keys**:
- Admin Key: {admin_key}
- Submit Key: {submit_key}
"""


async def get_topic_info_query(
    client: Client,
    context: Context,
    params: GetTopicInfoParameters,
) -> ToolResponse:
    """Execute a topic info query using the mirrornode service.

    Args:
        client: Hedera client used to determine network/ledger ID.
        context: Runtime context providing configuration and defaults.
        params: Query parameters containing the topic ID to query.

    Returns:
        A ToolResponse wrapping the raw topic info and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        parsed_params: GetTopicInfoParameters = (
            HederaParameterNormaliser.normalise_get_topic_info(params)
        )

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        topic_info: TopicInfo = await mirrornode_service.get_topic_info(
            parsed_params.topic_id
        )
        # Add the topic_id to the response if not present
        if "topic_id" not in topic_info:
            topic_info["topic_id"] = parsed_params.topic_id

        return ToolResponse(
            human_message=post_process(topic_info),
            extra={"topic_info": topic_info, "topic_id": parsed_params.topic_id},
        )

    except Exception as e:
        message: str = f"Failed to get topic info: {str(e)}"
        print("[get_topic_info_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_TOPIC_INFO_QUERY_TOOL: str = "get_topic_info_query_tool"


class GetTopicInfoQueryTool(Tool):
    """Tool wrapper that exposes the topic info query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_TOPIC_INFO_QUERY_TOOL
        self.name: str = "Get Topic Info"
        self.description: str = get_topic_info_query_prompt(context)
        self.parameters: type[GetTopicInfoParameters] = GetTopicInfoParameters
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: GetTopicInfoParameters
    ) -> ToolResponse:
        """Execute the topic info query using the provided client, context, and params.

        Args:
            client: Hedera client used to determine network/ledger ID.
            context: Runtime context providing configuration and defaults.
            params: Topic info query parameters accepted by this tool.

        Returns:
            The result of the topic info query as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await get_topic_info_query(client, context, params)
