from hedera_agent_kit_py.shared.plugin import Plugin
from .create_account import CreateAccountTool, CREATE_ACCOUNT_TOOL
from .delete_account import DeleteAccountTool, DELETE_ACCOUNT_TOOL
from .transfer_hbar import TransferHbarTool, TRANSFER_HBAR_TOOL
from .transfer_hbar_with_allowance import (
    TransferHbarWithAllowanceTool,
    TRANSFER_HBAR_WITH_ALLOWANCE_TOOL,
)
from .delete_hbar_allowance import (
    DeleteHbarAllowanceTool,
    DELETE_HBAR_ALLOWANCE_TOOL,
)
from .approve_hbar_allowance import (
    ApproveHbarAllowanceTool,
    APPROVE_HBAR_ALLOWANCE_TOOL,
)
from .update_account import UpdateAccountTool, UPDATE_ACCOUNT_TOOL

core_account_plugin = Plugin(
    name="core-account-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Account Service",
    tools=lambda context: [
        TransferHbarTool(context),
        DeleteAccountTool(context),
        CreateAccountTool(context),
        UpdateAccountTool(context),
        TransferHbarWithAllowanceTool(context),
        DeleteHbarAllowanceTool(context),
        ApproveHbarAllowanceTool(context),
    ],
)

core_account_plugin_tool_names = {
    "TRANSFER_HBAR_TOOL": TRANSFER_HBAR_TOOL,
    "CREATE_ACCOUNT_TOOL": CREATE_ACCOUNT_TOOL,
    "UPDATE_ACCOUNT_TOOL": UPDATE_ACCOUNT_TOOL,
    "DELETE_ACCOUNT_TOOL": DELETE_ACCOUNT_TOOL,
    "TRANSFER_HBAR_WITH_ALLOWANCE_TOOL": TRANSFER_HBAR_WITH_ALLOWANCE_TOOL,
    "DELETE_HBAR_ALLOWANCE_TOOL": DELETE_HBAR_ALLOWANCE_TOOL,
    "APPROVE_HBAR_ALLOWANCE_TOOL": APPROVE_HBAR_ALLOWANCE_TOOL,
}

__all__ = [
    "core_account_plugin",
    "core_account_plugin_tool_names",
    "TransferHbarTool",
    "DeleteAccountTool",
    "CreateAccountTool",
    "UpdateAccountTool",
    "TransferHbarWithAllowanceTool",
    "DeleteHbarAllowanceTool",
    "ApproveHbarAllowanceTool",
]
