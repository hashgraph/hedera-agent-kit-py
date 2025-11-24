"""Utilities for building and executing token association operations via the Agent Kit.

This module exposes:
- associate_token_prompt: Generate a prompt/description for the associate token tool.
- associate_token: Execute a token association transaction.
- AssociateTokenTool: Tool wrapper exposing the token association operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.tokens.token_associate_transaction import (
    TokenAssociateTransaction,
)

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
    AssociateTokenParameters,
    AssociateTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


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


async def associate_token(
    client: Client,
    context: Context,
    params: AssociateTokenParameters,
) -> ToolResponse:
    """Execute a token association using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the token association to perform.

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
        normalised_params: AssociateTokenParametersNormalised = (
            HederaParameterNormaliser.normalise_associate_token(params, context, client)
        )

        # Build transaction
        tx: TokenAssociateTransaction = HederaBuilder.associate_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to associate token(s): {str(e)}"
        print("[associate_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


ASSOCIATE_TOKEN_TOOL: str = "associate_token_tool"


class AssociateTokenTool(Tool):
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

    async def execute(
        self, client: Client, context: Context, params: AssociateTokenParameters
    ) -> ToolResponse:
        """Execute the token association using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token association parameters accepted by this tool.

        Returns:
            The result of the association as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await associate_token(client, context, params)
