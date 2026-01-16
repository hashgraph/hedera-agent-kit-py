"""Hedera Agent CLI Chatbot using Google ADK.

This example demonstrates using the Hedera Agent Kit with Google's
Agent Development Kit (ADK) and Gemini models.
"""

import asyncio
import os

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_consensus_query_plugin,
    core_account_query_plugin,
    core_consensus_plugin,
    core_evm_plugin,
    core_misc_query_plugin,
    core_transaction_query_plugin,
    core_token_query_plugin,
    core_token_plugin,
    core_evm_query_plugin,
)
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

APP_NAME = "hedera_agent_app"
USER_ID = "hedera_user"
SESSION_ID = "session_1"


async def bootstrap():
    """Main entry point for the Hedera ADK agent."""
    # Hedera Client setup (Testnet)
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

    network: Network = Network(
        network="testnet"
    )  # ensure this matches SDK expectations
    client: Client = Client(network)
    client.set_operator(operator_id, operator_key)

    # Configuration with all plugins
    configuration: Configuration = Configuration(
        tools=[],
        plugins=[
            core_consensus_plugin,
            core_account_query_plugin,
            core_consensus_query_plugin,
            core_misc_query_plugin,
            core_evm_plugin,
            core_account_plugin,
            core_token_plugin,
            core_transaction_query_plugin,
            core_token_query_plugin,
            core_evm_query_plugin,
        ],
        context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(operator_id)),
    )

    # Create Hedera ADK toolkit
    hedera_toolkit: HederaADKToolkit = HederaADKToolkit(
        client=client, configuration=configuration
    )

    # Get ADK-compatible tools (async functions)
    tools = hedera_toolkit.get_tools()

    # Create ADK agent with Gemini model
    hedera_agent = Agent(
        model="gemini-2.0-flash",
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

    # Setup session and runner
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=hedera_agent, app_name=APP_NAME, session_service=session_service
    )

    print("=" * 60)
    print("Hedera Agent CLI Chatbot with Google ADK")
    print("=" * 60)
    print("Type 'exit' or 'quit' to end the session.")
    print("")
    print("Example commands:")
    print("  - What's my current HBAR balance?")
    print("  - Create a new topic called 'Daily Updates'")
    print("  - Transfer 1 HBAR to account 0.0.12345")
    print("  - Create a fungible token called 'MyToken' with symbol 'MTK'")
    print("")

    # CLI loop
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            # Create user message
            content = types.Content(
                role="user", parts=[types.Part(text=user_input)]
            )

            # Run the agent
            events = runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=content
            )

            # Process events and print response
            async for event in events:
                if event.is_final_response():
                    text_parts = []
                    for part in event.content.parts:
                        # Skip function calls to avoid warning when accessing .text
                        if part.function_call:
                            continue
                        if part.text:
                            text_parts.append(part.text)
                    
                    if text_parts:
                        final_response = " ".join(text_parts)
                        print(f"Agent: {final_response}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())
