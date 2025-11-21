"""Utilities for building and executing token dissociation operations via the Agent Kit.

This module exposes:
- dissociate_token_prompt: Generate a prompt/description for the dissociate token tool.
- dissociate_token: Execute a token dissociation transaction.
- DissociateTokenTool: Tool wrapper exposing the dissociation operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, TokenDissociateTransaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    DissociateTokenParameters,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def dissociate_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the dissociate token tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will dissociate one or more tokens from a Hedera account.

Parameters:
- token_ids (array of strings, required): A list of Hedera token IDs to dissociate from the account. Example: ["0.0.1234", "0.0.5678"]
- {source_account_desc}, account from which to dissociate the token(s)
- transaction_memo (str, optional): Optional memo for the transaction

Examples:
- Dissociate a single token: {{ "token_ids": ["0.0.1234"] }}
- Dissociate multiple tokens from a specific account: {{ "token_ids": ["0.0.1234", "0.0.5678"], "account_id": "0.0.4321" }}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a token dissociation result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A message confirming the dissociation.
    """
    return f"Token(s) successfully dissociated with transaction id {response.transaction_id}"


async def dissociate_token(
    client: Client,
    context: Context,
    params: DissociateTokenParameters,
) -> ToolResponse:
    """Execute a token dissociation using normalized parameters and a built transaction.

    Args:
        client: Hedera client.
        context: Runtime context.
        params: Dissociation parameters.

    Returns:
        A ToolResponse wrapping the transaction result.
    """
    try:
        normalised_params = (
            await HederaParameterNormaliser.normalise_dissociate_token_params(
                params, context, client
            )
        )

        # Assuming HederaBuilder.dissociate_token exists
        tx: TokenDissociateTransaction = HederaBuilder.dissociate_token(
            normalised_params
        )

        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        desc = "Failed to dissociate token"
        message = f"{desc}: {str(e)}"
        print("[dissociate_token_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )


DISSOCIATE_TOKEN_TOOL: str = "dissociate_token_tool"


class DissociateTokenTool(Tool):
    """Tool wrapper that exposes the token dissociation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata.

        Args:
            context: Runtime context.
        """
        self.method: str = DISSOCIATE_TOKEN_TOOL
        self.name: str = "Dissociate Token"
        self.description: str = dissociate_token_prompt(context)
        self.parameters: type[DissociateTokenParameters] = DissociateTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: DissociateTokenParameters
    ) -> ToolResponse:
        """Execute the dissociation using the provided client, context, and params.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Dissociation parameters.

        Returns:
            The result of the transaction.
        """
        return await dissociate_token(client, context, params)
