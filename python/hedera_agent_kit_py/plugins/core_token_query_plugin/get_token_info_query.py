"""Utilities for querying Hedera token information via the Agent Kit.

This module exposes:
- get_token_info_query_prompt: Generate a prompt/description for the get token info query tool.
- get_token_info_query: Execute a token info query.
- GetTokenInfoQueryTool: Tool wrapper exposing the token info query operation to the runtime.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import TokenInfo
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    GetTokenInfoParameters,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def get_token_info_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get token info query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the information for a given Hedera token. Make sure to return token symbol.

Parameters:
- token_id (str): The token ID to query for.
{usage_instructions}
"""


def format_supply(supply: Optional[str], decimals_str: Optional[str]) -> str:
    """Format the token supply applying decimals.

    Args:
        supply: The raw supply string from the mirror node.
        decimals_str: The string representation of the token decimals.

    Returns:
        A formatted string representing the human-readable supply.
    """
    if not supply:
        return "N/A"

    if not decimals_str:
        return "the token has no supplied decimals"

    if decimals_str == "0":
        return supply

    try:
        decimals = int(decimals_str)
        amount = float(supply)
        calculated = amount / (10**decimals)
        # Format with commas
        return (
            f"{calculated:,.{decimals}f}".rstrip("0").rstrip(".")
            if "." in f"{calculated}"
            else f"{calculated:,.0f}"
        )
    except (ValueError, TypeError):
        return supply


def format_key(key: Optional[Dict[str, Any]]) -> str:
    """Format a key object for display.

    Args:
        key: The key dictionary from the mirror node response.

    Returns:
        A formatted string describing the key.
    """
    if not key:
        return "Not Set"
    if key.get("_type"):
        return str(key.get("key", "Present"))
    return "Present"


def post_process(token_info: TokenInfo) -> str:
    """Produce a human-readable summary for a token info query result.

    Args:
        token_info: The token info returned by the mirrornode API.

    Returns:
        A formatted markdown message describing the token details.
    """
    token_id = token_info.get("token_id", "N/A")
    name = token_info.get("name", "N/A")
    symbol = token_info.get("symbol", "N/A")
    token_type = token_info.get("type", "N/A")

    decimals_str = str(token_info.get("decimals", "0"))
    max_supply = format_supply(token_info.get("max_supply"), decimals_str)
    total_supply = format_supply(token_info.get("total_supply"), decimals_str)

    supply_type_raw = token_info.get("supply_type", "")
    supply_type = "Infinite" if supply_type_raw == "INFINITE" else "Finite"

    freeze_status = "Frozen" if token_info.get("freeze_default") else "Active"
    deleted_status = "Deleted" if token_info.get("deleted") else "Active"
    treasury = token_info.get("treasury_account_id", "N/A")

    # Keys
    admin_key = format_key(token_info.get("admin_key"))
    supply_key = format_key(token_info.get("supply_key"))
    wipe_key = format_key(token_info.get("wipe_key"))
    kyc_key = format_key(token_info.get("kyc_key"))
    freeze_key = format_key(token_info.get("freeze_key"))
    fee_schedule_key = format_key(token_info.get("fee_schedule_key"))
    pause_key = format_key(token_info.get("pause_key"))
    metadata_key = format_key(token_info.get("metadata_key"))

    memo_section = ""
    if token_info.get("memo"):
        memo_section = f"\n**Memo**: {token_info.get('memo')}"

    return f"""Here are the details for token **{token_id}**:

- **Token Name**: {name}
- **Token Symbol**: {symbol}
- **Token Type**: {token_type}
- **Decimals**: {decimals_str}
- **Max Supply**: {max_supply}
- **Current Supply**: {total_supply}
- **Supply Type**: {supply_type}
- **Treasury Account ID**: {treasury}
- **Status (Deleted/Active)**: {deleted_status}
- **Status (Frozen/Active)**: {freeze_status}

**Keys**:
- Admin Key: {admin_key}
- Supply Key: {supply_key}
- Wipe Key: {wipe_key}
- KYC Key: {kyc_key}
- Freeze Key: {freeze_key}
- Fee Schedule Key: {fee_schedule_key}
- Pause Key: {pause_key}
- Metadata Key: {metadata_key}
{memo_section}
"""


async def get_token_info_query(
    client: Client,
    context: Context,
    params: GetTokenInfoParameters,
) -> ToolResponse:
    """Execute a token info query using the mirrornode service.

    Args:
        client: Hedera client.
        context: Runtime context.
        params: Query parameters.

    Returns:
        A ToolResponse with token details.
    """
    try:
        parsed_params = HederaParameterNormaliser.normalise_get_token_info(params)

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Fetch token info
        token_info: TokenInfo = await mirrornode_service.get_token_info(
            parsed_params.token_id
        )

        # Ensure token_id is present in the dict
        if token_info["token_id"] is None:
            token_info["token_id"] = parsed_params.token_id

        return ToolResponse(
            human_message=post_process(token_info),
            extra={"tokenInfo": token_info, "tokenId": parsed_params.token_id},
        )

    except Exception as e:
        desc = "Failed to get token info"
        message = f"{desc}: {str(e)}"
        print("[get_token_info_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_TOKEN_INFO_QUERY_TOOL: str = "get_token_info_query_tool"


class GetTokenInfoQueryTool(Tool):
    """Tool wrapper that exposes the token info query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata.

        Args:
            context: Runtime context.
        """
        self.method: str = GET_TOKEN_INFO_QUERY_TOOL
        self.name: str = "Get Token Info"
        self.description: str = get_token_info_query_prompt(context)
        self.parameters: type[GetTokenInfoParameters] = GetTokenInfoParameters
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: GetTokenInfoParameters
    ) -> ToolResponse:
        """Execute the token info query.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Query parameters.

        Returns:
            The query result.
        """
        return await get_token_info_query(client, context, params)
