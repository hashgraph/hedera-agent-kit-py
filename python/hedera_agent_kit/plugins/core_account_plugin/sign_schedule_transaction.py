"""Utilities for building and executing schedule signing operations via the Agent Kit.

This module exposes:
- sign_schedule_transaction_prompt: Generate a prompt/description for the sign schedule transaction tool.
- sign_schedule_transaction: Execute a schedule signing transaction.
- SignScheduleTransactionTool: Tool wrapper exposing the schedule signing operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, ScheduleSignTransaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    SignScheduleTransactionToolParameters,
    SignScheduleTransactionParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def sign_schedule_transaction_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the sign schedule transaction tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will sign a scheduled transaction and return the transaction ID.

Parameters:
- schedule_id (string, required): The ID of the scheduled transaction to sign

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a schedule signing result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and the transaction ID.
    """
    return f"Transaction successfully signed. Transaction ID: {response.transaction_id}"


async def sign_schedule_transaction(
    client: Client,
    context: Context,
    params: SignScheduleTransactionToolParameters,
) -> ToolResponse:
    """Execute a schedule signing transaction using normalized parameters.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the schedule to sign.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        # Normalize parameters
        normalised_params: SignScheduleTransactionParametersNormalised = (
            HederaParameterNormaliser.normalise_sign_schedule_transaction(params)
        )

        # Build transaction
        tx: ScheduleSignTransaction = HederaBuilder.sign_schedule_transaction(
            normalised_params
        )

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to sign scheduled transaction: {str(e)}"
        print("[sign_schedule_transaction_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


SIGN_SCHEDULE_TRANSACTION_TOOL: str = "sign_schedule_transaction_tool"


class SignScheduleTransactionTool(Tool):
    """Tool wrapper that exposes the schedule signing capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = SIGN_SCHEDULE_TRANSACTION_TOOL
        self.name: str = "Sign Scheduled Transaction"
        self.description: str = sign_schedule_transaction_prompt(context)
        self.parameters: type[SignScheduleTransactionToolParameters] = (
            SignScheduleTransactionToolParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: SignScheduleTransactionToolParameters,
    ) -> ToolResponse:
        """Execute the schedule signing using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Schedule signing parameters accepted by this tool.

        Returns:
            The result of the schedule signing as a ToolResponse, including a
            human-readable message and error information if applicable.
        """
        return await sign_schedule_transaction(client, context, params)
