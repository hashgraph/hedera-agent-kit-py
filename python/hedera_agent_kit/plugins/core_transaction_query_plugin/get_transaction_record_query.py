"""Utilities for querying transaction records via the Agent Kit.

This module exposes:
- get_transaction_record_query_prompt: Generate a prompt/description for the get transaction record tool.
- get_transaction_record_query: Execute a transaction record query.
- GetTransactionRecordQueryTool: Tool wrapper exposing the transaction record query to the runtime.
"""

from __future__ import annotations

from typing import Dict, Any

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.hedera_utils.mirrornode.types.transaction import (
    TransactionDetailsResponse,
)
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    TransactionRecordQueryParameters,
    TransactionRecordQueryParametersNormalised,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def get_transaction_record_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get transaction record tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the transaction record for a given Hedera transaction ID.

Parameters:
- transaction_id (str, required): The transaction ID to fetch record for. Should be in format "shard.realm.num-sss-nnn" format where sss are seconds and nnn are nanoseconds
- nonce (number, optional): Optional nonce value for the transaction

{usage_instructions}

Additional information:
If user provides transaction ID in format 0.0.4177806@1755169980.051721264, parse it to 0.0.4177806-1755169980-051721264 and use it as transaction ID. Do not remove the starting zeros.
"""


def to_display_unit(amount: int, decimals: int) -> str:
    """Convert an amount from smallest unit to display unit.

    Args:
        amount: The amount in smallest units (e.g., tinybars).
        decimals: Number of decimal places (e.g., 8 for HBAR).

    Returns:
        A string representation of the amount in display units.
    """
    from decimal import Decimal

    divisor = Decimal(10**decimals)
    display_amount = Decimal(amount) / divisor
    return str(display_amount)


def post_process(
    transaction_record: TransactionDetailsResponse, transaction_id: str
) -> str:
    """Produce a human-readable summary for a transaction record query result.

    Args:
        transaction_record: The transaction record details from the mirror node.
        transaction_id: The transaction ID that was queried.

    Returns:
        A formatted message describing the transaction record(s).
    """
    transactions = transaction_record.get("transactions", [])

    if not transactions:
        return f"No transaction details found for transaction ID: {transaction_id}"

    results = []
    for index, tx in enumerate(transactions):
        transfers_info = ""
        if tx.get("transfers"):
            transfer_lines = []
            for transfer in tx["transfers"]:
                account = transfer["account"]
                amount_tinybars = transfer["amount"]
                amount_hbar = to_display_unit(amount_tinybars, 8)
                transfer_lines.append(f"  Account: {account}, Amount: {amount_hbar}ℏ")
            transfers_info = "\nTransfers:\n" + "\n".join(transfer_lines)

        transaction_header = (
            f"Transaction {index + 1} Details for {transaction_id}"
            if len(transactions) > 1
            else f"Transaction Details for {transaction_id}"
        )

        result = f"""{transaction_header}
Status: {tx.get('result', 'N/A')}
Consensus Timestamp: {tx.get('consensus_timestamp', 'N/A')}
Transaction Hash: {tx.get('transaction_hash', 'N/A')}
Transaction Fee: {tx.get('charged_tx_fee', 'N/A')}
Type: {tx.get('name', 'N/A')}
Entity ID: {tx.get('entity_id', 'N/A')}{transfers_info}"""

        results.append(result)

    return "\n\n" + "=" * 50 + "\n\n".join([""] + results)


async def get_transaction_record_query(
    client: Client, context: Context, params: TransactionRecordQueryParameters
) -> ToolResponse:
    """Execute a transaction record query using the mirror node service.

    Args:
        client: Hedera client used for network information.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the transaction to query.

    Returns:
        A ToolResponse wrapping the raw transaction record data and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
    """
    try:
        normalised_params: TransactionRecordQueryParametersNormalised = (
            HederaParameterNormaliser.normalise_get_transaction_record_params(params)
        )

        # Get mirrornode service
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        # Query transaction record
        transaction_record: TransactionDetailsResponse = (
            await mirrornode_service.get_transaction_record(
                normalised_params.transaction_id,
                normalised_params.nonce,
            )
        )

        return ToolResponse(
            human_message=post_process(
                transaction_record, params.get("transaction_id")
            ),
            extra={
                "transaction_id": params["transaction_id"],
                "transaction_record": transaction_record,
            },
        )

    except Exception as e:
        message: str = f"Failed to get transaction record: {str(e)}"
        print("[get_transaction_record_query_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


GET_TRANSACTION_RECORD_QUERY_TOOL: str = "get_transaction_record_query_tool"


class GetTransactionRecordQueryTool(Tool):
    """Tool wrapper that exposes the transaction record query capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = GET_TRANSACTION_RECORD_QUERY_TOOL
        self.name: str = "Get Transaction Record Query"
        self.description: str = get_transaction_record_query_prompt(context)
        self.parameters: type[TransactionRecordQueryParameters] = (
            TransactionRecordQueryParameters
        )
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: TransactionRecordQueryParameters
    ) -> ToolResponse:
        """Execute the transaction record query using the provided client, context, and params.

        Args:
            client: Hedera client used for network information.
            context: Runtime context providing configuration and defaults.
            params: Transaction record query parameters accepted by this tool.

        Returns:
            The result of the transaction record query as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await get_transaction_record_query(client, context, params)
