import asyncio
import os

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit_py.langchain import HederaAgentKitTool
from hedera_agent_kit_py.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit_py.plugins import core_account_plugin
from hedera_agent_kit_py.plugins.core_account_plugin import (
    core_account_plugin_tool_names,
)
from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]


async def bootstrap():
    # Initialize LLM
    model: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")

    # Hedera Client setup (Testnet)
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

    network: Network = Network(
        network="testnet"
    )  # ensure this matches SDK expectations
    client: Client = Client(network)
    client.set_operator(operator_id, operator_key)

    # Configuration placeholder
    configuration: Configuration = Configuration(
        tools=[TRANSFER_HBAR_TOOL],
        plugins=[core_account_plugin],
        context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(operator_id)),
    )

    # Prepare Hedera LangChain toolkit
    hedera_toolkit: HederaLangchainToolkit = HederaLangchainToolkit(
        client=client, configuration=configuration
    )

    # Fetch LangChain tools from toolkit
    tools: list[HederaAgentKitTool] = hedera_toolkit.get_tools()

    # Create the underlying tool-calling agent
    agent = create_agent(
        model,
        tools=tools,
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools and plugin tools",
        checkpointer=InMemorySaver(),
    )

    print("Hedera Agent CLI Chatbot with Plugin Support — type 'exit' to quit")
    print("Available plugin tools:")
    print("- example_greeting_tool: Generate personalized greetings")
    print(
        "- example_hbar_transfer_tool: Transfer HBAR to account 0.0.800 (demonstrates transaction strategy)"
    )
    print("")

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # CLI loop
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            response = await agent.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_input,
                        }
                    ]
                },
                context=configuration.context,
                config=config,
            )
            final_message = response["messages"][-1]
            print(f"AI: {final_message.content}")
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    asyncio.run(bootstrap())
