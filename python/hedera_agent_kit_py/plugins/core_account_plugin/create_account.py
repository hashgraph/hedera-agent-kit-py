"""Utilities for building and executing account creation operations via the Agent Kit.

This module exposes:
- create_account_prompt: Generate a prompt/description for the create account tool.
- create_account: Execute an account creation transaction.
- CreateAccountTool: Tool wrapper exposing the account creation operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParameters,
    CreateAccountParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


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

Parameters:
- public_key (str, optional): Public key to use for the account. If not provided, the tool will use the operator's public key.
- account_memo (str, optional): Optional memo for the account
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
    account_id_str = (
        str(response.account_id) if response.account_id else "unknown"
    )
    return (
        f"Account created successfully.\n"
        f"Transaction ID: {response.transaction_id}\n"
        f"New Account ID: {account_id_str}"
    )


async def create_account(
    client: Client,
    context: Context,
    params: CreateAccountParameters,
) -> ToolResponse:
    """Execute an account creation using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the account to create.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
        It accepts raw params, validates, and normalizes them before performing the transaction.
    """
    try:
        # Normalize parameters
        normalised_params: CreateAccountParametersNormalised = (
            await HederaParameterNormaliser.normalise_create_account(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.create_account(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to create account: {str(e)}"
        print("[create_account_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


CREATE_ACCOUNT_TOOL: str = "create_account_tool"


class CreateAccountTool(Tool):
    """Tool wrapper that exposes the account creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = CREATE_ACCOUNT_TOOL
        self.name: str = CREATE_ACCOUNT_TOOL
        self.description: str = create_account_prompt(context)
        self.parameters: type[CreateAccountParameters] = CreateAccountParameters

    async def execute(
        self, client: Client, context: Context, params: CreateAccountParameters
    ) -> ToolResponse:
        """Execute the account creation using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Account creation parameters accepted by this tool.

        Returns:
            The result of the account creation as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await create_account(client, context, params)
