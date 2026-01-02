"""Utilities for building and executing ERC20 transfer operations via the Agent Kit.

This module exposes:
- transfer_erc20_prompt: Generate a prompt/description for the ERC20 transfer tool.
- transfer_erc20: Execute an ERC20 transfer transaction.
- TransferERC20Tool: Tool wrapper exposing the ERC20 transfer operation to the runtime.
"""

from __future__ import annotations

from typing import cast

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    TransferERC20Parameters,
    ContractExecuteTransactionParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.constants.contracts import (
    ERC20_TRANSFER_FUNCTION_ABI,
    ERC20_TRANSFER_FUNCTION_NAME,
)


def transfer_erc20_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the transfer ERC20 tool."""
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This tool executes a direct transfer of **ERC20 tokens** by calling the transfer function on an **EVM Smart Contract**.

Use this tool ONLY when:
- The user explicitly mentions "ERC20".
- The asset is identified by a Contract ID or EVM address.
- The user wants to send tokens *directly* from the connected account (wallet) to a recipient.

Do NOT use this tool for:
- Native Hedera Token Service (HTS) transfers.
- Transferring tokens "on behalf of" another account (use the Allowance tool instead).

**Address Format Rules**:
- **EVM addresses** start with "0x" followed by 40 hexadecimal characters (e.g., "0x1111111111111111111111111111111111111111"). Keep them exactly as given.
- **Hedera account IDs** use the format "0.0.XXXXX" with dots (e.g., "0.0.1234"). Keep them exactly as given.
- NEVER convert between formats. Pass addresses exactly as the user provides them.

Parameters:
- contract_id (str, required): The ERC20 contract identifier. Can be an EVM address (0x...) or Hedera account ID (0.0.XXXX). Pass exactly as provided.
- recipient_address (str, required): The recipient's address. Can be an EVM address (0x...) or Hedera account ID (0.0.XXXX). Pass exactly as provided.
- amount (number, required): The amount to be transferred. Given in base units!
- {scheduled_desc}

{usage_instructions}

Example: "Transfer 1 ERC20 token 0.0.6473135 to 0xd94..." → contract_id="0.0.6473135", recipient_address="0xd94..."
Example: "Send 50 tokens from ERC20 contract 0.0.1234 to account 0.0.5678" → contract_id="0.0.1234", recipient_address="0.0.5678"
Example: "Transfer 10 from EVM contract 0x1111111111111111111111111111111111111111 to Hedera account 0.0.5678" → contract_id="0x1111111111111111111111111111111111111111", recipient_address="0.0.5678"
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for ERC20 transfer results."""
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled transfer of ERC20 successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return "ERC20 token transferred successfully."


async def transfer_erc20(
    client: Client,
    context: Context,
    params: TransferERC20Parameters,
) -> ToolResponse:
    """Execute ERC20 transfer transaction."""
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        normalised_params: ContractExecuteTransactionParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_erc20_params(
                params,
                ERC20_TRANSFER_FUNCTION_ABI,
                ERC20_TRANSFER_FUNCTION_NAME,
                context,
                mirrornode_service,
                client,
            )
        )

        tx: Transaction = HederaBuilder.execute_transaction(normalised_params)
        result = await handle_transaction(tx, client, context)

        if context.mode == AgentMode.RETURN_BYTES:
            return result

        raw_tx_data = cast(ExecutedTransactionToolResponse, result).raw
        human_message = post_process(raw_tx_data)

        return ExecutedTransactionToolResponse(
            human_message=human_message,
            raw=raw_tx_data,
        )

    except Exception as e:
        message = f"Failed to transfer ERC20: {str(e)}"
        print("[transfer_erc20_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_ERC20_TOOL = "transfer_erc20_tool"


class TransferERC20Tool(Tool):
    """Tool wrapper exposing ERC20 transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = TRANSFER_ERC20_TOOL
        self.name: str = "Transfer ERC20 Token"
        self.description: str = transfer_erc20_prompt(context)
        self.parameters: type[TransferERC20Parameters] = TransferERC20Parameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: TransferERC20Parameters
    ) -> ToolResponse:
        return await transfer_erc20(client, context, params)
