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
from typing import Any
from hedera_agent_kit.shared.parameter_schemas import (
    AccountBalanceQueryParameters,
    AccountBalanceQueryParametersNormalised,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
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


def post_process(hbar_balance: str, account_id: str) -> str:
    """Produce a human-readable summary for an HBAR balance query result.

    Args:
        hbar_balance: The stringified HBAR balance.
        account_id: The account ID that was queried.

    Returns:
        A concise message describing the HBAR balance.
    """
    return f"""Account {account_id} has a balance of {hbar_balance} HBAR

This balance is equivalent to {int(Decimal(hbar_balance) * Decimal("100000000"))} tinybars.
"""


GET_HBAR_BALANCE_QUERY_TOOL: str = "get_hbar_balance_query_tool"


class GetHbarBalanceTool(BaseToolV2):
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

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> AccountBalanceQueryParametersNormalised:
        return HederaParameterNormaliser.normalise_get_hbar_balance(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: AccountBalanceQueryParametersNormalised,
        context: Context,
        client: Client,
    ) -> ToolResponse:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        balance: Decimal = await mirrornode_service.get_account_hbar_balance(
            normalized_params.account_id
        )
        hbar_balance = str(balance / Decimal("100000000"))

        return ToolResponse(
            human_message=post_process(hbar_balance, normalized_params.account_id),
            extra={
                "balance": str(balance),
                "account_id": normalized_params.account_id,
            },
        )

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return False

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> Any:
        return core_result

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        desc = "Failed to get HBAR balance"
        message = f"{desc}: {str(error)}"
        print("[get_hbar_balance_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )
