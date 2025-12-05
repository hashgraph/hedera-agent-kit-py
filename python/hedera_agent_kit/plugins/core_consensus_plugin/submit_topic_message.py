"""Utilities for building and executing topic message submission operations via the Agent Kit.

This module exposes:
- submit_topic_message_prompt: Generate a prompt/description for the submit topic message tool.
- submit_topic_message: Execute a topic message submission transaction.
- SubmitTopicMessageTool: Tool wrapper exposing the submit topic message operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client

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
    SubmitTopicMessageParameters,
    SubmitTopicMessageParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def submit_topic_message_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the submit topic message tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_tx_params: str = (
        PromptGenerator.get_scheduled_transaction_params_description(context)
    )

    return f"""
This tool will submit a message to a topic on the Hedera network.

Parameters:
- topic_id (str, required): The ID of the topic to submit the message to
- message (str, required): The message to submit to the topic
- transaction_memo (str, optional): An optional memo to include on the transaction
{scheduled_tx_params}
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a topic message submission result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the transaction ID.
    """
    if response.schedule_id:
        return (
            f"Scheduled transaction created successfully.\n"
            f"Transaction ID: {str(response.transaction_id)}. Schedule ID: {str(response.schedule_id)}"
        )
    else:
        return f"Message submitted successfully with transaction id {response.transaction_id}"


async def submit_topic_message(
    client: Client,
    context: Context,
    params: SubmitTopicMessageParameters,
) -> ToolResponse:
    """Execute a topic message submission using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the message submission to perform.

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
        normalised_params: SubmitTopicMessageParametersNormalised = (
            await HederaParameterNormaliser.normalise_submit_topic_message(
                params, context, client
            )
        )

        # Build transaction
        tx = HederaBuilder.submit_topic_message(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to submit message to topic: {str(e)}"
        print("[submit_topic_message_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


SUBMIT_TOPIC_MESSAGE_TOOL: str = "submit_topic_message_tool"


class SubmitTopicMessageTool(Tool):
    """Tool wrapper that exposes the topic message submission capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = SUBMIT_TOPIC_MESSAGE_TOOL
        self.name: str = "Submit Topic Message"
        self.description: str = submit_topic_message_prompt(context)
        self.parameters: type[SubmitTopicMessageParameters] = (
            SubmitTopicMessageParameters
        )
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: SubmitTopicMessageParameters
    ) -> ToolResponse:
        """Execute the topic message submission using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Topic message submission parameters accepted by this tool.

        Returns:
            The result of the submission as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        return await submit_topic_message(client, context, params)
