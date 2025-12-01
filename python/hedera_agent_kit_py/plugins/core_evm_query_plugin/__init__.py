from hedera_agent_kit_py.plugins.core_evm_query_plugin.get_contract_info_query import (
    GetContractInfoQueryTool,
    GET_CONTRACT_INFO_QUERY_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin

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
