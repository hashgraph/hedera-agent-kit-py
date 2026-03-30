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
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from typing import Any
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


SCHEDULE_DELETE_TOOL = "schedule_delete_tool"


class ScheduleDeleteTool(BaseToolV2):
    def __init__(self, context: Context):
        self.method = SCHEDULE_DELETE_TOOL
        self.name = "Delete Scheduled Transaction"
        self.description = schedule_delete_prompt(context)
        self.parameters = ScheduleDeleteTransactionParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> ScheduleDeleteTransactionParametersNormalised:
        return HederaParameterNormaliser.normalise_schedule_delete_transaction(params)

    async def core_action(
        self,
        normalized_params: ScheduleDeleteTransactionParametersNormalised,
        context: Context,
        client: Client,
    ) -> ScheduleDeleteTransaction:
        return HederaBuilder.delete_schedule_transaction(normalized_params)

    async def secondary_action(
        self, transaction: ScheduleDeleteTransaction, client: Client, context: Context
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message: str = f"Failed to delete a schedule: {str(error)}"
        print("[schedule_delete_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )
