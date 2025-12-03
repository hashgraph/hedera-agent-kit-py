import asyncio
import os
import traceback

from dotenv import load_dotenv
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from hiero_sdk_python import AccountId, PrivateKey, Client, Network

from hedera_agent_kit_py.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration

from hedera_agent_kit_py.plugins import (
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


async def bootstrap():
    # 1. Initialize OpenAI LLM
    llm = ChatOpenAI(model="gpt-4o-mini")

    # 2. Hedera Client setup (Testnet)
    account_id_str = os.getenv("ACCOUNT_ID")
    private_key_str = os.getenv("PRIVATE_KEY")

    if not account_id_str or not private_key_str:
        raise ValueError("Please set ACCOUNT_ID and PRIVATE_KEY in your .env file")

    operator_id = AccountId.from_string(account_id_str)
    operator_key = PrivateKey.from_string(private_key_str)

    network = Network(network="testnet")
    client = Client(network)
    client.set_operator(operator_id, operator_key)

    # 3. Configuration & Toolkit
    configuration = Configuration(
        tools=[],  # Plugins will populate the tools automatically. This is equivalent to importing all tools
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
        context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(operator_id)),
    )

    hedera_toolkit = HederaLangchainToolkit(
        client=client, configuration=configuration
    )
    tools = hedera_toolkit.get_tools()

    # 4. Create the Tool Calling Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant"),
            # Placeholder for memory/history
            ("placeholder", "{chat_history}"),
            # The user input
            ("human", "{input}"),
            # Essential placeholder for tool calls (agent_scratchpad)
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # 5. Create the Tool Calling Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 6. Memory Setup
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    # 7. Agent Executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
    )

    print("Hedera Agent CLI Chatbot (Tool Calling) — type 'exit' to quit")

    # 8. CLI Loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Invoke the agent
            response = await agent_executor.ainvoke({"input": user_input})

            # The agent executor returns a dict; the answer is in 'output'
            print(f"AI: {response['output']}")

        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())