"""Utilities for building and executing token dissociation operations via the Agent Kit.

This module exposes:
- dissociate_token_prompt: Generate a prompt/description for the dissociate token tool.
- dissociate_token: Execute a token dissociation transaction.
- DissociateTokenTool: Tool wrapper exposing the dissociation operation to the runtime.
"""

from __future__ import annotations

from typing import Any

from hiero_sdk_python import Client, TokenDissociateTransaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    RawTransactionResponse,
    ToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    DissociateTokenParameters,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def dissociate_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the dissociate token tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will dissociate one or more tokens from a Hedera account.

Parameters:
- token_ids (array of strings, required): A list of Hedera token IDs to dissociate from the account. Example: ["0.0.1234", "0.0.5678"]
- {source_account_desc}, account from which to dissociate the token(s)
- transaction_memo (str, optional): Optional memo for the transaction

Examples:
- Dissociate a single token: {{ "token_ids": ["0.0.1234"] }}
- Dissociate multiple tokens from a specific account: {{ "token_ids": ["0.0.1234", "0.0.5678"], "account_id": "0.0.4321" }}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a token dissociation result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A message confirming the dissociation.
    """
    return f"Token(s) successfully dissociated with transaction id {response.transaction_id}"


DISSOCIATE_TOKEN_TOOL: str = "dissociate_token_tool"


class DissociateTokenTool(BaseToolV2):
    """Tool wrapper that exposes the token dissociation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata.

        Args:
            context: Runtime context.
        """
        self.method: str = DISSOCIATE_TOKEN_TOOL
        self.name: str = "Dissociate Token"
        self.description: str = dissociate_token_prompt(context)
        self.parameters: type[DissociateTokenParameters] = DissociateTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> Any:
        return await HederaParameterNormaliser.normalise_dissociate_token_params(
            params, context, client
        )

    async def core_action(
        self,
        normalized_params: Any,
        client: Client,
        context: Context,
    ) -> TokenDissociateTransaction:
        return HederaBuilder.dissociate_token(normalized_params)

    async def secondary_action(
        self,
        transaction: TokenDissociateTransaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
