import os
from dataclasses import dataclass
from typing import List

from hedera_agent_kit_py.plugins import (
    core_account_plugin_tool_names,
    core_account_plugin,
    core_consensus_query_plugin,
    core_consensus_query_plugin_tool_names,
    core_account_query_plugin,
    core_account_query_plugin_tool_names,
    core_consensus_plugin_tool_names,
    core_consensus_plugin,
    core_evm_plugin_tool_names,
    core_evm_plugin,
    core_misc_query_plugin_tool_names,
    core_misc_query_plugin,
    core_transaction_query_plugin,
    core_transaction_query_plugin_tool_names,
    core_token_query_plugin_tool_names,
    core_token_query_plugin,
    core_token_plugin_tool_names,
    core_token_plugin,
)


from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.plugin import Plugin
from .llm_factory import LLMProvider, LLMOptions

CREATE_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"]
DELETE_ACCOUNT_TOOL = core_account_plugin_tool_names["DELETE_ACCOUNT_TOOL"]
CREATE_ACCOUNT_TOOL = core_account_plugin_tool_names["CREATE_ACCOUNT_TOOL"]
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
UPDATE_ACCOUNT_TOOL = core_account_plugin_tool_names["UPDATE_ACCOUNT_TOOL"]
TRANSFER_HBAR_WITH_ALLOWANCE_TOOL = core_account_plugin_tool_names[
    "TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"
]
CREATE_TOPIC_TOOL = core_consensus_plugin_tool_names["CREATE_TOPIC_TOOL"]
DELETE_TOPIC_TOOL = core_consensus_plugin_tool_names["DELETE_TOPIC_TOOL"]
GET_HBAR_BALANCE_QUERY_TOOL = core_account_query_plugin_tool_names[
    "GET_HBAR_BALANCE_QUERY_TOOL"
]
GET_TRANSACTION_RECORD_QUERY_TOOL = core_transaction_query_plugin_tool_names[
    "GET_TRANSACTION_RECORD_QUERY_TOOL"
]
CREATE_ERC20_TOOL = core_evm_plugin_tool_names["CREATE_ERC20_TOOL"]
SUBMIT_TOPIC_MESSAGE_TOOL = core_consensus_plugin_tool_names[
    "SUBMIT_TOPIC_MESSAGE_TOOL"
]
GET_EXCHANGE_RATE_TOOL = core_misc_query_plugin_tool_names["GET_EXCHANGE_RATE_TOOL"]
GET_TOPIC_INFO_QUERY_TOOL = core_consensus_query_plugin_tool_names[
    "GET_TOPIC_INFO_QUERY_TOOL"
]

GET_ACCOUNT_QUERY_TOOL = core_account_query_plugin_tool_names["GET_ACCOUNT_QUERY_TOOL"]
UPDATE_TOPIC_TOOL = core_consensus_plugin_tool_names["UPDATE_TOPIC_TOOL"]
GET_TOKEN_INFO_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_TOKEN_INFO_QUERY_TOOL"
]


@dataclass
class LangchainTestOptions:
    tools: List[str]
    plugins: List[Plugin]
    agent_mode: AgentMode


def get_provider_api_key_map() -> dict:
    """Load provider API keys lazily, after dotenv is loaded."""
    return {
        LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
        LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_KEY"),
        LLMProvider.GROQ: os.getenv("GROQ_API_KEY"),
    }


DEFAULT_LLM_OPTIONS: LLMOptions = LLMOptions(
    provider=LLMProvider.OPENAI,
    model="gpt-4o-mini",
    temperature=0.7,
    max_iterations=1,
    system_prompt="""You are a Hedera blockchain assistant. You have access to tools for blockchain operations.
        When a user asks to transfer HBAR, use the transfer_hbar_tool with the correct parameters.
        Extract the amount and recipient account ID from the user's request.
        Always use the exact tool name and parameter structure expected.
        When error occurs, respond with a detailed error message.""",
    api_key=None,
    base_url=None,
)

TOOLKIT_OPTIONS: LangchainTestOptions = LangchainTestOptions(
    tools=[
        TRANSFER_HBAR_TOOL,
        CREATE_ACCOUNT_TOOL,
        CREATE_TOPIC_TOOL,
        GET_HBAR_BALANCE_QUERY_TOOL,
        GET_TOPIC_INFO_QUERY_TOOL,
        GET_EXCHANGE_RATE_TOOL,
        UPDATE_ACCOUNT_TOOL,
        DELETE_ACCOUNT_TOOL,
        DELETE_TOPIC_TOOL,
        CREATE_ERC20_TOOL,
        SUBMIT_TOPIC_MESSAGE_TOOL,
        GET_ACCOUNT_QUERY_TOOL,
        CREATE_FUNGIBLE_TOKEN_TOOL,
        GET_TRANSACTION_RECORD_QUERY_TOOL,
        TRANSFER_HBAR_WITH_ALLOWANCE_TOOL,
        UPDATE_TOPIC_TOOL,
        GET_TOKEN_INFO_QUERY_TOOL,
    ],
    plugins=[
        core_account_plugin,
        core_consensus_plugin,
        core_account_query_plugin,
        core_consensus_query_plugin,
        core_misc_query_plugin,
        core_evm_plugin,
        core_transaction_query_plugin,
        core_token_plugin,
        core_token_query_plugin,
    ],
    agent_mode=AgentMode.AUTONOMOUS,
)

MIRROR_NODE_WAITING_TIME = 4000
