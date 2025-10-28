from typing import Any, Dict

from hiero_sdk_python import Client, ResponseCode

from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.parameter_schemas import TransferHbarParameters
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def transfer_hbar_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    source_account_desc = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc = PromptGenerator.get_scheduled_transaction_params_description(
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
) -> Dict[str, Any]:
    """
    Execute an HBAR transfer.
    """
    try:
        # Normalize parameters
        normalised_params = await HederaParameterNormaliser.normalise_transfer_hbar(
            params, context, client
        )

        # Build transaction
        tx = HederaBuilder.transfer_hbar(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message = f"Failed to transfer HBAR: {str(e)}"
        print("[transfer_hbar_tool]", message)
        return {
            "raw": {
                "status": str(ResponseCode.INVALID_TRANSACTION),
                "error": message,
            },
            "human_message": message,
        }


TRANSFER_HBAR_TOOL = "transfer_hbar_tool"


class TransferHbarTool(Tool):
    def __init__(self, context: Context):
        self.method = TRANSFER_HBAR_TOOL
        self.name = TRANSFER_HBAR_TOOL
        self.description = transfer_hbar_prompt(context)
        self.parameters = TransferHbarParameters

    async def execute(self, client: Client, context: Context, params: Any) -> Any:
        return await transfer_hbar(client, context, params)
