"""Utilities for building and executing topic update operations via the Agent Kit.

This module exposes:
- update_topic_prompt: Generate a prompt/description for the update topic tool.
- update_topic: Execute a topic update transaction.
- UpdateTopicTool: Tool wrapper exposing the update topic operation to the runtime.
"""

from __future__ import annotations

from typing import Dict, Optional

from hiero_sdk_python import Client, PublicKey
from hiero_sdk_python.consensus.topic_update_transaction import TopicUpdateTransaction

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import TopicInfo
from hedera_agent_kit_py.shared.models import (
    RawTransactionResponse,
    ToolResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.consensus_schema import (
    UpdateTopicParameters,
    UpdateTopicParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def update_topic_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the update topic tool.

    Args:
        context: Optional contextual configuration that may influence the prompt.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}
This tool will update an existing Hedera Consensus Topic. Only the fields provided will be updated.
Key fields (adminKey, submitKey) must contain **Hedera-compatible public keys (as strings) or boolean (true/false)**. You can provide these in one of three ways:
1. **Boolean true** – Set this field to use user/operator key. Injecting of the key will be handled automatically.
2. **Not provided** – The field will not be updated.
3. **String** – Provide a Hedera-compatible public key string to set a field explicitly.

Parameters:
- topic_id (string): ID of the topic to update.
- topic_memo (string, optional): New memo for the topic.
- admin_key (boolean|string, optional): New admin key. Pass true to use your operator key, or provide a public key string.
- submit_key (boolean|string, optional): New submit key. Pass true to use your operator key, or provide a public key string.
- auto_renew_account_Id (string, optional): Account to automatically pay for renewal.
- auto_renew_Period (number, optional): Auto renew period in seconds.
- expiration_time (string|Date, optional): New expiration time for the topic (ISO string or Date).
Examples:
- If the user asks for "my key" -> set the field to `true`.
- If the user does not mention the key -> do not set the field.
- If the user provides a key -> set the field to the provided public key string.

If the user provides multiple fields in a single request, 
combine them into **one tool call** with all parameters together.
{usage_instructions}
"""


async def check_validity_of_updates(
    params: UpdateTopicParametersNormalised,
    mirrornode: IHederaMirrornodeService,
    user_public_key: Optional[PublicKey],
) -> None:
    """Validate that the requested updates are permissible on the existing topic.

    Args:
        params: The normalized update parameters.
        mirrornode: The mirror node service to fetch the current topic state.
        user_public_key: The public key of the current operator.

    Raises:
        Exception: If the topic is not found, the user lacks permission or invalid key update.
    """
    # Retrieve raw dictionary or TypedDict from service
    topic_details: TopicInfo = await mirrornode.get_topic_info(str(params.topic_id))

    if not topic_details:
        raise Exception("Topic not found")

    # Mirror node returns keys structure, e.g. {'key': '...'} or None
    current_admin_key_info = topic_details.get("admin_key")

    if not current_admin_key_info:
        raise Exception("Topic does not have an admin key. It cannot be updated.")

    current_admin_key_str = current_admin_key_info.get("key")

    # Check permissions: An operator key must match the topic's admin key
    if user_public_key:
        user_key_str = user_public_key.to_string_raw()
        if current_admin_key_str != user_key_str and current_admin_key_str != str(
            user_public_key
        ):
            print(
                f"topicDetails.admin_key: {current_admin_key_str} vs userPublicKey: {user_key_str}"
            )
            raise Exception(
                "You do not have permission to update this topic. The adminKey does not match your public key."
            )
        pass

    # Check: Cannot add a key to a topic created without that key type
    key_checks: Dict[str, str] = {
        "admin_key": "admin_key",
        "submit_key": "submit_key",
    }

    for param_field, topic_field in key_checks.items():
        user_value = getattr(params, param_field)
        topic_key_info = topic_details.get(topic_field)  # type: ignore[misc]

        if user_value is not None and not topic_key_info:
            raise Exception(
                f"Cannot update {param_field}: topic was created without a {topic_field}"
            )


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a topic update result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing success.
    """
    return f"Topic successfully updated. Transaction ID: {response.transaction_id}"


async def update_topic(
    client: Client,
    context: Context,
    params: UpdateTopicParameters,
) -> ToolResponse:
    """Execute a topic update using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the update.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.
    """
    try:
        normalised_params = await HederaParameterNormaliser.normalise_update_topic(
            params, context, client
        )

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        user_public_key = client.operator_private_key.public_key()

        await check_validity_of_updates(
            normalised_params, mirrornode_service, user_public_key
        )

        tx: TopicUpdateTransaction = HederaBuilder.update_topic(normalised_params)

        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        desc = "Failed to update topic"
        message = f"{desc}: {str(e)}"
        print("[update_topic_tool]", message)
        return ExecutedTransactionToolResponse(
            human_message=message,
            error=message,
            raw=RawTransactionResponse(status="INVALID_TRANSACTION", error=message),
        )


UPDATE_TOPIC_TOOL: str = "update_topic_tool"


class UpdateTopicTool(Tool):
    """Tool wrapper that exposes the topic update capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = UPDATE_TOPIC_TOOL
        self.name: str = "Update Topic"
        self.description: str = update_topic_prompt(context)
        self.parameters: type[UpdateTopicParameters] = UpdateTopicParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: UpdateTopicParameters
    ) -> ToolResponse:
        """Execute the topic update using the provided client, context, and params.

        Args:
            client: Hedera client.
            context: Runtime context.
            params: Topic update parameters.

        Returns:
            The result of the update as a ToolResponse.
        """
        return await update_topic(client, context, params)
