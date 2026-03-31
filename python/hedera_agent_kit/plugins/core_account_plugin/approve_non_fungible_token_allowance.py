from __future__ import annotations

from pprint import pprint

from hiero_sdk_python import Client, AccountAllowanceApproveTransaction
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
    ApproveNftAllowanceParameters,
    ApproveNftAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def approve_nft_allowance_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    owner_account_desc = PromptGenerator.get_account_parameter_description(
        "owner_account_id", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool approves an NFT allowance from the owner to the spender for specific NFT serial numbers of a token, or for all serials in the NFT collection.

Parameters:
- {owner_account_desc}
- spender_account_id (string, required): Spender account ID
- token_id (string, required): The NFT token ID (e.g., 0.0.xxxxx)
- all_serials (boolean, optional): If true, approves allowance for all current and future serials of the NFT. When true, do not provide serial_numbers.
- serial_numbers (number[], conditionally required): Array of NFT serial numbers to approve. Required when all_serials is not true.
- transaction_memo (string, optional): Optional memo for the transaction
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"NFT allowance approved successfully. Transaction ID: {response.transaction_id}"


async def approve_nft_allowance(
    client: Client,
    context: Context,
    params: ApproveNftAllowanceParameters,
) -> ToolResponse:
    try:
        pprint(params)
        normalised_params: ApproveNftAllowanceParametersNormalised = (
            HederaParameterNormaliser.normalise_approve_nft_allowance(
                params, context, client
            )
        )
        tx: AccountAllowanceApproveTransaction = HederaBuilder.approve_nft_allowance(
            normalised_params
        )
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        desc = "Failed to approve NFT allowance"
        message = f"{desc}: {str(e)}"
        print(f"[approve_nft_allowance_tool] {message}")
        return ToolResponse(
            human_message=message,
            error=message,
        )


APPROVE_NFT_ALLOWANCE_TOOL = "approve_nft_allowance_tool"


class ApproveNftAllowanceTool(Tool):
    def __init__(self, context: Context):
        self.method = APPROVE_NFT_ALLOWANCE_TOOL
        self.name = "Approve NFT Allowance"
        self.description = approve_nft_allowance_prompt(context)
        self.parameters = ApproveNftAllowanceParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: ApproveNftAllowanceParameters
    ) -> ToolResponse:
        return await approve_nft_allowance(client, context, params)
