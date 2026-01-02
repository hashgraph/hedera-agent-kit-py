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
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    TransferNonFungibleTokenParameters,
    TransferNonFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def transfer_nft_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    scheduled_params_desc: str = (
        PromptGenerator.get_scheduled_transaction_params_description(context)
    )

    return f"""
{context_snippet}

This tool will transfer non-fungible tokens (NFTs). Support transferring multiple NFTs (from one collections) to multiple recipients in a single transaction.

Parameters:
- {source_account_desc}
- token_id (string, required): The NFT token ID to transfer (e.g. "0.0.12345")
- recipients (array, required): List of objects specifying recipients and serial numbers
  - recipient (string): Account to transfer to
  - serial_number (string): NFT serial number to transfer
- transaction_memo (string, optional): Optional memo for the transaction

{scheduled_params_desc}
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"Non-fungible tokens successfully transferred. Transaction ID: {response.transaction_id}"


async def transfer_nft(
    client: Client,
    context: Context,
    params: TransferNonFungibleTokenParameters,
) -> ToolResponse:
    try:
        normalised_params: TransferNonFungibleTokenParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_non_fungible_token(
                params, context, client
            )
        )
        tx = HederaBuilder.transfer_non_fungible_token(normalised_params)
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        desc = "Failed to transfer non-fungible token"
        message = f"{desc}: {str(e)}"
        print(f"[transfer_non_fungible_token_tool] {message}")
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_NON_FUNGIBLE_TOKEN_TOOL = "transfer_non_fungible_token_tool"


class TransferNonFungibleTokenTool(Tool):
    def __init__(self, context: Context):
        self.method = TRANSFER_NON_FUNGIBLE_TOKEN_TOOL
        self.name = "Transfer Non Fungible Token"
        self.description = transfer_nft_prompt(context)
        self.parameters = TransferNonFungibleTokenParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: TransferNonFungibleTokenParameters,
    ) -> ToolResponse:
        return await transfer_nft(client, context, params)
