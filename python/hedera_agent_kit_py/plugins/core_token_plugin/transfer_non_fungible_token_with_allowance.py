from __future__ import annotations

from pprint import pprint

from hiero_sdk_python import Client
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    TransferNonFungibleTokenWithAllowanceParameters,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator


def transfer_nft_with_allowance_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will transfer non-fungible tokens (NFTs) using an existing **token allowance**.

Parameters:
- source_account_id (string, required): The token owner (allowance granter)
- token_id (string, required): The NFT token ID to transfer (e.g. "0.0.12345")
- recipients (array, required): List of objects specifying recipients and serial numbers
  - recipientId (string): Account to transfer to
  - serialNumber (string): NFT serial number to transfer
- transaction_memo (string, optional): Optional memo for the transaction

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"Non-fungible tokens successfully transferred with allowance. Transaction ID: {response.transaction_id}"


async def transfer_nft_with_allowance(
    client: Client,
    context: Context,
    params: TransferNonFungibleTokenWithAllowanceParameters,
) -> ToolResponse:
    try:
        pprint(params)
        normalised_params: TransferNonFungibleTokenWithAllowanceParametersNormalised = (
            HederaParameterNormaliser.normalise_transfer_non_fungible_token_with_allowance(
                params, context
            )
        )
        tx = HederaBuilder.transfer_non_fungible_token_with_allowance(normalised_params)
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        desc = "Failed to transfer non-fungible token with allowance"
        message = f"{desc}: {str(e)}"
        print(f"[transfer_non_fungible_token_with_allowance_tool] {message}")
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_NFT_WITH_ALLOWANCE_TOOL = "transfer_non_fungible_token_with_allowance_tool"


class TransferNftWithAllowanceTool(Tool):
    def __init__(self, context: Context):
        self.method = TRANSFER_NFT_WITH_ALLOWANCE_TOOL
        self.name = "Transfer Non Fungible Token with Allowance"
        self.description = transfer_nft_with_allowance_prompt(context)
        self.parameters = TransferNonFungibleTokenWithAllowanceParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self,
        client: Client,
        context: Context,
        params: TransferNonFungibleTokenWithAllowanceParameters,
    ) -> ToolResponse:
        return await transfer_nft_with_allowance(client, context, params)
