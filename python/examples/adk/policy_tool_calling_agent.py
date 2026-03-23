"""Hedera Agent CLI Chatbot using Google ADK with MaxRecipientsPolicy"""

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
from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy
from hedera_agent_kit.plugins import core_account_plugin, core_token_plugin

load_dotenv(".env")

APP_NAME = "hedera_policy_agent_app"
USER_ID = "hedera_policy_user"
SESSION_ID = "session_1"


async def bootstrap():
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

    network: Network = Network(network="testnet")
    client: Client = Client(network)
    client.set_operator(operator_id, operator_key)

    # Instantiate the MaxRecipientsPolicy, restricting transfers to a maximum of 2 recipients
    policy = MaxRecipientsPolicy(max_recipients=2)

    # We load only the core_account_plugin and core_token_plugin, which provide the base set
    # of tools that the MaxRecipientsPolicy operates on:
    # - TRANSFER_HBAR_TOOL
    # - TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
    # - AIRDROP_FUNGIBLE_TOKEN_TOOL
    # - TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
    # - TRANSFER_NFT_WITH_ALLOWANCE_TOOL
    # - TRANSFER_NON_FUNGIBLE_TOKEN_TOOL
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

    hedera_agent = Agent(
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

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=hedera_agent, app_name=APP_NAME, session_service=session_service
    )

    print("=" * 60)
    print("Hedera Agent CLI Chatbot with Google ADK (Policy Restricted)")
    print("=" * 60)
    print("This agent explicitly loads tools related to Transfers and Airdrops.")
    print("MaxRecipientsPolicy is ACTIVE: All transfers to >2 recipients are blocked.")
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
