"""Utilities for building and executing topic creation operations via the Agent Kit.

This module exposes:
- create_topic_prompt: Generate a prompt/description for the create topic tool.
- create_topic: Execute a topic creation transaction.
- CreateTopicTool: Tool wrapper exposing the create topic operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.consensus.topic_create_transaction import TopicCreateTransaction

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
    CreateTopicParameters,
    CreateTopicParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def create_topic_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the create topic tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
This tool will create a new topic on the Hedera network.

Parameters:
- topic_memo (str, optional): A memo for the topic.
- transaction_memo (str, optional): An optional memo to include on the submitted transaction.
- submit_key (bool or str, optional): Submit key for the topic. Pass boolean `true` to use the operator/user key,
  or provide a Hedera-compatible public key string. Defaults to None (no submit key).
- admin_key (bool or str, optional): Admin key for the topic. Pass boolean `true` to use the operator/user key,
  or provide a Hedera-compatible public key string. Defaults to true (operator key).

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a topic creation result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status, topic ID, and transaction ID.
    """
    topic_id_str = (
        str(response.topic_id) if hasattr(response, "topic_id") else "unknown"
    )
    return f"Topic created successfully with topic id {topic_id_str} and transaction id {response.transaction_id}"


async def create_topic(
    client: Client,
    context: Context,
    params: CreateTopicParameters,
) -> ToolResponse:
    """Execute a topic creation using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the topic creation to perform.

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
        normalised_params: CreateTopicParametersNormalised = (
            await HederaParameterNormaliser.normalise_create_topic_params(
                params, context, client
            )
        )

        # Build transaction
        tx: TopicCreateTransaction = HederaBuilder.create_topic(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to create topic: {str(e)}"
        print("[create_topic_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


CREATE_TOPIC_TOOL: str = "create_topic_tool"


class CreateTopicTool(Tool):
    """Tool wrapper that exposes the topic creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = CREATE_TOPIC_TOOL
        self.name: str = "Create Topic"
        self.description: str = create_topic_prompt(context)
        self.parameters: type[CreateTopicParameters] = CreateTopicParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: CreateTopicParameters
    ) -> ToolResponse:
        """Execute the topic creation using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Topic creation parameters accepted by this tool.

        Returns:
            The result of the creation as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await create_topic(client, context, params)
