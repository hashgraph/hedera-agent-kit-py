"""Utilities for building and executing non-fungible token (NFT) creation operations via the Agent Kit.

This module exposes:
- create_non_fungible_token_prompt: Generate a prompt/description for the create NFT tool.
- create_non_fungible_token: Execute an NFT creation transaction.
- CreateNonFungibleTokenTool: Tool wrapper exposing the create NFT operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParameters,
    CreateNonFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def create_non_fungible_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the create non-fungible token tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    treasury_account_desc: str = PromptGenerator.get_account_parameter_description(
        "treasury_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_params_desc: str = (
        PromptGenerator.get_scheduled_transaction_params_description(context)
    )

    return f"""
{context_snippet}

This tool creates a non-fungible token (NFT) on Hedera.

Parameters:
- token_name (str, required): Name of the token
- token_symbol (str, required): Symbol of the token
- max_supply (int, optional): Maximum NFT supply. If not specified, the supply is infinite.
- {treasury_account_desc}
{scheduled_params_desc}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a non-fungible token creation result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status, token ID, and transaction ID.
    """
    if response.schedule_id:
        return f"""Scheduled transaction created successfully.
Transaction ID: {response.transaction_id}
Schedule ID: {response.schedule_id}"""

    token_id_str = str(response.token_id) if response.token_id else "unknown"
    return f"""Token created successfully.
Transaction ID: {response.transaction_id}
Token ID: {token_id_str}"""


async def create_non_fungible_token(
    client: Client,
    context: Context,
    params: CreateNonFungibleTokenParameters,
) -> ToolResponse:
    """Execute a non-fungible token creation using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the token to create.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Normalize parameters
        normalised_params: CreateNonFungibleTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_create_non_fungible_token_params(
                params, context, client, mirrornode_service
            )
        )

        # Build transaction
        tx = HederaBuilder.create_non_fungible_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to create non-fungible token: {str(e)}"
        print("[create_non_fungible_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


CREATE_NON_FUNGIBLE_TOKEN_TOOL: str = "create_non_fungible_token_tool"


class CreateNonFungibleTokenTool(Tool):
    """Tool wrapper that exposes the non-fungible token creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = CREATE_NON_FUNGIBLE_TOKEN_TOOL
        self.name: str = "Create Non-Fungible Token"
        self.description: str = create_non_fungible_token_prompt(context)
        self.parameters: type[CreateNonFungibleTokenParameters] = (
            CreateNonFungibleTokenParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: CreateNonFungibleTokenParameters
    ) -> ToolResponse:
        """Execute the token creation using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token creation parameters accepted by this tool.

        Returns:
            The result of the creation as a ToolResponse.
        """
        return await create_non_fungible_token(client, context, params)
