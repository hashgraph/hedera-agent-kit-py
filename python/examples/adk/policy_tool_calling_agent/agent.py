"""Hedera Agent Toolkit - Google ADK Policy Agent.

This agent is designed to be run using the ADK dev tools CLI:
    adk run policy_tool_calling_agent
"""

import os
from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from google.adk.agents import Agent

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration
from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy
from hedera_agent_kit.plugins import core_account_plugin, core_token_plugin

load_dotenv(".env")

# Hedera Client setup (Testnet)
operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

network: Network = Network(network="testnet")
client: Client = Client(network)
client.set_operator(operator_id, operator_key)

# Instantiate the MaxRecipientsPolicy, restricting transfers to a maximum of 2 recipients
policy = MaxRecipientsPolicy(max_recipients=2)

# We load only the core_account_plugin and core_token_plugin, which provide the base set
# of tools that the MaxRecipientsPolicy operates on.
configuration: Configuration = Configuration(
    tools=[],
    plugins=[core_account_plugin, core_token_plugin],
    context=Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(operator_id), hooks=[policy]
    ),
)

hedera_toolkit: HederaADKToolkit = HederaADKToolkit(
    client=client, configuration=configuration
)

tools = hedera_toolkit.get_tools()

root_agent = Agent(
    model="gemini-3.1-flash-lite-preview",
    name="hedera_policy_agent",
    instruction=(
        "You are a helpful assistant with access to Hedera blockchain tools. "
        "You can help users perform transactions. "
    ),
    description=(
        "An AI agent that can interact with the Hedera blockchain network "
        "using policy-restricted tools."
    ),
    tools=tools,
)
