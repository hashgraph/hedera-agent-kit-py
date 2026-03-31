"""Utilities for querying Hedera EVM contract information via the Agent Kit.

This module exposes:
- get_contract_info_query_prompt: Generate a prompt/description for the contract info query tool.
- get_contract_info_query: Execute a contract info query using the Mirror Node API.
- GetContractInfoQueryTool: Tool wrapper exposing the contract info query operation to the runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.hedera_utils.mirrornode.types.common import (
    MirrornodeKeyInfo,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode.types.evm import ContractInfo
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas.evm_schema import (
    ContractInfoQueryParameters,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    untyped_query_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


def get_contract_info_query_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the get contract info query tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default network information.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()

    return f"""
{context_snippet}

This tool will return the information for a given Hedera EVM contract.

Parameters:
- contract_id (str): The contract ID or EVM address to query for.
{usage_instructions}
"""


def format_key(key: Optional[MirrornodeKeyInfo]) -> str:
    """Format a mirrornode key info object for display."""
    if not key:
        return "Not Set"
    if key.get("_type"):
        return key.get("key", "Present")
    return "Present"


def format_timestamp(ts: Optional[str]) -> str:
    """Format a timestamp string (seconds.nanos) to ISO 8601, or N/A."""
    if not ts:
        return "N/A"
    try:
        seconds = ts.split(".")[0]
        date = datetime.fromtimestamp(int(seconds))
        return date.isoformat()
    except Exception:
        return ts or "N/A"


def post_process(contract: ContractInfo) -> str:
    """Produce a human-readable summary for a contract info query result."""

    contract_id = contract.get("contract_id", "N/A")
    evm_address = contract.get("evm_address", "N/A")
    memo = contract.get("memo", "N/A")
    deleted = "Yes" if contract.get("deleted") else "No"
    created_timestamp = format_timestamp(contract.get("created_timestamp"))
    expiration_timestamp = format_timestamp(contract.get("expiration_timestamp"))
    admin_key = format_key(contract.get("admin_key"))
    auto_renew_account = contract.get("auto_renew_account", "N/A")
    auto_renew_period = contract.get("auto_renew_period")
    auto_renew_period_str = (
        str(auto_renew_period) if auto_renew_period is not None else "N/A"
    )
    max_assoc = contract.get("max_automatic_token_associations")
    max_assoc_str = str(max_assoc) if max_assoc is not None else "N/A"
    file_id = contract.get("file_id", "N/A")
    nonce = contract.get("nonce")
    nonce_str = str(nonce) if nonce is not None else "N/A"

    return (
        "Contract Info Query Result:\n"
        f"- Contract ID: {contract_id}\n"
        f"- EVM Address: {evm_address}\n"
        f"- Memo: {memo}\n"
        f"- Deleted: {deleted}\n"
        f"- Created: {created_timestamp}\n"
        f"- Expiration: {expiration_timestamp}\n"
        f"- Admin Key: {admin_key}\n"
        f"- Auto Renew Account: {auto_renew_account}\n"
        f"- Auto Renew Period (s): {auto_renew_period_str}\n"
        f"- Max Auto Token Associations: {max_assoc_str}\n"
        f"- Bytecode File ID: {file_id}\n"
        f"- Nonce: {nonce_str}"
    )


async def get_contract_info_query(
    client: Client, context: Context, params: ContractInfoQueryParameters
) -> ToolResponse:
    """Execute a contract info query via the Mirror Node service."""
    try:
        # validate/parse params using schema — pydantic will validate on creation
        parsed = params

        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        info = await mirrornode_service.get_contract_info(parsed.get("contract_id"))

        human_message = post_process(info)
        return ToolResponse(human_message=human_message)

    except Exception as e:
        message = f"== Failed to get contract info: {str(e)}"
        print("[get_contract_info_query]", message)
        return ToolResponse(human_message=message, error=message)


GET_CONTRACT_INFO_QUERY_TOOL = "get_contract_info_query_tool"


class GetContractInfoQueryTool(Tool):
    """Tool wrapper exposing contract info query capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = GET_CONTRACT_INFO_QUERY_TOOL
        self.name: str = "Get Contract Info"
        self.description: str = get_contract_info_query_prompt(context)
        self.parameters: type[ContractInfoQueryParameters] = ContractInfoQueryParameters
        self.outputParser = untyped_query_output_parser

    async def execute(
        self, client: Client, context: Context, params: ContractInfoQueryParameters
    ) -> ToolResponse:
        return await get_contract_info_query(client, context, params)
