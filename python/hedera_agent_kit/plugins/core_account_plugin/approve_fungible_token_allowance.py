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
from hedera_agent_kit.shared.parameter_schemas.account_schema import (
    ApproveTokenAllowanceParameters,
    ApproveTokenAllowanceParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)


def approve_fungible_token_allowance_prompt(context: Context = {}) -> str:
    context_snippet = PromptGenerator.get_context_snippet(context)
    owner_account_desc = PromptGenerator.get_account_parameter_description(
        "owner_account_id", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool approves allowances for one or more fungible tokens from the owner to the spender.

Parameters:
- {owner_account_desc}
- spender_account_id (string, required): Spender account ID
- token_approvals (array, required): List of approvals. Each item:
  - token_id (string): Token ID
  - amount (number): Amount of tokens to approve (must be a positive number, can be float). Given in display units, the tools will parse them to correct format.
- transaction_memo (string, optional): Optional memo for the transaction
{usage_instructions}

Example:
Approve allowance of 50.1 tokens for token **0.0.7777** from **0.0.1001** to spender **0.0.3003** with memo "demo"

{{
    'owner_account_id': '0.0.1001',
    'spender_account_id': '0.0.3003',
    'token_approvals': [
        {{
            'token_id': '0.0.7777',
            'amount': 50.1
        }}
    ],
    'transaction_memo': 'demo'
}}


Note: Make sure token_approvals was passed - it is mandatory!
"""


def post_process(response: RawTransactionResponse) -> str:
    return f"Fungible token allowance(s) approved successfully. Transaction ID: {response.transaction_id}"


async def approve_fungible_token_allowance(
    client: Client,
    context: Context,
    params: ApproveTokenAllowanceParameters,
) -> ToolResponse:
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        normalised_params: ApproveTokenAllowanceParametersNormalised = (
            await HederaParameterNormaliser.normalise_approve_token_allowance(
                params, context, client, mirrornode_service
            )
        )
        tx: AccountAllowanceApproveTransaction = HederaBuilder.approve_token_allowance(
            normalised_params
        )
        return await handle_transaction(tx, client, context, post_process)
    except Exception as e:
        desc = "Failed to approve token allowance"
        message = f"{desc}: {str(e)}"
        print(f"[approve_fungible_token_allowance_tool] {message}")
        return ToolResponse(
            human_message=message,
            error=message,
        )


APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL = "approve_fungible_token_allowance_tool"


class ApproveFungibleTokenAllowanceTool(Tool):
    def __init__(self, context: Context):
        self.method = APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL
        self.name = "Approve Fungible Token Allowance"
        self.description = approve_fungible_token_allowance_prompt(context)
        self.parameters = ApproveTokenAllowanceParameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: ApproveTokenAllowanceParameters
    ) -> ToolResponse:
        return await approve_fungible_token_allowance(client, context, params)
