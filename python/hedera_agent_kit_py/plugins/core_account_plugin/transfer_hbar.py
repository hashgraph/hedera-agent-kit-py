from __future__ import annotations

from hiero_sdk_python import Client, ResponseCode
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import (
    ExecutedTransactionToolResponse,
    ToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def transfer_hbar_prompt(context: Context = {}) -> str:
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This async tool will transfer HBAR to an account.

Parameters:
- transfers (list of dicts, required): Each dict must contain:
    - account_id (str): Recipient account ID
    - amount (float or str): Amount of HBAR to transfer
- {source_account_desc}
- transaction_memo (str, optional): Optional memo for the transfer transaction
{scheduled_desc}

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled HBAR transfer created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return f"HBAR successfully transferred.\nTransaction ID: {response.transaction_id}"


async def transfer_hbar(
    client: Client,
    context: Context,
    params: TransferHbarParameters,
) -> ToolResponse:
    """
    Execute an HBAR transfer.
    """
    try:
        # Normalize parameters
        normalised_params: TransferHbarParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_hbar(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.transfer_hbar(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to transfer HBAR: {str(e)}"
        print("[transfer_hbar_tool]", message)
        return ExecutedTransactionToolResponse(
            raw=RawTransactionResponse(
                status=str(ResponseCode.INVALID_TRANSACTION), error=message
            ),
            human_message=message,
        )


TRANSFER_HBAR_TOOL: str = "transfer_hbar_tool"


class TransferHbarTool(Tool):
    def __init__(self, context: Context):
        self.method: str = TRANSFER_HBAR_TOOL
        self.name: str = TRANSFER_HBAR_TOOL
        self.description: str = transfer_hbar_prompt(context)
        self.parameters: type[TransferHbarParameters] = TransferHbarParameters

    async def execute(
        self, client: Client, context: Context, params: TransferHbarParameters
    ) -> ToolResponse:
        return await transfer_hbar(client, context, params)
