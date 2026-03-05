"""Utilities for building and executing token association operations via the Agent Kit.

This module exposes:
- associate_token_prompt: Generate a prompt/description for the associate token tool.
- associate_token: Execute a token association transaction.
- AssociateTokenTool: Tool wrapper exposing the token association operation to the runtime.
"""

from __future__ import annotations

from typing import Any

from hiero_sdk_python import Client
from hiero_sdk_python.tokens.token_associate_transaction import (
    TokenAssociateTransaction,
)

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
    AssociateTokenParameters,
    AssociateTokenParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def associate_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the associate token tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_any_address_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will associate one or more tokens with a Hedera account.

Parameters:
{account_desc}
- token_ids (List[str], required): Array of token IDs to associate
{usage_instructions}

Example: "Associate tokens 0.0.123 and 0.0.456 to account 0.0.789".
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a token association result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return (
        f"Tokens successfully associated with transaction id {response.transaction_id}"
    )


ASSOCIATE_TOKEN_TOOL: str = "associate_token_tool"


class AssociateTokenTool(BaseToolV2):
    """Tool wrapper that exposes the token association capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = ASSOCIATE_TOKEN_TOOL
        self.name: str = "Associate Token(s)"
        self.description: str = associate_token_prompt(context)
        self.parameters: type[AssociateTokenParameters] = AssociateTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> AssociateTokenParametersNormalised:
        return HederaParameterNormaliser.normalise_associate_token(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: AssociateTokenParametersNormalised,
        client: Client,
        context: Context,
    ) -> TokenAssociateTransaction:
        return HederaBuilder.associate_token(normalized_params)

    async def secondary_action(
        self,
        transaction: TokenAssociateTransaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
