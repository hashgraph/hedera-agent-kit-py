"""Hedera Agent Toolkit - Google ADK Audit Hook Agent.

This agent is designed to be run using the ADK dev tools CLI:
    adk run audit_hook_agent
"""

import os
from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from google.adk.agents import Agent

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.plugins import (
    core_account_plugin_tool_names,
    core_token_plugin_tool_names,
)

load_dotenv(".env")

# Hedera Client setup (Testnet)
operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

network: Network = Network(network="testnet")
client: Client = Client(network)
client.set_operator(operator_id, operator_key)

audit_hook = HcsAuditTrailHook(
    relevant_tools=[
        core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
        core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"],
    ],
    hcs_topic_id="0.0.8357090",  # FIXME: REMOVE THE PLACEHOLDER! Replace it with your actual topic ID. Create one using the Hedera Portal Playground or Hedera Agent Kit
)

configuration: Configuration = Configuration(
    tools=[],
    plugins=[],
    context=Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(operator_id), hooks=[audit_hook]
    ),
)

hedera_toolkit: HederaADKToolkit = HederaADKToolkit(
    client=client, configuration=configuration
)

tools = hedera_toolkit.get_tools()

root_agent = Agent(
    # model="gemini-3.1-flash-lite-preview",
    model="gemini-3-flash-preview",
    name="hedera_audit_agent",
    instruction=(
        "You are a helpful assistant with access to Hedera blockchain tools. "
        "You can help users create accounts, transfer HBAR, manage tokens, "
        "create topics, and query blockchain information. "
        "Always provide clear explanations of the transactions you perform."
        "Note that some actions (like HBAR transfers and Token Creation) are automatically audited."
    ),
    description=(
        "An AI agent that can interact with the Hedera blockchain network "
        "and performs audited actions recorded on the HCS service."
    ),
    tools=tools,
)
