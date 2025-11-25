"""Utilities for querying token balances via the Agent Kit."""

from __future__ import annotations

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import (
    TokenBalancesResponse,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    AccountTokenBalancesQueryParameters,
    AccountTokenBalancesQueryParametersNormalised,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def get_token_balances_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get token balances tool."""
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the token balances for a given Hedera account.

Parameters:
- {account_desc}
- token_id (str, optional): The token ID to query for. If not provided, all token balances will be returned

{usage_instructions}
"""


def post_process(token_balances: TokenBalancesResponse, account_id: str) -> str:
    """Produce a human-readable summary for a token balances query result."""
    if not token_balances.get("tokens"):
        return f"No token balances found for account {account_id}"

    balances_text = "\n".join(
        [
            f"  Token: {token['token_id']}, Symbol: {token.get('symbol', 'UNKNOWN')}, Balance: {token['balance']}, Decimals: {token['decimals']}"
            for token in token_balances["tokens"]
        ]
    )

    return f"""Details for {account_id}
--- Token Balances ---
{balances_text}"""


async def get_token_balances(
    client: Client,
    context: Context,
    params: AccountTokenBalancesQueryParameters,
) -> ToolResponse:
    """Execute a token balances query using the mirror node service."""
    try:
        normalised_params: AccountTokenBalancesQueryParametersNormalised = (
            HederaParameterNormaliser.normalise_account_token_balances_params(
                params, context, client
            )
        )

        # Get mirrornode service
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Query token balances
        token_balances: TokenBalancesResponse = (
            await mirrornode_service.get_account_token_balances(
                normalised_params.account_id, normalised_params.token_id
            )
        )

        return ToolResponse(
            human_message=post_process(token_balances, normalised_params.account_id),
            extra={
                "account_id": normalised_params.account_id,
                "token_balances": token_balances,
            },
        )

    except Exception as e:
        message: str = f"Failed to get account token balances: {str(e)}"
        print("[get_account_token_balances_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL: str = "get_account_token_balances_query_tool"


class GetTokenBalancesTool(Tool):
    """Tool wrapper that exposes the token balances query capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL
        self.name: str = "Get Account Token Balances"
        self.description: str = get_token_balances_prompt(context)
        self.parameters: type[AccountTokenBalancesQueryParameters] = (
            AccountTokenBalancesQueryParameters
        )
        self.outputParser = untyped_query_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: AccountTokenBalancesQueryParameters,
    ) -> ToolResponse:
        return await get_token_balances(client, context, params)
