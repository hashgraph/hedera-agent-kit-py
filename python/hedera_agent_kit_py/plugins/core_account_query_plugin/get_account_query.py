"""Utilities for querying account information via the Mirror Node.

This module exposes:
- get_account_query_prompt: Generate a prompt/description for the get account query tool.
- get_account_query: Execute an account query via the Mirror Node.
- GetAccountQueryTool: Tool wrapper exposing the account query operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import AccountResponse
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import AccountQueryParameters
from hedera_agent_kit_py.shared.parameter_schemas.account_schema import (
    AccountQueryParametersNormalised,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import untyped_query_output_parser
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def get_account_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get account query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the account information for a given Hedera account.

Parameters:
- account_id (str, required): The account ID to query
{usage_instructions}
"""


def post_process(account: AccountResponse) -> str:
    """Produce a human-readable summary for an account query result.

    Args:
        account: The account response from the Mirror Node.

    Returns:
        A formatted string describing the account details.
    """
    return f"""Details for {account['account_id']}
Balance: {account['balance']['balance']}
Public Key: {account['account_public_key']}
EVM address: {account['evm_address']}
"""


async def get_account_query(
    client: Client,
    context: Context,
    params: AccountQueryParameters,
) -> ToolResponse:
    """Execute an account query using the Mirror Node service.

    Args:
        client: Hedera client used to determine the network.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the account to query.

    Returns:
        A ToolResponse wrapping the raw account response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        parsed_params: AccountQueryParametersNormalised = (
            HederaParameterNormaliser.normalise_get_account_query(params)
        )
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        account = await mirrornode_service.get_account(parsed_params.account_id)
        return ToolResponse(
            extra={"account_id": parsed_params.account_id, "account": account},
            human_message=post_process(account),
        )
    except Exception as e:
        message: str = f"Failed to get account query: {str(e)}"
        print("[get_account_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_ACCOUNT_QUERY_TOOL: str = "get_account_query_tool"


class GetAccountQueryTool(Tool):
    """Tool wrapper that exposes the account query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_ACCOUNT_QUERY_TOOL
        self.name: str = "Get Account Query"
        self.description: str = get_account_query_prompt(context)
        self.parameters: type[AccountQueryParameters] = AccountQueryParameters
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: AccountQueryParameters
    ) -> ToolResponse:
        """Execute the account query using the provided client, context, and params.

        Args:
            client: Hedera client used to determine the network.
            context: Runtime context providing configuration and defaults.
            params: Account query parameters accepted by this tool.

        Returns:
            The result of the account query as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await get_account_query(client, context, params)
