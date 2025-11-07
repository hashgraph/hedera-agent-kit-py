"""Utilities for querying Hedera network exchange rates via the Agent Kit.

This module exposes:
- get_exchange_rate_prompt: Generate a prompt/description for the get exchange rate tool.
- get_exchange_rate_query: Execute an exchange rate query.
- GetExchangeRateTool: Tool wrapper exposing the exchange rate query operation to the runtime.
"""

from __future__ import annotations

from datetime import datetime

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import (
    ExchangeRateResponse,
)
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import ExchangeRateQueryParameters
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def get_exchange_rate_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get exchange rate tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool retrieves the current or historical HBAR exchange rate from the Hedera Mirror Node.

Parameters:
- timestamp (str, optional): Historical timestamp to query. Pass seconds or nanos since epoch
  (e.g., 1726000000.123456789). If omitted, returns the latest rate.
{usage_instructions}
"""


def _calculate_usd_per_hbar(cent_equivalent: int, hbar_equivalent: int) -> float:
    """Calculate USD per HBAR."""
    return (cent_equivalent / 100) / hbar_equivalent


def post_process(rates: ExchangeRateResponse) -> str:
    """Produce a human-readable summary for an exchange rate query result.

    Args:
        rates: The exchange rate response returned by the mirrornode API.

    Returns:
        A formatted markdown string describing the current and next exchange rates.
    """
    current_rate = rates.get("current_rate", {})
    next_rate = rates.get("next_rate", {})
    timestamp = rates.get("timestamp", "N/A")

    usd_per_hbar = _calculate_usd_per_hbar(
        current_rate.get("cent_equivalent", 0),
        current_rate.get("hbar_equivalent", 1),
    )
    next_usd_per_hbar = _calculate_usd_per_hbar(
        next_rate.get("cent_equivalent", 0),
        next_rate.get("hbar_equivalent", 1),
    )

    current_expiry = (
        datetime.fromtimestamp(current_rate.get("expiration_time", 0)).isoformat()
        if current_rate.get("expiration_time")
        else "N/A"
    )
    next_expiry = (
        datetime.fromtimestamp(next_rate.get("expiration_time", 0)).isoformat()
        if next_rate.get("expiration_time")
        else "N/A"
    )

    return f"""Exchange Rate Details for timestamp: **{timestamp}**

**Current Rate**
- USD per HBAR: {usd_per_hbar:.6f}
- Expires at: {current_expiry}

**Next Rate**
- USD per HBAR: {next_usd_per_hbar:.6f}
- Expires at: {next_expiry}
"""


async def get_exchange_rate_query(
    client: Client,
    context: Context,
    params: ExchangeRateQueryParameters,
) -> ToolResponse:
    """Execute an exchange rate query using the mirror node service.

    Args:
        client: Hedera client used to determine network/ledger ID.
        context: Runtime context providing configuration and defaults.
        params: Query parameters containing the timestamp to query.

    Returns:
        A ToolResponse wrapping the raw exchange rate data and a human-friendly message.
    """
    try:
        parsed_params: ExchangeRateQueryParameters = (
            HederaParameterNormaliser.normalise_get_exchange_rate(params)
        )

        mirrornode_service: IHederaMirrornodeService = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        rates: ExchangeRateResponse = await mirrornode_service.get_exchange_rate(
            parsed_params.timestamp
        )

        return ToolResponse(
            human_message=post_process(rates),
            extra={"exchange_rate": rates},
        )

    except Exception as e:
        message: str = f"Failed to get exchange rate: {str(e)}"
        print("[get_exchange_rate_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_EXCHANGE_RATE_TOOL: str = "get_exchange_rate_tool"


class GetExchangeRateTool(Tool):
    """Tool wrapper that exposes the exchange rate query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_EXCHANGE_RATE_TOOL
        self.name: str = "Get Exchange Rate"
        self.description: str = get_exchange_rate_prompt(context)
        self.parameters: type[ExchangeRateQueryParameters] = ExchangeRateQueryParameters

    async def execute(
        self, client: Client, context: Context, params: ExchangeRateQueryParameters
    ) -> ToolResponse:
        """Execute the exchange rate query using the provided client, context, and params."""
        if isinstance(params, dict):
            params = ExchangeRateQueryParameters(**params)
        return await get_exchange_rate_query(client, context, params)
