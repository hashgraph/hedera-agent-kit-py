"""Core consensus plugin for Hedera Agent Kit."""

from .create_topic import (
    CreateTopicTool,
    CREATE_TOPIC_TOOL,
)
from .delete_topic import DELETE_TOPIC_TOOL, DeleteTopicTool
from hedera_agent_kit_py.plugins.core_consensus_plugin.submit_topic_message import (
    SubmitTopicMessageTool,
    SUBMIT_TOPIC_MESSAGE_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin
from .update_topic import UpdateTopicTool, UPDATE_TOPIC_TOOL

core_consensus_plugin = Plugin(
    name="core-consensus-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Consensus Service",
    tools=lambda context: [
        CreateTopicTool(context),
        DeleteTopicTool(context),
        SubmitTopicMessageTool(context),
        UpdateTopicTool(context),
    ],
)

core_consensus_plugin_tool_names = {
    "CREATE_TOPIC_TOOL": CREATE_TOPIC_TOOL,
    "SUBMIT_TOPIC_MESSAGE_TOOL": SUBMIT_TOPIC_MESSAGE_TOOL,
    "DELETE_TOPIC_TOOL": DELETE_TOPIC_TOOL,
    "UPDATE_TOPIC_TOOL": UPDATE_TOPIC_TOOL,
}

__all__ = [
    "core_consensus_plugin",
    "core_consensus_plugin_tool_names",
    "CreateTopicTool",
    "DeleteTopicTool",
    "SubmitTopicMessageTool",
    "UpdateTopicTool",
]
