"""Utilities for querying HBAR balance via the Agent Kit.

This module exposes:
- get_hbar_balance_prompt: Generate a prompt/description for the get HBAR balance tool.
- get_hbar_balance: Execute an HBAR balance query.
- GetHbarBalanceTool: Tool wrapper exposing the HBAR balance query to the runtime.
"""

from __future__ import annotations

from decimal import Decimal

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    AccountBalanceQueryParameters,
    AccountBalanceQueryParametersNormalised,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def get_hbar_balance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get HBAR balance tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the HBAR balance for a given Hedera account.

Parameters:
- {account_desc}

{usage_instructions}
"""


def post_process(balance: Decimal, account_id: str) -> str:
    """Produce a human-readable summary for an HBAR balance query result.

    Args:
        balance: The HBAR balance in tinybars.
        account_id: The account ID that was queried.

    Returns:
        A concise message describing the HBAR balance.
    """
    # Convert tinybars to HBAR (1 HBAR = 100,000,000 tinybars)
    hbar_balance = balance / Decimal("100000000")
    return f"HBAR Balance for {account_id}: {hbar_balance} HBAR ({balance} tinybars)"


async def get_hbar_balance(
    client: Client,
    context: Context,
    params: AccountBalanceQueryParameters,
) -> ToolResponse:
    """Execute an HBAR balance query using the mirror node service.

    Args:
        client: Hedera client used for network information.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the account to query.

    Returns:
        A ToolResponse wrapping the raw balance data and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        normalised_params: AccountBalanceQueryParametersNormalised = (
            HederaParameterNormaliser.normalise_get_hbar_balance(
                params, context, client
            )
        )

        # Get mirrornode service
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Query HBAR balance
        balance: Decimal = await mirrornode_service.get_account_hbar_balance(
            normalised_params.account_id
        )

        return ToolResponse(
            human_message=post_process(balance, normalised_params.account_id),
            extra={
                "balance": str(balance),
                "account_id": str(normalised_params.account_id),
            },
        )

    except Exception as e:
        message: str = f"Failed to get HBAR balance: {str(e)}"
        print("[get_hbar_balance_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_HBAR_BALANCE_QUERY_TOOL: str = "get_hbar_balance_query_tool"


class GetHbarBalanceTool(Tool):
    """Tool wrapper that exposes the HBAR balance query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_HBAR_BALANCE_QUERY_TOOL
        self.name: str = "Get HBAR Balance"
        self.description: str = get_hbar_balance_prompt(context)
        self.parameters: type[AccountBalanceQueryParameters] = (
            AccountBalanceQueryParameters
        )
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: AccountBalanceQueryParameters
    ) -> ToolResponse:
        """Execute the HBAR balance query using the provided client, context, and params.

        Args:
            client: Hedera client used for network information.
            context: Runtime context providing configuration and defaults.
            params: HBAR balance query parameters accepted by this tool.

        Returns:
            The result of the HBAR balance query as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await get_hbar_balance(client, context, params)
