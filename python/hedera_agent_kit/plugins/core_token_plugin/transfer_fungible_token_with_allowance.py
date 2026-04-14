"""Utilities for building and executing fungible token allowance transfer operations via the Agent Kit.

This module exposes:
- transfer_fungible_token_with_allowance_prompt: Generate a prompt/description for the tool.
- transfer_fungible_token_with_allowance: Execute a fungible token transfer using allowance.
- TransferFungibleTokenWithAllowanceTool: Tool wrapper exposing the operation to the runtime.
"""

from __future__ import annotations

from typing import Any

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenWithAllowanceParameters,
    TransferFungibleTokenWithAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def transfer_fungible_token_with_allowance_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the transfer fungible token with allowance tool."""
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool transfers Fungible Tokens **on behalf of another account** using a pre-approved **Allowance**.

Use this tool ONLY when:
- The request involves spending from a "source account" that is NOT the current signer.
- The user explicitly mentions "allowance", "delegated transfer", or "spending limit".
- You are moving funds *from* a specific owner *to* a recipient using previously granted permissions.

Do NOT use this tool for:
- Standard direct transfers of ERC20 tokens (use the ERC20 tool).
- Standard direct transfers of HTS tokens where the signer owns the tokens.

Parameters:
- token_id (string, required): The token ID to transfer (e.g. "0.0.12345")
- source_account_id (string, required): Account ID of the token owner (the allowance granter).
- transfers (array of objects, required): List of token transfers. Each object should contain:
  - account_id (string): Recipient account ID
  - amount (number): Amount of tokens to transfer in display unit
- transaction_memo (string, optional): Optional memo for the transaction
{PromptGenerator.get_scheduled_transaction_params_description(context)}

{usage_instructions}

Example: "Spend allowance from account 0.0.1002 to send 25 tokens (token id: 0.0.123123) to 0.0.2002"
Example: "Spend allowance from account 0.0.1002 to send 25 fungible tokens with id 0.0.33333 to 0.0.2002"
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


TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL: str = (
    "transfer_fungible_token_with_allowance_tool"
)


class TransferFungibleTokenWithAllowanceTool(BaseToolV2):
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

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> TransferFungibleTokenWithAllowanceParametersNormalised:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        return await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
            params, context, client, mirrornode_service
        )

    async def core_action(
        self,
        normalized_params: TransferFungibleTokenWithAllowanceParametersNormalised,
        client: Client,
        context: Context,
    ) -> Transaction:
        return HederaBuilder.transfer_fungible_token_with_allowance(normalized_params)

    async def secondary_action(
        self,
        transaction: Transaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
