from hedera_agent_kit.plugins.core_consensus_query_plugin.get_topic_info_query import (
    GetTopicInfoQueryTool,
    GET_TOPIC_INFO_QUERY_TOOL,
)
from hedera_agent_kit.shared.plugin import Plugin

core_consensus_query_plugin = Plugin(
    name="core-consensus-query-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Consensus Service (HCS)",
    tools=lambda context: [
        GetTopicInfoQueryTool(context),
    ],
)

core_consensus_query_plugin_tool_names = {
    "GET_TOPIC_INFO_QUERY_TOOL": GET_TOPIC_INFO_QUERY_TOOL
}

__all__ = [
    "core_consensus_query_plugin",
    "core_consensus_query_plugin_tool_names",
    "GetTopicInfoQueryTool",
]
