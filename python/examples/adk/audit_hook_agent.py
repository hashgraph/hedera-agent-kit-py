"""Hedera Agent CLI Chatbot using Google ADK with HCS Audit Trail Hook"""

import asyncio
import os

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.plugins import (
    core_account_plugin_tool_names,
    core_token_plugin_tool_names,
)

load_dotenv(".env")

APP_NAME = "hedera_audit_agent_app"
USER_ID = "hedera_audit_user"
SESSION_ID = "session_1"


async def bootstrap():
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
        hcs_topic_id="0.0.???",  # Replace it with your actual topic ID. Create one using the Hedera Portal Playground or Hedera Agent Kit
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

    hedera_agent = Agent(
        model="gemini-3.1-flash-lite-preview",
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

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=hedera_agent, app_name=APP_NAME, session_service=session_service
    )

    print("=" * 60)
    print("Hedera Agent CLI Chatbot with Google ADK (Audit Hook Active)")
    print("=" * 60)
    print("Type 'exit' or 'quit' to end the session.")
    print("")

    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            content = types.Content(role="user", parts=[types.Part(text=user_input)])

            events = runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=content
            )

            async for event in events:
                if event.is_final_response():
                    text_parts = []
                    for part in event.content.parts:
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
