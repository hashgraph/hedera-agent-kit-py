from .associate_token import (
    AssociateTokenTool,
    ASSOCIATE_TOKEN_TOOL,
)
from ... import Plugin

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Token Service",
    tools=lambda context: [
        AssociateTokenTool(context),
    ],
)

core_token_plugin_tool_names = {
    "ASSOCIATE_TOKEN_TOOL": ASSOCIATE_TOKEN_TOOL,
}


__all__ = [
    "AssociateTokenTool",
    "ASSOCIATE_TOKEN_TOOL",
    core_token_plugin,
    core_token_plugin_tool_names,
]
