from hedera_agent_kit.shared.plugin import Plugin
from hedera_agent_kit.plugins.core_evm_query_plugin.get_contract_info_query import (
    GetContractInfoQueryTool,
    GET_CONTRACT_INFO_QUERY_TOOL,
)

core_evm_query_plugin = Plugin(
    name="core-evm-query-plugin",
    version="1.0.0",
    description="A plugin for querying EVM-related data on Hedera",
    tools=lambda context: [
        GetContractInfoQueryTool(context),
    ],
)

core_evm_query_plugin_tool_names = {
    "GET_CONTRACT_INFO_QUERY_TOOL": GET_CONTRACT_INFO_QUERY_TOOL,
}

__all__ = [
    "core_evm_query_plugin",
    "core_evm_query_plugin_tool_names",
    "GetContractInfoQueryTool",
]
