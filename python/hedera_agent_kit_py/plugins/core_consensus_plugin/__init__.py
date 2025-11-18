"""Core consensus plugin for Hedera Agent Kit."""

from .create_topic import (
    CreateTopicTool,
    CREATE_TOPIC_TOOL,
)
from .delete_topic import DELETE_TOPIC_TOOL, DeleteTopicTool
from hedera_agent_kit_py.shared.plugin import Plugin

core_consensus_plugin = Plugin(
    name="core-consensus-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Consensus Service",
    tools=lambda context: [
        CreateTopicTool(context),
        DeleteTopicTool(context),
    ],
)

core_consensus_plugin_tool_names = {
    "CREATE_TOPIC_TOOL": CREATE_TOPIC_TOOL,
    "DELETE_TOPIC_TOOL": DELETE_TOPIC_TOOL,
}

__all__ = [
    "core_consensus_plugin",
    "core_consensus_plugin_tool_names",
    "CreateTopicTool",
    "DeleteTopicTool",
]
