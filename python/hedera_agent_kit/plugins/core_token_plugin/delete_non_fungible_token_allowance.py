"""Utilities for deleting NFT allowances via the Agent Kit.

This module exposes:
- delete_non_fungible_token_allowance_prompt: Generate a prompt/description for the tool.
- delete_non_fungible_token_allowance: Execute a delete NFT allowance transaction.
- DeleteNonFungibleTokenAllowanceTool: Tool wrapper exposing the operation to the runtime.
"""

from __future__ import annotations


from typing import Any

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
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    DeleteNonFungibleTokenAllowanceParameters,
    DeleteNftAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
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


DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL: str = (
    "delete_non_fungible_token_allowance_tool"
)


class DeleteNonFungibleTokenAllowanceTool(BaseToolV2):
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

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> DeleteNftAllowanceParametersNormalised:
        return HederaParameterNormaliser.normalise_delete_non_fungible_token_allowance(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: DeleteNftAllowanceParametersNormalised,
        client: Client,
        context: Context,
    ) -> Transaction:
        return HederaBuilder.delete_nft_allowance(normalized_params)

    async def secondary_action(
        self,
        transaction: Transaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
