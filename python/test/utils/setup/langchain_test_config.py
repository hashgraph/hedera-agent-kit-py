import os
from dataclasses import dataclass
from typing import List

from hedera_agent_kit_py.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
    core_account_plugin,
)
from hedera_agent_kit_py.plugins.core_account_query_plugin import (
    core_account_query_plugin,
    core_account_query_plugin_tool_names,
)

from hedera_agent_kit_py.plugins.core_consensus_plugin import core_consensus_plugin_tool_names, core_consensus_plugin
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.plugin import Plugin
from .llm_factory import LLMProvider, LLMOptions

(TRANSFER_HBAR_TOOL, CREATE_ACCOUNT_TOOL) = core_account_plugin_tool_names
CREATE_TOPIC_TOOL = core_consensus_plugin_tool_names["CREATE_TOPIC_TOOL"]
GET_HBAR_BALANCE_QUERY_TOOL = core_account_query_plugin_tool_names[
    "GET_HBAR_BALANCE_QUERY_TOOL"
]

GET_ACCOUNT_QUERY_TOOL = core_account_query_plugin_tool_names["GET_ACCOUNT_QUERY_TOOL"]


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
        GET_HBAR_BALANCE_QUERY_TOOL,
        GET_ACCOUNT_QUERY_TOOL,
        CREATE_TOPIC_TOOL,
    ],
    plugins=[core_account_plugin, core_account_query_plugin, core_consensus_plugin],
    agent_mode=AgentMode.AUTONOMOUS,
)

MIRROR_NODE_WAITING_TIME = 4000
