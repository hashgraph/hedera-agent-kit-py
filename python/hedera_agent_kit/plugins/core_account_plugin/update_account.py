"""Utilities for building and executing account update operations via the Agent Kit.

This module exposes:
- update_account_prompt: Generate a prompt/description for the update account tool.
- update_account: Execute an account update transaction.
- UpdateAccountTool: Tool wrapper exposing the account update operation to the runtime.
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
    UpdateAccountParameters,
    UpdateAccountParametersNormalised,
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


UPDATE_ACCOUNT_TOOL: str = "update_account_tool"


class UpdateAccountTool(BaseToolV2):
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

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> UpdateAccountParametersNormalised:
        return await HederaParameterNormaliser.normalise_update_account(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: UpdateAccountParametersNormalised,
        context: Context,
        client: Client,
    ) -> Transaction:
        return HederaBuilder.update_account(normalized_params)

    async def secondary_action(
        self, transaction: Transaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message: str = f"Failed to update account: {str(error)}"
        print("[update_account_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )
