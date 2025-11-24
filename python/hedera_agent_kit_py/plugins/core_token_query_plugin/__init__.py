from hedera_agent_kit_py.plugins.core_token_query_plugin.get_token_info_query import (
    GetTokenInfoQueryTool,
    GET_TOKEN_INFO_QUERY_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin

core_token_query_plugin = Plugin(
    name="core-token-query-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Token Service (HTS) queries",
    tools=lambda context: [
        GetTokenInfoQueryTool(context),
    ],
)

core_token_query_plugin_tool_names = {
    "GET_TOKEN_INFO_QUERY_TOOL": GET_TOKEN_INFO_QUERY_TOOL
}

__all__ = [
    "core_token_query_plugin",
    "core_token_query_plugin_tool_names",
    "GetTokenInfoQueryTool",
]
