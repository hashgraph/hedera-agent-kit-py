from hedera_agent_kit_py.shared.plugin import Plugin
from .transfer_hbar import TransferHbarTool, TRANSFER_HBAR_TOOL

core_account_plugin = Plugin(
    name="core-account-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Account Service",
    tools=lambda context: [
        TransferHbarTool(context),
    ],
)

core_account_plugin_tool_names = {
    TRANSFER_HBAR_TOOL,
}

__all__ = [
    "core_account_plugin",
    "core_account_plugin_tool_names",
    "TransferHbarTool",
]
