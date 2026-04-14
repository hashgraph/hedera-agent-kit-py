"""Utilities for building and executing HBAR allowance transfer operations via the Agent Kit.

This module exposes:
- transfer_hbar_with_allowance_prompt: Generate a prompt/description for the tool.
- transfer_hbar_with_allowance: Execute an HBAR transfer using allowance.
- TransferHbarWithAllowanceTool: Tool wrapper exposing the operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, TransferTransaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    TransferHbarWithAllowanceParameters,
    TransferHbarWithAllowanceParametersNormalised,
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


def transfer_hbar_with_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the transfer HBAR with allowance tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool transfers HBAR **on behalf of another account** using a pre-approved **Allowance**.

Use this tool ONLY when:
- The request involves spending from a "source account" that is NOT the current signer.
- The user explicitly mentions "allowance", "delegated transfer", or "spending limit".
- You are moving HBAR *from* a specific owner *to* a recipient using previously granted permissions.

Do NOT use this tool for:
- Standard direct transfers of HBAR where the signer owns the HBAR.

Parameters:
- source_account_id (string, required): Account ID of the HBAR owner (the allowance granter)
- transfers (array of objects, required): List of HBAR transfers. Each object should contain:
  - account_id (string): Recipient account ID
  - amount (number): Amount of HBAR to transfer
- transaction_memo (string, optional): Optional memo for the transfer HBAR with allowance transaction
{PromptGenerator.get_scheduled_transaction_params_description(context)}

{usage_instructions}

Example: "Transfer 2 HBAR from 0.0.1002 to 0.0.2002 using allowance"
Example: "Spend allowance from account 0.0.1002 to send 5 HBAR to 0.0.2002"
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for an HBAR allowance transfer.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A message confirming the transaction.
    """
    return f"HBAR successfully transferred with allowance. Transaction ID: {response.transaction_id}"


TRANSFER_HBAR_WITH_ALLOWANCE_TOOL: str = "transfer_hbar_with_allowance_tool"


class TransferHbarWithAllowanceTool(BaseToolV2):
    """Tool wrapper that exposes the HBAR allowance transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool.

        Args:
            context: Runtime context.
        """
        self.method: str = TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
        self.name: str = "Transfer HBAR with allowance"
        self.description: str = transfer_hbar_with_allowance_prompt(context)
        self.parameters: type[TransferHbarWithAllowanceParameters] = (
            TransferHbarWithAllowanceParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> TransferHbarWithAllowanceParametersNormalised:
        return await HederaParameterNormaliser.normalise_transfer_hbar_with_allowance(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: TransferHbarWithAllowanceParametersNormalised,
        context: Context,
        client: Client,
    ) -> TransferTransaction:
        return HederaBuilder.transfer_hbar_with_allowance(normalized_params)

    async def secondary_action(
        self, transaction: TransferTransaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        desc = "Failed to transfer HBAR with allowance"
        message = f"{desc}: {str(error)}"
        print("[transfer_hbar_with_allowance_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )
