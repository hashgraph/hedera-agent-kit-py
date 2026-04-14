"""Utilities for building and executing topic deletion operations via the Agent Kit.

This module exposes:
- delete_topic_prompt: Generate a prompt/description for the delete topic tool.
- delete_topic: Execute a topic deletion transaction.
- DeleteTopicTool: Tool wrapper exposing the delete topic operation to the runtime.
"""

from __future__ import annotations

from typing import Any

from hiero_sdk_python import Client
from hiero_sdk_python.consensus.topic_delete_transaction import TopicDeleteTransaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteTopicParameters,
    DeleteTopicParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def delete_topic_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the delete topic tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
This tool will delete a given Hedera network topic.

Parameters:
- topic_id (str, required): id of topic to delete
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a topic deletion result.

    Args:
        response: The raw response returned by the transaction execution.
        topic_id: The ID of the topic that was deleted.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return f"Topic with id {response.topic_id} deleted successfully. Transaction id {response.transaction_id}"


DELETE_TOPIC_TOOL: str = "delete_topic_tool"


class DeleteTopicTool(BaseToolV2):
    """Tool wrapper that exposes the topic deletion capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = DELETE_TOPIC_TOOL
        self.name: str = "Delete Topic"
        self.description: str = delete_topic_prompt(context)
        self.parameters: type[DeleteTopicParameters] = DeleteTopicParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> DeleteTopicParametersNormalised:
        return HederaParameterNormaliser.normalise_delete_topic(params)

    async def core_action(
        self,
        normalized_params: DeleteTopicParametersNormalised,
        client: Client,
        context: Context,
    ) -> TopicDeleteTransaction:
        return HederaBuilder.delete_topic(normalized_params)

    async def secondary_action(
        self,
        transaction: TopicDeleteTransaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
