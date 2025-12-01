"""Utilities for building and executing fungible token allowance transfer operations via the Agent Kit.

This module exposes:
- transfer_fungible_token_with_allowance_prompt: Generate a prompt/description for the tool.
- transfer_fungible_token_with_allowance: Execute a fungible token transfer using allowance.
- TransferFungibleTokenWithAllowanceTool: Tool wrapper exposing the operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, TransferTransaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenWithAllowanceParameters,
    TransferFungibleTokenWithAllowanceParametersNormalised,
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


def transfer_fungible_token_with_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the transfer fungible token with allowance tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will transfer a fungible token using an existing **token allowance**.

Parameters:
- token_id (string, required): The token ID to transfer (e.g. "0.0.12345")
- source_account_id (string, required): Account ID of the token owner (the allowance granter)
- transfers (array of objects, required): List of token transfers. Each object should contain:
  - account_id (string): Recipient account ID
  - amount (number): Amount of tokens to transfer in display unit
- transaction_memo (string, optional): Optional memo for the transaction
{PromptGenerator.get_scheduled_transaction_params_description(context)}

{usage_instructions}

Example: Spend allowance from account 0.0.1002 to send 25 fungible tokens with id 0.0.33333 to 0.0.2002
Example 2: Use allowance from 0.0.1002 to send 50 TKN (FT token id: '0.0.33333') to 0.0.2002 and 75 TKN to 0.0.3003
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a fungible token allowance transfer.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A message confirming the transaction.
    """
    if response.schedule_id:
        return f"""Scheduled allowance transfer created successfully.
Transaction ID: {response.transaction_id}
Schedule ID: {response.schedule_id}"""
    return f"Fungible tokens successfully transferred with allowance. Transaction ID: {response.transaction_id}"


async def transfer_fungible_token_with_allowance(
    client: Client,
    context: Context,
    params: TransferFungibleTokenWithAllowanceParameters,
) -> ToolResponse:
    """Execute a fungible token transfer using allowance.

    Args:
        client: Hedera client.
        context: Runtime context.
        params: Transfer parameters.

    Returns:
        A ToolResponse wrapping the transaction result.
    """
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        normalised_params: TransferFungibleTokenWithAllowanceParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
                params, context, client, mirrornode_service
            )
        )

        tx = HederaBuilder.transfer_fungible_token_with_allowance(normalised_params)

        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        desc = "Failed to transfer fungible token with allowance"
        message = f"{desc}: {str(e)}"
        print("[transfer_fungible_token_with_allowance_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )


TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL: str = (
    "transfer_fungible_token_with_allowance_tool"
)


class TransferFungibleTokenWithAllowanceTool(Tool):
    """Tool wrapper that exposes the fungible token allowance transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool.

        Args:
            context: Runtime context.
        """
        self.method: str = TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
        self.name: str = "Transfer Fungible Token with Allowance"
        self.description: str = transfer_fungible_token_with_allowance_prompt(context)
        self.parameters: type[TransferFungibleTokenWithAllowanceParameters] = (
            TransferFungibleTokenWithAllowanceParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: TransferFungibleTokenWithAllowanceParameters,
    ) -> ToolResponse:
        """Execute the transfer using the provided client, context, and params.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Transfer parameters.

        Returns:
            The result of the transaction.
        """
        return await transfer_fungible_token_with_allowance(client, context, params)
