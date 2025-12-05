"""Core Transaction Query Plugin.

This plugin provides tools for querying transaction records and details
from the Hedera network using the mirror node service.
"""

from hedera_agent_kit.shared.plugin import Plugin
from .get_transaction_record_query import (
    GetTransactionRecordQueryTool,
    GET_TRANSACTION_RECORD_QUERY_TOOL,
)

core_transaction_query_plugin = Plugin(
    name="core-transaction-query-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Transaction Query Service",
    tools=lambda context: [
        GetTransactionRecordQueryTool(context),
    ],
)

core_transaction_query_plugin_tool_names = {
    "GET_TRANSACTION_RECORD_QUERY_TOOL": GET_TRANSACTION_RECORD_QUERY_TOOL,
}

__all__ = [
    "core_transaction_query_plugin",
    "core_transaction_query_plugin_tool_names",
    "GetTransactionRecordQueryTool",
]
