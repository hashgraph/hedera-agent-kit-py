"""Utilities for building and executing fungible token creation operations via the Agent Kit.

This module exposes:
- create_fungible_token_prompt: Generate a prompt/description for the create fungible token tool.
- create_fungible_token: Execute a token creation transaction.
- CreateFungibleTokenTool: Tool wrapper exposing the create fungible token operation to the runtime.
"""

from __future__ import annotations

from pprint import pprint

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    CreateFungibleTokenParameters,
    CreateFungibleTokenParametersNormalised,
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


def create_fungible_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the create fungible token tool.

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

This tool creates a fungible token on Hedera.
*NOTE*: if token_name or token_symbol are not specified, do not call this tool and ask user for specific token name and symbol!
ONLY token_name and token_symbol ARE REQUIRED!

Parameters:
- token_name (str, required): The name of the token, required. If not explicitly specified, do not call this tool and ask user for specific token name.
- token_symbol (str, required): The symbol of the token, required.  If not explicitly specified, do not call this tool and ask user for specific token symbol 
- initial_supply (int, optional): The initial supply of the token, defaults to 0
- supply_type (int, optional): The supply type of the token. Can be finite = 1 or infinite = 0. Defaults to finite = 1
- max_supply (int, optional): The maximum supply of the token. Only applicable if supplyType is "finite". Defaults to 1,000,000 if not specified
- decimals (int, optional): The number of decimals the token supports. Defaults to 0
- {treasury_account_desc}
- is_supply_key (boolean, optional): If user wants to set supply key set to true, otherwise false. Defaults to true if max supply is specified or finite supply is set.
{scheduled_params_desc}
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a fungible token creation result.

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


async def create_fungible_token(
    client: Client,
    context: Context,
    params: CreateFungibleTokenParameters,
) -> ToolResponse:
    """Execute a fungible token creation using normalized parameters and a built transaction.

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
        normalised_params: CreateFungibleTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_create_fungible_token_params(
                params, context, client, mirrornode_service
            )
        )

        # Build transaction
        tx = HederaBuilder.create_fungible_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to create fungible token: {str(e)}"
        print("[create_fungible_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


CREATE_FUNGIBLE_TOKEN_TOOL: str = "create_fungible_token_tool"


class CreateFungibleTokenTool(Tool):
    """Tool wrapper that exposes the fungible token creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = CREATE_FUNGIBLE_TOKEN_TOOL
        self.name: str = "Create Fungible Token"
        self.description: str = create_fungible_token_prompt(context)
        self.parameters: type[CreateFungibleTokenParameters] = (
            CreateFungibleTokenParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: CreateFungibleTokenParameters
    ) -> ToolResponse:
        """Execute the token creation using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token creation parameters accepted by this tool.

        Returns:
            The result of the creation as a ToolResponse.
        """
        return await create_fungible_token(client, context, params)
