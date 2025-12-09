"""Utilities for building and executing topic deletion operations via the Agent Kit.

This module exposes:
- delete_topic_prompt: Generate a prompt/description for the delete topic tool.
- delete_topic: Execute a topic deletion transaction.
- DeleteTopicTool: Tool wrapper exposing the delete topic operation to the runtime.
"""

from __future__ import annotations

from typing import cast

from hiero_sdk_python import Client
from hiero_sdk_python.consensus.topic_delete_transaction import TopicDeleteTransaction

from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    DeleteTopicParameters,
    DeleteTopicParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
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


def post_process(response: RawTransactionResponse, topic_id: str) -> str:
    """Produce a human-readable summary for a topic deletion result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status and transaction ID.
    """
    return f"Topic with id {topic_id} deleted successfully. Transaction id {response.transaction_id}"


async def delete_topic(
    client: Client,
    context: Context,
    params: DeleteTopicParameters,
) -> ToolResponse:
    """Execute a topic deletion using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the topic deletion to perform.

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
        normalised_params: DeleteTopicParametersNormalised = (
            HederaParameterNormaliser.normalise_delete_topic(
                params,
            )
        )

        # Build transaction
        tx: TopicDeleteTransaction = HederaBuilder.delete_topic(normalised_params)

        # Execute transaction and post-process result
        result = await handle_transaction(tx, client, context)

        if context.mode == AgentMode.RETURN_BYTES:
            return result

        raw_tx_data = cast(ExecutedTransactionToolResponse, result).raw
        human_message = post_process(raw_tx_data, params["topic_id"])

        return ExecutedTransactionToolResponse(
            human_message=human_message,
            raw=raw_tx_data,
        )

    except Exception as e:
        message: str = f"Failed to delete the topic: {str(e)}"
        print("[delete_topic_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


DELETE_TOPIC_TOOL: str = "delete_topic_tool"


class DeleteTopicTool(Tool):
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

    async def execute(
        self, client: Client, context: Context, params: DeleteTopicParameters
    ) -> ToolResponse:
        """Execute the topic deletion using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Topic deletion parameters accepted by this tool.

        Returns:
            The result of the deletion as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await delete_topic(client, context, params)
