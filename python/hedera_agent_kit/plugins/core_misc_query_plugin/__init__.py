from hedera_agent_kit.plugins.core_misc_query_plugin.get_exchange_rate_tool import (
    GET_EXCHANGE_RATE_TOOL,
    GetExchangeRateTool,
)
from hedera_agent_kit.shared.plugin import Plugin

core_misc_query_plugin = Plugin(
    name="core-misc-query-plugin",
    version="1.0.0",
    description="A plugin for the miscellaneous queries",
    tools=lambda context: [
        GetExchangeRateTool(context),
    ],
)

core_misc_query_plugin_tool_names = {"GET_EXCHANGE_RATE_TOOL": GET_EXCHANGE_RATE_TOOL}

__all__ = [
    "GetExchangeRateTool",
    "core_misc_query_plugin",
    "core_misc_query_plugin_tool_names",
]
