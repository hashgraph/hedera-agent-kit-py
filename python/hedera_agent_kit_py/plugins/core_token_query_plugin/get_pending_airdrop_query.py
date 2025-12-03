"""Utilities for querying pending airdrops via the Agent Kit.

This module exposes:
- get_pending_airdrop_query_prompt: Generate a prompt/description for the get pending airdrop query tool.
- get_pending_airdrop_query: Execute a pending airdrop query.
- GetPendingAirdropQueryTool: Tool wrapper exposing the pending airdrop query operation to the runtime.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TypedDict, List, cast

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils import to_display_unit
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import HederaParameterNormaliser
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import \
    IHederaMirrornodeService
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import (
    TokenAirdrop,
    TokenAirdropsResponse, TokenInfo,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    PendingAirdropQueryParameters,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator

class EnrichedTokenAirdrop(TokenAirdrop):
    """Extends the basic airdrop record with token metadata."""
    decimals: int
    symbol: str

class EnrichedTokenAirdropsResponse(TypedDict):
    """Response wrapper containing enriched airdrops."""
    airdrops: List[EnrichedTokenAirdrop]


def get_pending_airdrop_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get pending airdrop query tool."""
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return pending airdrops for a given Hedera account.

Parameters:
- {account_desc}
{usage_instructions}
"""


async def enrich_single_airdrop(
    airdrop: TokenAirdrop, mirrornode_service: IHederaMirrornodeService
) -> EnrichedTokenAirdrop:
    """Helper: Fetches token info for a single airdrop and adds symbol/decimals to it."""
    enriched = cast(EnrichedTokenAirdrop, airdrop)
    token_id = airdrop.get("token_id")

    # Default values in case of logic skip or error
    decimals = 0
    symbol = "N/A"

    if token_id:
        try:
            info: TokenInfo = await mirrornode_service.get_token_info(token_id)
            decimals = int(info.get("decimals", 0))
            symbol = info.get("symbol", "N/A")
        except Exception:
            symbol = "UNKNOWN"

        # Assign values
    enriched["decimals"] = decimals
    enriched["symbol"] = symbol

    return enriched


def post_process(account_id: str, enriched_airdrops: List[EnrichedTokenAirdrop]) -> str:
    """Format the enriched airdrop list into a readable Markdown string."""
    count = len(enriched_airdrops)

    if count == 0:
        return f"No pending airdrops found for account {account_id}"

    details = []

    for airdrop in enriched_airdrops:
        symbol = airdrop["symbol"]
        decimals = airdrop["decimals"]

        serial_number = airdrop.get("serial_number")

        if serial_number:
            details.append(f"- **{symbol}** #{serial_number}")
        else:
            amount = Decimal(airdrop.get("amount", 0))
            display_amount_dec = to_display_unit(amount, decimals)
            display_amount_str = f"{display_amount_dec:.{decimals}f}"
            details.append(f"- {display_amount_str} **{symbol}**")

    details_str = "\n".join(details)
    return f"Here are the pending airdrops for account **{account_id}** (total: {count}):\n\n{details_str}"


async def get_pending_airdrop_query(
        client: Client,
        context: Context,
        params: PendingAirdropQueryParameters,
) -> ToolResponse:
    """Execute a pending airdrop query using the mirrornode service."""
    try:
        parsed_params: PendingAirdropQueryParameters = cast(
            PendingAirdropQueryParameters,
            HederaParameterNormaliser.parse_params_with_schema(
                params, PendingAirdropQueryParameters
            ),
        )

        account_id = parsed_params.account_id or AccountResolver.get_default_account(
            context, client
        )

        if not account_id:
            raise ValueError("Account ID is required and was not provided")

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # 1. Fetch the list of pending airdrops
        response: TokenAirdropsResponse = await mirrornode_service.get_pending_airdrops(
            account_id
        )

        # 2. Parallel Fetch & Enrich
        raw_airdrops = response.get("airdrops", [])

        tasks = [
            enrich_single_airdrop(airdrop, mirrornode_service)
            for airdrop in raw_airdrops
        ]

        gathered_airdrops = await asyncio.gather(*tasks)

        # 3. Return ToolResponse
        enriched_response: EnrichedTokenAirdropsResponse = {
            "airdrops": list(gathered_airdrops),
        }

        return ToolResponse(
            human_message=post_process(account_id, list(gathered_airdrops)),
            extra={"accountId": account_id, "pending_airdrops": enriched_response},
        )

    except Exception as e:
        desc = "Failed to get pending airdrops"
        message = f"{desc}: {str(e)}"
        print("[get_pending_airdrop_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )

GET_PENDING_AIRDROP_QUERY_TOOL: str = "get_pending_airdrop_query_tool"


class GetPendingAirdropQueryTool(Tool):
    """Tool wrapper that exposes the pending airdrop query capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = GET_PENDING_AIRDROP_QUERY_TOOL
        self.name: str = "Get Pending Airdrops"
        self.description: str = get_pending_airdrop_query_prompt(context)
        self.parameters: type[PendingAirdropQueryParameters] = (
            PendingAirdropQueryParameters
        )
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: PendingAirdropQueryParameters
    ) -> ToolResponse:
        return await get_pending_airdrop_query(client, context, params)