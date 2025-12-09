from __future__ import annotations

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
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    ApproveHbarAllowanceParameters,
    ApproveHbarAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def approve_hbar_allowance_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    owner_account_desc = PromptGenerator.get_account_parameter_description(
        "owner_account_id", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool approves an HBAR allowance from the owner to the spender.

Parameters:
- {owner_account_desc}
- spender_account_id (string, required): Spender account ID
- amount (number, required): Amount of HBAR to approve (can be decimal, cannot be negative)
- transaction_memo (string, optional): Optional memo for the transaction
{usage_instructions}
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"HBAR allowance approved successfully. Transaction ID: {response.transaction_id}"


async def approve_hbar_allowance(
    client: Client,
    context: Context,
    params: ApproveHbarAllowanceParameters,
) -> ToolResponse:
    try:
        normalised_params: ApproveHbarAllowanceParametersNormalised = (
            HederaParameterNormaliser.normalise_approve_hbar_allowance(
                params, context, client
            )
        )
        tx: AccountAllowanceApproveTransaction = HederaBuilder.approve_hbar_allowance(
            normalised_params
        )
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        desc = "Failed to approve hbar allowance."
        message = f"{desc}: {str(e)}"
        print(f"[approve_hbar_allowance_tool] {message}")
        return ToolResponse(
            human_message=message,
            error=message,
        )


APPROVE_HBAR_ALLOWANCE_TOOL = "approve_hbar_allowance_tool"


class ApproveHbarAllowanceTool(Tool):
    def __init__(self, context: Context):
        self.method = APPROVE_HBAR_ALLOWANCE_TOOL
        self.name = "Approve HBAR Allowance"
        self.description = approve_hbar_allowance_prompt(context)
        self.parameters = ApproveHbarAllowanceParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: ApproveHbarAllowanceParameters
    ) -> ToolResponse:
        return await approve_hbar_allowance(client, context, params)
