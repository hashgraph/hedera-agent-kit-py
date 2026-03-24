"""Hedera Agent Toolkit - Google ADK Plugin Agent.

This agent is designed to be run using the ADK dev tools CLI:
    adk run plugin_tool_calling_agent
"""

import os
from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from google.adk.agents import Agent

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

# Hedera Client setup (Testnet)
operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

network: Network = Network(network="testnet")
client: Client = Client(network)
client.set_operator(operator_id, operator_key)

# Configuration with all plugins
configuration: Configuration = Configuration(
    tools=[],  # load all tools
    plugins=[],  # load all plugins
    context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(operator_id)),
)

# Create Hedera ADK toolkit
hedera_toolkit: HederaADKToolkit = HederaADKToolkit(
    client=client, configuration=configuration
)

# Get ADK-compatible tools (async functions)
tools = hedera_toolkit.get_tools()

# Create ADK agent
root_agent = Agent(
    model="gemini-3.1-flash-lite-preview",
    name="hedera_agent",
    instruction=(
        "You are a helpful assistant with access to Hedera blockchain tools. "
        "You can help users create accounts, transfer HBAR, manage tokens, "
        "create topics, and query blockchain information. "
        "Always provide clear explanations of the transactions you perform."
    ),
    description=(
        "An AI agent that can interact with the Hedera blockchain network "
        "using various tools for account management, token operations, "
        "consensus service, and more."
    ),
    tools=tools,
)
