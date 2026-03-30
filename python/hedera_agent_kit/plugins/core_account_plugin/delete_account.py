"""Utilities for building and executing account deletion operations via the Agent Kit.

This module exposes:
- delete_account_prompt: Generate a prompt/description for the delete account tool.
- delete_account: Execute an account deletion transaction.
- DeleteAccountTool: Tool wrapper exposing the delete account operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.account.account_delete_transaction import (
    AccountDeleteTransaction,
)

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteAccountParameters,
    DeleteAccountParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from typing import Any
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def delete_account_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the delete account tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will delete an existing Hedera account. The remaining balance of the account will be transferred to the transfer_account_id if provided, otherwise the operator account will be used.

Parameters:
- {account_desc}
- account_id (str, required): The account ID to delete
- transfer_account_id (str, optional): The account ID to transfer the remaining balance to. If not provided, the operator account will be used.

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for an account deletion result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return f"Account successfully deleted. Transaction ID: {response.transaction_id}"


DELETE_ACCOUNT_TOOL: str = "delete_account_tool"


class DeleteAccountTool(BaseToolV2):
    """Tool wrapper that exposes the account deletion capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = DELETE_ACCOUNT_TOOL
        self.name: str = "Delete Account"
        self.description: str = delete_account_prompt(context)
        self.parameters: type[DeleteAccountParameters] = DeleteAccountParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> DeleteAccountParametersNormalised:
        return HederaParameterNormaliser.normalise_delete_account(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: DeleteAccountParametersNormalised,
        context: Context,
        client: Client,
    ) -> AccountDeleteTransaction:
        return HederaBuilder.delete_account(normalized_params)

    async def secondary_action(
        self, transaction: AccountDeleteTransaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message: str = f"Failed to delete account: {str(error)}"
        print("[delete_account_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )
