from .get_account_query import GetAccountQueryTool, GET_ACCOUNT_QUERY_TOOL
from hedera_agent_kit_py.shared.plugin import Plugin
from .get_hbar_balance import GetHbarBalanceTool, GET_HBAR_BALANCE_QUERY_TOOL

core_account_query_plugin = Plugin(
    name="core-account-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Account Service",
    tools=lambda context: [GetHbarBalanceTool(context), GetAccountQueryTool(context)],
)

core_account_query_plugin_tool_names = {
    "GET_HBAR_BALANCE_QUERY_TOOL": GET_HBAR_BALANCE_QUERY_TOOL,
    "GET_ACCOUNT_QUERY_TOOL": GET_ACCOUNT_QUERY_TOOL,
}

__all__ = [
    "core_account_query_plugin",
    "core_account_query_plugin_tool_names",
    "GetHbarBalanceTool",
    "GetAccountQueryTool",
]
