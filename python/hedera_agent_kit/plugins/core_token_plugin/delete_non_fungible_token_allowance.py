"""Utilities for deleting NFT allowances via the Agent Kit.

This module exposes:
- delete_non_fungible_token_allowance_prompt: Generate a prompt/description for the tool.
- delete_non_fungible_token_allowance: Execute a delete NFT allowance transaction.
- DeleteNonFungibleTokenAllowanceTool: Tool wrapper exposing the operation to the runtime.
"""

from __future__ import annotations


from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    DeleteNonFungibleTokenAllowanceParameters,
    DeleteNftAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def delete_non_fungible_token_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the delete NFT allowance tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet = PromptGenerator.get_context_snippet(context)
    owner_account_desc = PromptGenerator.get_account_parameter_description(
        "owner_account_id", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    return f"""
{context_snippet}
This tool deletes NFT allowance(s) from the owner. Removing an allowance for a serial number means clearing the currently approved spender.

Parameters:
- {owner_account_desc}
- token_id (str, required): The ID of the NFT token.
- serial_numbers (array, required): List of serial numbers to remove allowance for.
- transaction_memo (str, optional): Optional memo for the transaction.

{usage_instructions}
Example: "Delete allowance for NFT 0.0.123 serials [1, 2]"
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a delete NFT allowance result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return f"NFT allowance(s) deleted successfully. Transaction ID: {response.transaction_id}"


async def delete_non_fungible_token_allowance(
    client: Client,
    context: Context,
    params: DeleteNonFungibleTokenAllowanceParameters,
) -> ToolResponse:
    """Execute a delete NFT allowance transaction using normalized parameters.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the allowance deletion.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.
    """
    try:
        # Normalize parameters
        normalised_params: DeleteNftAllowanceParametersNormalised = (
            HederaParameterNormaliser.normalise_delete_non_fungible_token_allowance(
                params, context, client
            )
        )

        tx = HederaBuilder.delete_nft_allowance(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        desc = "Failed to delete NFT allowance(s)."
        message: str = desc + (f": {str(e)}" if str(e) else "")
        print("[delete_non_fungible_token_allowance_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL: str = (
    "delete_non_fungible_token_allowance_tool"
)


class DeleteNonFungibleTokenAllowanceTool(Tool):
    """Tool wrapper that exposes the delete NFT allowance capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
        self.name: str = "Delete Non Fungible Token Allowance"
        self.description: str = delete_non_fungible_token_allowance_prompt(context)
        self.parameters: type[DeleteNonFungibleTokenAllowanceParameters] = (
            DeleteNonFungibleTokenAllowanceParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: DeleteNonFungibleTokenAllowanceParameters,
    ) -> ToolResponse:
        """Execute the delete NFT allowance using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Delete NFT allowance parameters accepted by this tool.

        Returns:
            The result of the deletion as a ToolResponse.
        """
        return await delete_non_fungible_token_allowance(client, context, params)
