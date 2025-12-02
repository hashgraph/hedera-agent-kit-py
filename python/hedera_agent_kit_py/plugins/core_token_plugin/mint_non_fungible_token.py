"""Utilities for building and executing non-fungible token minting operations via the Agent Kit.

This module exposes:
- mint_non_fungible_token_prompt: Generate a prompt/description for the mint non-fungible token tool.
- mint_non_fungible_token: Execute a token minting transaction.
- MintNonFungibleTokenTool: Tool wrapper exposing the token minting operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

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
    MintNonFungibleTokenParameters,
    MintNonFungibleTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def mint_non_fungible_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the mint non-fungible token tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will mint NFTs with its unique metadata for the class of NFTs (non-fungible tokens) defined by the tokenId on Hedera.

Parameters:
- token_id (str, required): The id of the token
- uris (array, required): An array of strings (URIs) of maximum size 10 hosting the NFT metadata
{usage_instructions}

Example: "Mint 0.0.6465503 with metadata: ipfs://bafyreiao6ajgsfji6qsgbqwdtjdu5gmul7tv2v3pd6kjgcw5o65b2ogst4/metadata.json" means minting an NFT with the given metadata URI for the class of NFTs defined by the token with id 0.0.6465503.
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
    token_id_str = str(response.token_id) if response.token_id else "unknown"
    return (
        f"Token successfully minted.\n"
        f"Transaction ID: {response.transaction_id}\n"
        f"Token ID: {token_id_str}"
    )


async def mint_non_fungible_token(
    client: Client,
    context: Context,
    params: MintNonFungibleTokenParameters,
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
        # Normalize parameters
        normalised_params: MintNonFungibleTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_mint_non_fungible_token_params(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.mint_non_fungible_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to mint non-fungible token: {str(e)}"
        print("[mint_non_fungible_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


MINT_NON_FUNGIBLE_TOKEN_TOOL: str = "mint_non_fungible_token_tool"


class MintNonFungibleTokenTool(Tool):
    """Tool wrapper that exposes the non-fungible token minting capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = MINT_NON_FUNGIBLE_TOKEN_TOOL
        self.name: str = "Mint Non-Fungible Token"
        self.description: str = mint_non_fungible_token_prompt(context)
        self.parameters: type[MintNonFungibleTokenParameters] = (
            MintNonFungibleTokenParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: MintNonFungibleTokenParameters
    ) -> ToolResponse:
        """Execute the token minting using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token minting parameters accepted by this tool.

        Returns:
            The result of the token minting as a ToolResponse.
        """
        return await mint_non_fungible_token(client, context, params)
