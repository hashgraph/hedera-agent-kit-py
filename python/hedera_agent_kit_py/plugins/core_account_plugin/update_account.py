"""Utilities for building and executing account update operations via the Agent Kit.

This module exposes:
- update_account_prompt: Generate a prompt/description for the update account tool.
- update_account: Execute an account update transaction.
- UpdateAccountTool: Tool wrapper exposing the account update operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    UpdateAccountParameters,
    UpdateAccountParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import transaction_tool_output_parser
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def update_account_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the update account tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information or scheduling capabilities.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This tool will update an existing Hedera account. Only provided fields will be updated.

Parameters:
- {account_desc}
- account_id (str, optional): Account ID to update (e.g., 0.0.xxxxx). If not provided, operator account ID will be used
- max_automatic_token_associations (int, optional): Max automatic token associations, positive, zero, or -1 for unlimited
- staked_account_id (str, optional): Account ID to stake to
- account_memo (str, optional): Memo to be set for the updated account
- decline_staking_reward (bool, optional): Whether to decline staking rewards
{scheduled_desc}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for an account update result.

    Args:
        response: The raw response returned by the transaction execution, which
            may contain a schedule_id if the transaction was scheduled.

    Returns:
        A concise message describing the status and any relevant identifiers
        (e.g., transaction ID, schedule ID).
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled account update created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return (
        f"Account successfully updated.\n" f"Transaction ID: {response.transaction_id}"
    )


async def update_account(
    client: Client,
    context: Context,
    params: UpdateAccountParameters,
) -> ToolResponse:
    """Execute an account update using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the account update.

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
        normalised_params: UpdateAccountParametersNormalised = (
            await HederaParameterNormaliser.normalise_update_account(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.update_account(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to update account: {str(e)}"
        print("[update_account_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


UPDATE_ACCOUNT_TOOL: str = "update_account_tool"


class UpdateAccountTool(Tool):
    """Tool wrapper that exposes the account update capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = UPDATE_ACCOUNT_TOOL
        self.name: str = "Update Account"
        self.description: str = update_account_prompt(context)
        self.parameters: type[UpdateAccountParameters] = UpdateAccountParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: UpdateAccountParameters
    ) -> ToolResponse:
        """Execute the account update using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Account update parameters accepted by this tool.

        Returns:
            The result of the account update as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await update_account(client, context, params)
