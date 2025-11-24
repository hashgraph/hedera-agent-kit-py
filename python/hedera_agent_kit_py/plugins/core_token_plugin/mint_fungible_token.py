"""Utilities for building and executing fungible token minting operations via the Agent Kit.

This module exposes:
- mint_fungible_token_prompt: Generate a prompt/description for the mint fungible token tool.
- mint_fungible_token: Execute a token minting transaction.
- MintFungibleTokenTool: Tool wrapper exposing the token minting operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    MintFungibleTokenParameters,
    MintFungibleTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def mint_fungible_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the mint fungible token tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will mint a given amount (supply) of an existing fungible token on Hedera.

Parameters:
- token_id (str, required): The id of the token
- amount (number, required): The amount to be minted
{usage_instructions}

Example: "Mint 1 of 0.0.6458037" means minting the amount of 1 of the token with id 0.0.6458037.
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a token minting result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and any relevant identifiers.
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled mint transaction created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return f"Tokens successfully minted.\n" f"Transaction ID: {response.transaction_id}"


async def mint_fungible_token(
    client: Client,
    context: Context,
    params: MintFungibleTokenParameters,
) -> ToolResponse:
    """Execute a token minting using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the token mint.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.
    """
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        # Normalize parameters
        normalised_params: MintFungibleTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_mint_fungible_token_params(
                params, context, client, mirrornode_service
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.mint_fungible_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to mint fungible token: {str(e)}"
        print("[mint_fungible_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


MINT_FUNGIBLE_TOKEN_TOOL: str = "mint_fungible_token_tool"


class MintFungibleTokenTool(Tool):
    """Tool wrapper that exposes the fungible token minting capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = MINT_FUNGIBLE_TOKEN_TOOL
        self.name: str = "Mint Fungible Token"
        self.description: str = mint_fungible_token_prompt(context)
        self.parameters: type[MintFungibleTokenParameters] = MintFungibleTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: MintFungibleTokenParameters
    ) -> ToolResponse:
        """Execute the token minting using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token minting parameters accepted by this tool.

        Returns:
            The result of the token minting as a ToolResponse.
        """
        return await mint_fungible_token(client, context, params)
