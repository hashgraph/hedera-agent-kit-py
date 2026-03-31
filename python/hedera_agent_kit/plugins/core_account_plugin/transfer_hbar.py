"""Utilities for building and executing HBAR transfer operations via the Agent Kit.

This module exposes:
- transfer_hbar_prompt: Generate a prompt/description for the transfer tool.
- transfer_hbar: Execute an HBAR transfer transaction.
- TransferHbarTool: Tool wrapper exposing the transfer operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

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
    TransferHbarParameters,
    TransferHbarParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def transfer_hbar_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the HBAR transfer tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information or scheduling capabilities.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This async tool will transfer HBAR to an account.

Parameters:
- transfers (list of dicts, required): Each dict must contain:
    - account_id (str): Recipient account ID
    - amount (float or str): Amount of HBAR to transfer
- {source_account_desc}
- transaction_memo (str, optional): Optional memo for the transfer transaction
{scheduled_desc}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a transfer transaction result.

    Args:
        response: The raw response returned by the transaction execution, which
            may contain a schedule_id if the transaction was scheduled.

    Returns:
        A concise message describing the status and any relevant identifiers
        (e.g., transaction ID, schedule ID).
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled HBAR transfer created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return f"HBAR successfully transferred.\nTransaction ID: {response.transaction_id}"


async def transfer_hbar(
    client: Client,
    context: Context,
    params: TransferHbarParameters,
) -> ToolResponse:
    """Execute an HBAR transfer using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the transfer(s) to perform.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
        It accepts raw params, validates, and normalizes them before performing the transaction.
    """
    try:
        # Normalize parameters
        normalised_params: TransferHbarParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_hbar(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.transfer_hbar(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to transfer HBAR: {str(e)}"
        print("[transfer_hbar_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_HBAR_TOOL: str = "transfer_hbar_tool"


class TransferHbarTool(Tool):
    """Tool wrapper that exposes the HBAR transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = TRANSFER_HBAR_TOOL
        self.name: str = "Transfer HBAR"
        self.description: str = transfer_hbar_prompt(context)
        self.parameters: type[TransferHbarParameters] = TransferHbarParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: TransferHbarParameters
    ) -> ToolResponse:
        """Execute the HBAR transfer using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Transfer parameters accepted by this tool.

        Returns:
            The result of the transfer as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await transfer_hbar(client, context, params)
