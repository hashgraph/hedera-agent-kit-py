from __future__ import annotations


from typing import Any

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction
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
    TransferNonFungibleTokenWithAllowanceParameters,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


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
  - recipient_id (string): Account to transfer to
  - serial_number (string): NFT serial number to transfer
- transaction_memo (string, optional): Optional memo for the transaction

{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"Non-fungible tokens successfully transferred with allowance. Transaction ID: {response.transaction_id}"


TRANSFER_NFT_WITH_ALLOWANCE_TOOL = "transfer_non_fungible_token_with_allowance_tool"


class TransferNftWithAllowanceTool(BaseToolV2):
    def __init__(self, context: Context):
        self.method = TRANSFER_NFT_WITH_ALLOWANCE_TOOL
        self.name = "Transfer Non Fungible Token with Allowance"
        self.description = transfer_nft_with_allowance_prompt(context)
        self.parameters = TransferNonFungibleTokenWithAllowanceParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> TransferNonFungibleTokenWithAllowanceParametersNormalised:
        return HederaParameterNormaliser.normalise_transfer_non_fungible_token_with_allowance(
            params, context
        )

    async def core_action(
        self,
        normalized_params: TransferNonFungibleTokenWithAllowanceParametersNormalised,
        client: Client,
        context: Context,
    ) -> Transaction:
        return HederaBuilder.transfer_non_fungible_token_with_allowance(
            normalized_params
        )

    async def secondary_action(
        self,
        transaction: Transaction,
        client: Client,
        context: Context,
    ) -> ToolResponse:
        return await handle_transaction(transaction, client, context, post_process)
