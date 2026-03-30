"""Utilities for deleting token allowances via the Agent Kit.

This module exposes:
- delete_token_allowance_prompt: Generate a prompt/description for the delete token allowance tool.
- delete_token_allowance: Execute a delete token allowance transaction.
- DeleteTokenAllowanceTool: Tool wrapper exposing the delete token allowance operation to the runtime.
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
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteTokenAllowanceParameters,
    ApproveTokenAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def delete_token_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the delete token allowance tool.

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
This tool deletes token allowance(s) from the owner to the spender.

Parameters:
- {owner_account_desc}
- spender_account_id (str, required): Spender account ID
- token_ids (array, required): List of token IDs whose allowances should be removed
- transaction_memo (str, optional): Optional memo for the transaction
{usage_instructions}
Example: "Delete token allowance for account 0.0.123 on token 0.0.456". Means that 0.0.123 is the spenderId, 0.0.456 is the tokenId and the ownerId is taken from context or default operator.
Example 2: "Delete token allowance given from 0.0.1001 to account 0.0.2002 for token 0.0.3003". Means that 0.0.1001 is the ownerId, 0.0.2002 is the spenderId and 0.0.3003 is the tokenId.
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a delete token allowance result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return f"Token allowance(s) deleted successfully. Transaction ID: {response.transaction_id}"


DELETE_TOKEN_ALLOWANCE_TOOL: str = "delete_token_allowance_tool"


class DeleteTokenAllowanceTool(BaseToolV2):
    """Tool wrapper that exposes the delete token allowance capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = DELETE_TOKEN_ALLOWANCE_TOOL
        self.name: str = "Delete Token Allowance"
        self.description: str = delete_token_allowance_prompt(context)
        self.parameters: type[DeleteTokenAllowanceParameters] = (
            DeleteTokenAllowanceParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> ApproveTokenAllowanceParametersNormalised:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        return await HederaParameterNormaliser.normalise_delete_token_allowance(
            params, context, client, mirrornode_service
        )

    async def core_action(
        self,
        normalized_params: ApproveTokenAllowanceParametersNormalised,
        client: Client,
        context: Context,
    ) -> Transaction:
        return HederaBuilder.approve_token_allowance(normalized_params)

    async def secondary_action(
        self,
        transaction: Transaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
