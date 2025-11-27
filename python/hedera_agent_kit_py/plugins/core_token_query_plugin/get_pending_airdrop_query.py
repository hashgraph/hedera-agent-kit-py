"""Utilities for querying pending airdrops via the Agent Kit.

This module exposes:
- get_pending_airdrop_query_prompt: Generate a prompt/description for the get pending airdrop query tool.
- get_pending_airdrop_query: Execute a pending airdrop query.
- GetPendingAirdropQueryTool: Tool wrapper exposing the pending airdrop query operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import (
    TokenAirdrop,
    TokenAirdropsResponse,
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


def get_pending_airdrop_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get pending airdrop query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

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

This tool will return pending airdrops for a given Hedera account.

Parameters:
- {account_desc}
{usage_instructions}
"""


def format_airdrop(airdrop: TokenAirdrop, index: int) -> str:
    """Format a single airdrop record for display.

    Args:
        airdrop: The airdrop dictionary from the mirror node.
        index: The index of the airdrop in the list.

    Returns:
        A formatted string describing the airdrop.
    """
    token = airdrop.get("token_id", "N/A")
    amount = airdrop.get("amount", 0)
    serial = airdrop.get("serial_number", "N/A")
    sender = airdrop.get("sender_id", "N/A")
    receiver = airdrop.get("receiver_id", "N/A")

    timestamp = airdrop.get("timestamp", {})
    from_ts = timestamp.get("from_", "N/A")
    to_ts = timestamp.get("to", "N/A")

    time_range = f"{from_ts}"
    if to_ts:
        time_range += f" -> {to_ts}"

    return (
        f"#{index + 1} Token: {token}, Amount: {amount}, Serial: {serial}, "
        f"Sender: {sender}, Receiver: {receiver}, Timestamp: {time_range}"
    )


def post_process(account_id: str, response: TokenAirdropsResponse) -> str:
    """Produce a human-readable summary for a pending airdrop query result.

    Args:
        account_id: The account ID that was queried.
        response: The response from the mirrornode API.

    Returns:
        A formatted markdown message describing the pending airdrops.
    """
    airdrops = response.get("airdrops", [])
    count = len(airdrops)

    if count == 0:
        return f"No pending airdrops found for account {account_id}"

    details = "\n".join(
        format_airdrop(airdrop, i) for i, airdrop in enumerate(airdrops)
    )
    return f"Here are the pending airdrops for account **{account_id}** (total: {count}):\n\n{details}"


async def get_pending_airdrop_query(
    client: Client,
    context: Context,
    params: PendingAirdropQueryParameters,
) -> ToolResponse:
    """Execute a pending airdrop query using the mirrornode service.

    Args:
        client: Hedera client.
        context: Runtime context.
        params: Query parameters.

    Returns:
        A ToolResponse with pending airdrop details.
    """
    try:
        account_id = params["account_id"] or AccountResolver.get_default_account(
            context, client
        )
        if not account_id:
            raise ValueError("Account ID is required and was not provided")

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Fetch pending airdrops
        response: TokenAirdropsResponse = await mirrornode_service.get_pending_airdrops(
            account_id
        )

        return ToolResponse(
            human_message=post_process(account_id, response),
            extra={"accountId": account_id, "pendingAirdrops": response},
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
        """Initialize the tool metadata.

        Args:
            context: Runtime context.
        """
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
        """Execute the pending airdrop query.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Query parameters.

        Returns:
            The query result.
        """
        return await get_pending_airdrop_query(client, context, params)
