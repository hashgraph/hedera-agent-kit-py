from hedera_agent_kit_py.shared.plugin import Plugin
from .transfer_hbar import TransferHbarTool, TRANSFER_HBAR_TOOL
from .create_account import CreateAccountTool, CREATE_ACCOUNT_TOOL
from .update_account import UpdateAccountTool, UPDATE_ACCOUNT_TOOL

core_account_plugin = Plugin(
    name="core-account-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Account Service",
    tools=lambda context: [
        TransferHbarTool(context),
        CreateAccountTool(context),
        UpdateAccountTool(context),
    ],
)

core_account_plugin_tool_names = {
    "TRANSFER_HBAR_TOOL": TRANSFER_HBAR_TOOL,
    "CREATE_ACCOUNT_TOOL": CREATE_ACCOUNT_TOOL,
    "UPDATE_ACCOUNT_TOOL": UPDATE_ACCOUNT_TOOL,
}

__all__ = [
    "core_account_plugin",
    "core_account_plugin_tool_names",
    "TransferHbarTool",
    "CreateAccountTool",
    "UpdateAccountTool",
]
