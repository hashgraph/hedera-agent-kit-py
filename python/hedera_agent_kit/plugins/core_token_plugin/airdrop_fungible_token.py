"""Utilities for building and executing fungible token airdrop operations via the Agent Kit.

This module exposes:
- airdrop_fungible_token_prompt: Generate a prompt/description for the airdrop fungible token tool.
- airdrop_fungible_token: Execute a token airdrop transaction.
- AirdropFungibleTokenTool: Tool wrapper exposing the airdrop fungible token operation to the runtime.
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
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    AirdropFungibleTokenParameters,
    AirdropFungibleTokenParametersNormalised,
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


def airdrop_fungible_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the airdrop fungible token tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_params_desc: str = (
        PromptGenerator.get_scheduled_transaction_params_description(context)
    )

    return f"""
{context_snippet}

This tool will airdrop a fungible token on Hedera.

Parameters:
- token_id (str, required): The id of the token
- {source_account_desc}
- recipients (array, required): A list of recipient objects, each containing:
  - account_id (string): The recipient's account ID (e.g., "0.0.1234")
  - amount (number or string): The amount of tokens to send to that recipient (in display units, the tool will parse them itself)
- transaction_memo (str, optional): Optional memo for the transaction
{scheduled_params_desc}
{usage_instructions}

If the user specifies multiple recipients in a single request, include them all in **one tool call** as a list of recipients.
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a fungible token airdrop result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    if response.schedule_id:
        return f"""Scheduled transaction created successfully.
Transaction ID: {response.transaction_id}
Schedule ID: {response.schedule_id}"""

    return f"""Token successfully airdropped with transaction id {response.transaction_id}"""


AIRDROP_FUNGIBLE_TOKEN_TOOL: str = "airdrop_fungible_token_tool"


class AirdropFungibleTokenTool(BaseToolV2):
    """Tool wrapper that exposes the fungible token airdrop capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = AIRDROP_FUNGIBLE_TOKEN_TOOL
        self.name: str = "Airdrop Fungible Token"
        self.description: str = airdrop_fungible_token_prompt(context)
        self.parameters: type[AirdropFungibleTokenParameters] = (
            AirdropFungibleTokenParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> AirdropFungibleTokenParametersNormalised:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        return await HederaParameterNormaliser.normalise_airdrop_fungible_token_params(
            params, context, client, mirrornode_service
        )

    async def core_action(
        self,
        normalized_params: AirdropFungibleTokenParametersNormalised,
        client: Client,
        context: Context,
    ) -> Transaction:
        return HederaBuilder.airdrop_fungible_token(normalized_params)

    async def secondary_action(
        self,
        transaction: Transaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
