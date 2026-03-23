import asyncio
import json
import os

from dotenv import load_dotenv
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from hiero_sdk_python import AccountId, PrivateKey, Client, Network, Transaction

from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration

from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_consensus_plugin,
    core_account_query_plugin,
    core_consensus_query_plugin,
    core_misc_query_plugin,
    core_evm_plugin,
    core_token_plugin,
    core_transaction_query_plugin,
    core_token_query_plugin,
)

load_dotenv(".env")


def extract_bytes_from_agent_response(response: dict) -> str | None:
    """Extracts raw bytes from the AgentExecutor's intermediate steps."""
    intermediate_steps = response.get("intermediate_steps", [])

    if intermediate_steps and len(intermediate_steps) > 0:
        # LangChain Python returns a list of tuples: (AgentAction, observation)
        action, observation = intermediate_steps[0]
        try:
            # Parse the observation if it was returned as a JSON string
            obs_obj = (
                json.loads(observation) if isinstance(observation, str) else observation
            )

            if isinstance(obs_obj, dict):
                # Check for bytes directly or nested in the 'raw' object
                return obs_obj.get("bytes_data") or obs_obj.get("raw", {}).get(
                    "bytes_data"
                )
        except Exception as e:
            print(f"Error parsing observation: {e}")

    return None


async def bootstrap():
    # Initialize OpenAI LLM
    llm = ChatOpenAI(model="gpt-4o-mini")

    account_id_str = os.getenv("ACCOUNT_ID")
    private_key_str = os.getenv("PRIVATE_KEY")

    if not account_id_str or not private_key_str:
        raise ValueError("Please set ACCOUNT_ID and PRIVATE_KEY in your .env file")

    operator_id = AccountId.from_string(account_id_str)
    operator_key = PrivateKey.from_string(private_key_str)
    network = Network(network="testnet")

    # Hedera client setup (Testnet by default)
    human_in_the_loop_client = Client(network)
    human_in_the_loop_client.set_operator(operator_id, operator_key)

    agent_client = Client(network)

    # Prepare Hedera toolkit
    configuration = Configuration(
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
        ],
        context=Context(mode=AgentMode.RETURN_BYTES, account_id=str(operator_id)),
    )

    hedera_toolkit = HederaLangchainToolkit(
        client=agent_client, configuration=configuration
    )
    tools = hedera_toolkit.get_tools()

    # Load the structured chat prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant"),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Create the underlying agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # In-memory conversation history
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    # Wrap everything in an executor that will maintain memory
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        return_intermediate_steps=True,
        verbose=False,
    )

    print('Hedera Agent CLI Chatbot — type "exit" to quit\n')

    while True:
        try:
            user_input = input("You: ").strip()

            # Handle early termination
            if not user_input or user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Invoke the agent
            response = await agent_executor.ainvoke({"input": user_input})
            print(f"AI: {response.get('output', '')}")

            # Extract bytes natively
            bytes_hex = extract_bytes_from_agent_response(response)

            if bytes_hex:
                print("Transaction bytes found. Executing...")

                # Convert hex string to raw bytes and create a transaction
                unsigned_bytes = bytes.fromhex(bytes_hex)
                tx = Transaction.from_bytes(unsigned_bytes)

                # Sign and execute with the human-in-the-loop client
                tx = tx.sign(human_in_the_loop_client.operator_private_key)
                receipt = tx.execute(human_in_the_loop_client)

                print(
                    f"Transaction receipt: {receipt.status.name if hasattr(receipt.status, 'name') else receipt.status}"
                )
                print(f"Transaction result: {receipt.transaction_id}")
            else:
                print("No transaction bytes found in the response.")

        except Exception as err:
            print(f"Error: {err}")


if __name__ == "__main__":
    try:
        asyncio.run(bootstrap())
    except Exception as e:
        print(f"Fatal error during CLI bootstrap: {e}")
        exit(1)
