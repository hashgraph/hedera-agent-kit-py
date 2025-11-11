"""Utilities for building and executing ERC20 creation operations via the Agent Kit.

This module exposes:
- create_erc20_prompt: Generate a prompt/description for the ERC20 creation tool.
- create_erc20: Execute an ERC20 creation transaction through the BaseERC20Factory contract.
- CreateERC20Tool: Tool wrapper exposing the ERC20 creation operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client, TransactionRecordQuery, TransactionRecord
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.configuration import Context, AgentMode
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit_py.shared.models import ToolResponse, RawTransactionResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateERC20Parameters,
    ContractExecuteTransactionParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit_py.shared.tool import Tool
from hedera_agent_kit_py.shared.utils import ledger_id_from_network
from hedera_agent_kit_py.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit_py.shared.constants.contracts import (
    get_erc20_factory_address,
    ERC20_FACTORY_ABI,
)


def create_erc20_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the create ERC20 tool."""
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This tool creates an ERC20 token on Hedera by calling the BaseERC20Factory contract.
ERC20 is an EVM-compatible fungible token standard.

Parameters:
- token_name (str, required): The name of the token.
- token_symbol (str, required): The token symbol (e.g., HED).
- decimals (int, optional): Number of decimal places (default: 18).
- initial_supply (int, optional): Initial supply of the token (default: 0).
{scheduled_desc}

{usage_instructions}
"""


def post_process(erc20_address: str | None, response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for ERC20 creation results."""
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled creation of ERC20 successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return (
        f"ERC20 token created successfully at address {erc20_address or 'unknown'}.\n"
        f"Transaction ID: {response.transaction_id}"
    )


async def get_erc20_address(client: Client, tx: RawTransactionResponse) -> str:
    record: TransactionRecord = (
        TransactionRecordQuery().set_transaction_id(tx.transaction_id).execute(client)
    )
    return f"0x{record.call_result.evm_address}"


async def create_erc20(
    client: Client,
    context: Context,
    params: CreateERC20Parameters,
) -> ToolResponse:
    """Execute ERC20 creation transaction via the BaseERC20Factory contract."""
    try:
        factory_address = get_erc20_factory_address(
            ledger_id_from_network(client.network)
        )

        normalised_params: ContractExecuteTransactionParametersNormalised = (
            await HederaParameterNormaliser.normalise_create_erc20_params(
                params,
                factory_address,
                ERC20_FACTORY_ABI,
                "deployToken",
                context,
                client,
            )
        )

        tx: Transaction = HederaBuilder.execute_transaction(normalised_params)
        result = await handle_transaction(tx, client, context)

        if context.mode == AgentMode.RETURN_BYTES:
            return result

        raw_tx = getattr(result, "raw_tx", None)
        erc20_address = await get_erc20_address(client, raw_tx)
        human_message = post_process(erc20_address, raw_tx)

        return ToolResponse(
            human_message=human_message,
            extra={"erc20_address": erc20_address, "raw": raw_tx},
        )

    except Exception as e:
        message = f"Failed to create ERC20 token: {str(e)}"
        print("[create_erc20_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


CREATE_ERC20_TOOL = "create_erc20_tool"


class CreateERC20Tool(Tool):
    """Tool wrapper exposing ERC20 creation capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = CREATE_ERC20_TOOL
        self.name: str = "Create ERC20 Token"
        self.description: str = create_erc20_prompt(context)
        self.parameters: type[CreateERC20Parameters] = CreateERC20Parameters

    async def execute(
        self, client: Client, context: Context, params: CreateERC20Parameters
    ) -> ToolResponse:
        return await create_erc20(client, context, params)
