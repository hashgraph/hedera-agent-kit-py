"""Tool for deleting HBAR allowances."""

from hiero_sdk_python import Client

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
    DeleteHbarAllowanceParameters,
    ApproveHbarAllowanceParametersNormalised,
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


def delete_hbar_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the delete HBAR allowance tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    owner_account_desc: str = PromptGenerator.get_account_parameter_description(
        "ownerAccountId", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool deletes an HBAR allowance from the owner to the spender.

Parameters:
- {owner_account_desc}
- spender_account_d (string, required): Spender account ID
- transaction_memo (string, optional): Optional memo for the transaction
{usage_instructions}

Example: "Delete HBAR allowance from 0.0.123 to 0.0.456". Spender account ID is 0.0.456 and the owner account ID is 0.0.789.
Example 2: "Delete HBAR allowance for 0.0.123". Spender account ID is 0.0.123 and the owner account ID was not specified.
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a delete HBAR allowance transaction.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A message confirming the transaction.
    """
    return f"HBAR allowance deleted successfully. Transaction ID: {response.transaction_id}"


DELETE_HBAR_ALLOWANCE_TOOL: str = "delete_hbar_allowance_tool"


class DeleteHbarAllowanceTool(BaseToolV2):
    """Tool wrapper that exposes the delete HBAR allowance capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool.

        Args:
            context: Runtime context.
        """
        self.method: str = DELETE_HBAR_ALLOWANCE_TOOL
        self.name: str = "Delete HBAR Allowance"
        self.description: str = delete_hbar_allowance_prompt(context)
        self.parameters: type[DeleteHbarAllowanceParameters] = (
            DeleteHbarAllowanceParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> ApproveHbarAllowanceParametersNormalised:
        return await HederaParameterNormaliser.normalise_delete_hbar_allowance(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: ApproveHbarAllowanceParametersNormalised,
        context: Context,
        client: Client,
    ):
        return HederaBuilder.approve_hbar_allowance(normalized_params)

    async def secondary_action(
        self, transaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        desc = "Failed to delete hbar allowance."
        message = f"{desc}: {str(error)}"
        print("[delete_hbar_allowance_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )
