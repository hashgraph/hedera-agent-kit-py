import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client, Transaction

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from hedera_agent_kit.adk import HederaADKToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

APP_NAME = "hedera_agent_app"
USER_ID = "hedera_user"
SESSION_ID = "session_1"


def extract_bytes_data(response_data) -> str | None:
    """Safely extracts bytes_data from heavily nested dicts or objects."""
    if not response_data:
        return None

    if isinstance(response_data, dict):
        return response_data.get("bytes_data") or response_data.get("raw", {}).get(
            "bytes_data"
        )

    # Handle object-based responses safely
    raw_attr = getattr(response_data, "raw", None)
    return getattr(raw_attr, "bytes_data", None)


def execute_pending_transactions(function_responses: list, client: Client) -> bool:
    """Searches for raw bytes in function responses, executes them, and returns success status."""
    for func_response in function_responses:
        bytes_hex = extract_bytes_data(getattr(func_response, "response", None))

        if bytes_hex:
            print("⚙️ Transaction bytes found. Executing...")
            tx = Transaction.from_bytes(bytes.fromhex(bytes_hex))
            tx = tx.sign(client.operator_private_key)
            receipt = tx.execute(client)

            print("✅ Transaction executed successfully")
            print(f"🆔 Transaction ID: {receipt.transaction_id}")
            return True

    return False


async def bootstrap():
    """Main entry point for the Hedera ADK agent."""
    # 1. Setup Hedera Client
    operator_id = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    client = Client(Network(network="testnet"))
    client.set_operator(operator_id, PrivateKey.from_string(os.getenv("PRIVATE_KEY")))

    # 2. Setup Toolkit & Agent
    hedera_toolkit = HederaADKToolkit(
        client=client,
        configuration=Configuration(
            tools=[],
            plugins=[],
            context=Context(mode=AgentMode.RETURN_BYTES, account_id=str(operator_id)),
        ),
    )

    agent = Agent(
        model="gemini-3.1-flash-lite-preview",
        name="hedera_agent",
        instruction=(
            "You are a helpful assistant with access to Hedera blockchain tools. "
            "You can help users create accounts, transfer HBAR, manage tokens, "
            "create topics, and query blockchain information. "
            "Always provide clear explanations of the transactions you perform."
        ),
        tools=hedera_toolkit.get_tools(),
    )

    # 3. Setup Runner
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    print("=" * 60)
    print("Hedera Agent CLI Chatbot (Return Bytes Mode)")
    print("=" * 60)
    print("Type 'exit' to end. Try: 'What's my HBAR balance?'\n")

    # 4. Streamlined CLI Loop
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit", ""):
            print("Goodbye!")
            break

        try:
            content = types.Content(role="user", parts=[types.Part(text=user_input)])
            events = runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=content
            )

            function_responses = []
            final_text = ""

            # Accumulate events
            async for event in events:
                if getattr(event, "content", None):
                    function_responses.extend(
                        part.function_response
                        for part in event.content.parts
                        if part.function_response
                    )

                if event.is_final_response():
                    final_text = "".join(
                        part.text
                        for part in event.content.parts
                        if part.text and not part.function_call
                    )

            # Handle Operations
            transaction_executed = execute_pending_transactions(
                function_responses, client
            )

            if not transaction_executed and final_text:
                print(f"Agent: {final_text}")
                if function_responses:
                    print("\n=== Tool Data ===")
                    for fr in function_responses:
                        pprint(getattr(fr, "response", None))

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(bootstrap())
