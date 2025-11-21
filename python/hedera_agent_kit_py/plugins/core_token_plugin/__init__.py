from hedera_agent_kit_py.plugins.core_token_plugin.dissociate_token import (
    DissociateTokenTool,
    DISSOCIATE_TOKEN_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the HTS service",
    tools=lambda context: [
        DissociateTokenTool(context),
    ],
)

core_token_plugin_tool_names = {"DISSOCIATE_TOKEN_TOOL": DISSOCIATE_TOKEN_TOOL}

__all__ = [
    "DissociateTokenTool",
    "core_token_plugin",
    "core_token_plugin_tool_names",
]
