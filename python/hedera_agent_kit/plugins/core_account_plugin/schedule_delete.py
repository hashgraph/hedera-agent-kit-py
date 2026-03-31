from __future__ import annotations

from hiero_sdk_python import Client, ScheduleDeleteTransaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    ScheduleDeleteTransactionParameters,
    ScheduleDeleteTransactionParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def schedule_delete_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will delete a scheduled transaction (by admin) so it will not execute.

Parameters:
- schedule_id (string, required): The ID of the scheduled transaction to delete
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"Scheduled transaction successfully deleted. Transaction ID: {response.transaction_id}"


async def schedule_delete(
    client: Client,
    context: Context,
    params: ScheduleDeleteTransactionParameters,
) -> ToolResponse:
    try:
        normalised_params: ScheduleDeleteTransactionParametersNormalised = (
            HederaParameterNormaliser.normalise_schedule_delete_transaction(params)
        )
        tx: ScheduleDeleteTransaction = HederaBuilder.delete_schedule_transaction(
            normalised_params
        )
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        message: str = f"Failed to delete a schedule: {str(e)}"
        print("[schedule_delete_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


SCHEDULE_DELETE_TOOL = "schedule_delete_tool"


class ScheduleDeleteTool(Tool):
    def __init__(self, context: Context):
        self.method = SCHEDULE_DELETE_TOOL
        self.name = "Delete Scheduled Transaction"
        self.description = schedule_delete_prompt(context)
        self.parameters = ScheduleDeleteTransactionParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: ScheduleDeleteTransactionParameters,
    ) -> ToolResponse:
        return await schedule_delete(client, context, params)
