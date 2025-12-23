"""Utilities for building and executing token update operations via the Agent Kit.

This module exposes:
- update_token_prompt: Generate a prompt/description for the update token tool.
- update_token: Execute a token update transaction.
- UpdateTokenTool: Tool wrapper exposing the token update operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, PublicKey
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import IHederaMirrornodeService
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import TokenInfo

from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    UpdateTokenParameters,
    UpdateTokenParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import handle_transaction
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver
from hedera_agent_kit.shared.utils.default_tool_output_parsing import transaction_tool_output_parser
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.tool import Tool


async def check_validity_of_updates(
    params: UpdateTokenParametersNormalised,
    mirrornode: IHederaMirrornodeService,
    user_public_key: PublicKey,
) -> None:
    """Verify that the user has permission to update the token and that keys exist.

    Args:
        params: Normalized update parameters.
        mirrornode: Mirror node service to fetch token info.
        user_public_key: The public key of the user attempting the update.

    Raises:
        ValueError: If token not found, user lacks permission, or key updates are invalid.
    """
    token_id_str = str(params.token_id)
    token_details: TokenInfo = await mirrornode.get_token_info(token_id_str)

    if not token_details:
        raise ValueError("Token not found")

    # Check admin key
    admin_key_info = token_details.get("admin_key")
    token_admin_key_str = admin_key_info.get("key") if admin_key_info else None

    if token_admin_key_str != user_public_key.to_string_der():
        if token_admin_key_str != user_public_key.to_string_raw():
            try:
                token_admin_key = PublicKey.from_string(token_admin_key_str)
                if token_admin_key.to_string_der() != user_public_key.to_string_der():
                    raise ValueError(
                        f"You do not have permission to update this token. "
                        f"The adminKey ({token_admin_key_str}) does not match your public key."
                    )
            except Exception:
                if (
                    token_admin_key_str
                ):  # Only throw if there IS an admin key and it doesn't match
                    raise ValueError(
                        f"You do not have permission to update this token. "
                        f"The adminKey ({token_admin_key_str}) does not match your public key."
                    )

    # Check if we are trying to update a key that doesn't exist on the token
    key_checks = [
        "admin_key",
        "kyc_key",
        "freeze_key",
        "wipe_key",
        "supply_key",
        "fee_schedule_key",
        "pause_key",
        "metadata_key",
    ]

    # In params.token_keys, we have the keys that are being updated.
    if params.token_keys:
        for key in key_checks:
            new_key = getattr(params.token_keys, key, None)
            if new_key:
                # User is trying to update this key
                existing_key = token_details.get(key)  # type: ignore
                if not existing_key:
                    raise ValueError(
                        f"Cannot update {key}: token was created without a {key}"
                    )


def update_token_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the update token tool.

    Args:
        context: Optional contextual configuration.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    token_desc: str = PromptGenerator.get_any_address_parameter_description(
        "token_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will update an existing Hedera HTS token. Only the fields provided will be updated.

Key fields (adminKey, kycKey, freezeKey, wipeKey, supplyKey, feeScheduleKey, pauseKey, metadataKey) must contain **Hedera-compatible public keys (as strings) or boolean (true/false)**. You can provide these in one of three ways:

1. **Boolean true** – Set this field to use user/operator key. Injecting of the key will be handled automatically.
2. **Not provided** – The field will not be updated.
3. **String** – Provide a Hedera-compatible public key string to set a field explicitly.

Parameters:
- {token_desc}
- token_name (str, optional): New name for the token. Up to 100 characters.
- token_symbol (str, optional): New symbol for the token. Up to 100 characters.
- treasury_account_id (str, optional): New treasury account for the token (Hedera account ID).
- admin_key (bool|str, optional): New admin key. Pass true to use your operator key, or provide a public key string.
- kyc_key (bool|str, optional): New KYC key. Pass true to use your operator key, or provide a public key string.
- freeze_key (bool|str, optional): New freeze key. Pass true to use your operator key, or provide a public key string.
- wipe_key (bool|str, optional): New wipe key. Pass true to use your operator key, or provide a public key string.
- supply_key (bool|str, optional): New supply key. Pass true to use your operator key, or provide a public key string.
- fee_schedule_key (bool|str, optional): New fee schedule key. Pass true to use your operator key, or provide a public key string.
- pause_key (bool|str, optional): New pause key. Pass true to use your operator key, or provide a public key string.
- metadata_key (bool|str, optional): New metadata key. Pass true to use your operator key, or provide a public key string.
- metadata (str, optional): New metadata for the token as str. Will be encoded as UTF-8.
- token_memo (str, optional): Short public memo for the token, up to 100 characters.
- auto_renew_account_id (str, optional): Account to automatically pay for renewal.

Examples:
- If the user asks for "my key" → set the field to `true`. Example: set kycKey to my key.
- If the user does not mention the key → do not set the field.
- If the user provides a key → set the field to the provided public key string.

*IMPORTANT:* If the user provides multiple fields in a single request, combine them into **one tool call** with all parameters together.

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a token update result.

    Args:
        response: The raw response returned by the transaction execution.

    Returns:
        A concise message describing the status.
    """
    if response.schedule_id:
        return f"""Scheduled token update created successfully.
Transaction ID: {response.transaction_id}
Schedule ID: {response.schedule_id}"""

    return f"Token successfully updated. Transaction ID: {response.transaction_id}"


async def update_token(
    client: Client,
    context: Context,
    params: UpdateTokenParameters,
) -> ToolResponse:
    """Execute a token update using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the token update.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.
    """
    try:
        # Normalize parameters
        normalised_params: UpdateTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_update_token(params, context, client)
        )

        # Check validity of updates
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        user_public_key = await AccountResolver.get_default_public_key(context, client)

        await check_validity_of_updates(
            normalised_params, mirrornode_service, user_public_key
        )

        # Build transaction
        tx: Transaction = HederaBuilder.update_token(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to update token: {str(e)}"
        print("[update_token_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


UPDATE_TOKEN_TOOL: str = "update_token_tool"


class UpdateTokenTool(Tool):
    """Tool wrapper that exposes the token update capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = UPDATE_TOKEN_TOOL
        self.name: str = "Update Token"
        self.description: str = update_token_prompt(context)
        self.parameters: type[UpdateTokenParameters] = UpdateTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: UpdateTokenParameters
    ) -> ToolResponse:
        """Execute the token update using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Token update parameters accepted by this tool.

        Returns:
            The result of the token update as a ToolResponse.
        """
        return await update_token(client, context, params)
