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
from hedera_agent_kit.shared.tool import Tool
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
- spenderAccountId (string, required): Spender account ID
- transactionMemo (string, optional): Optional memo for the transaction
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


async def delete_hbar_allowance(
    client: Client,
    context: Context,
    params: DeleteHbarAllowanceParameters,
) -> ToolResponse:
    """Execute a delete HBAR allowance transaction.

    Args:
        client: Hedera client.
        context: Runtime context.
        params: Delete allowance parameters.

    Returns:
        A ToolResponse wrapping the transaction result.
    """
    try:
        normalised_params: ApproveHbarAllowanceParametersNormalised = (
            await HederaParameterNormaliser.normalise_delete_hbar_allowance(
                params, context, client
            )
        )

        tx = HederaBuilder.approve_hbar_allowance(normalised_params)

        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        desc = "Failed to delete hbar allowance."
        message = f"{desc}: {str(e)}"
        print("[delete_hbar_allowance_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )


DELETE_HBAR_ALLOWANCE_TOOL: str = "delete_hbar_allowance_tool"


class DeleteHbarAllowanceTool(Tool):
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

    async def execute(
        self,
        client: Client,
        context: Context,
        params: DeleteHbarAllowanceParameters,
    ) -> ToolResponse:
        """Execute the delete allowance using the provided client, context, and params.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Delete allowance parameters.

        Returns:
            The result of the transaction.
        """
        return await delete_hbar_allowance(client, context, params)
