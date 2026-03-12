"""Utilities for building and executing account creation operations via the Agent Kit.

This module exposes:
- create_account_prompt: Generate a prompt/description for the create account tool.
- create_account: Execute an account creation transaction.
- CreateAccountTool: Tool wrapper exposing the account creation operation to the runtime.
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
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParameters,
    CreateAccountParametersNormalised,
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


def create_account_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the create account tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information or scheduling capabilities.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This tool will create a new Hedera account with a passed public key. If not passed, the tool will use operator's public key.

IMPORTANT: All parameters are optional. If the user does not explicitly provide optional parameters, proceed immediately using the default values. Do NOT ask the user for optional parameters.

Parameters:
- public_key (str, optional): Public key to use for the account. If not provided, the tool will use the operator's public key.
- account_memo (str, optional): Optional memo for the account. Can be up to 100 characters long. Too long memos will be truncated in params normalization
- initial_balance (float, optional, default 0): Initial HBAR to fund the account
- max_automatic_token_associations (int, optional, default -1): -1 means unlimited
{scheduled_desc}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for an account creation result.

    Args:
        response: The raw response returned by the transaction execution, which
            may contain a schedule_id if the transaction was scheduled.

    Returns:
        A concise message describing the status and any relevant identifiers
        (e.g., transaction ID, account ID, schedule ID).
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled transaction created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    account_id_str = str(response.account_id) if response.account_id else "unknown"
    return (
        f"Account created successfully.\n"
        f"Transaction ID: {response.transaction_id}\n"
        f"New Account ID: {account_id_str}"
    )


CREATE_ACCOUNT_TOOL: str = "create_account_tool"


class CreateAccountTool(BaseToolV2):
    """Tool wrapper that exposes the account creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = CREATE_ACCOUNT_TOOL
        self.name: str = "Create Account"
        self.description: str = create_account_prompt(context)
        self.parameters: type[CreateAccountParameters] = CreateAccountParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> CreateAccountParametersNormalised:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        return await HederaParameterNormaliser.normalise_create_account(
            params, context, client, mirrornode_service
        )

    async def core_action(
        self,
        normalized_params: CreateAccountParametersNormalised,
        context: Context,
        client: Client,
    ) -> Transaction:
        return HederaBuilder.create_account(normalized_params)

    async def secondary_action(
        self, transaction: Transaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        desc = "Failed to create account"
        message = f"{desc}: {str(error)}"
        print(f"[create_account_tool] {message}")
        return ToolResponse(
            error=message,
            human_message=message,
        )
