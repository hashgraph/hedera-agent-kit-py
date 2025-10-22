import asyncio
import os

from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from hedera_agent_kit_py.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit_py.plugins import core_account_plugin
from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration
from dotenv import load_dotenv

load_dotenv('.env')

async def bootstrap():
    # Initialize LLM
    model = ChatOpenAI(model="gpt-4o-mini")

    # Hedera Client setup (Testnet)
    operator_id = AccountId.from_string(os.getenv('ACCOUNT_ID'))
    operator_key = PrivateKey.from_string(os.getenv('PRIVATE_KEY'))

    network = Network(network="testnet")  # ensure this matches SDK expectations
    client = Client(network)
    client.set_operator(operator_id, operator_key)

    # Configuration placeholder
    configuration = Configuration(
        tools=["TRANSFER_HBAR_TOOL"],
        plugins=[core_account_plugin],
        context=Context(mode=AgentMode.AUTONOMOUS)
    )

    # Prepare Hedera LangChain toolkit
    hedera_toolkit = HederaLangchainToolkit(client=client, configuration=configuration)

    # Chat prompt template
    # FIXME: the usage of ChatPromptTemplate has changed
    system_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to Hedera blockchain tools and plugin tools"),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Fetch LangChain tools from toolkit
    tools = hedera_toolkit.get_tools()

    # Create the underlying tool-calling agent
    agent = create_agent(model, tools,
                         system_prompt='You are a helpful assistant with access to Hedera blockchain tools and plugin tools',
                         checkpointer=InMemorySaver())

    print("Hedera Agent CLI Chatbot with Plugin Support — type 'exit' to quit")
    print("Available plugin tools:")
    print("- example_greeting_tool: Generate personalized greetings")
    print("- example_hbar_transfer_tool: Transfer HBAR to account 0.0.800 (demonstrates transaction strategy)")
    print("")

    # CLI loop
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            command = Command(update={"messages": [{"role": "user", "content": user_input}]})
            response = await agent.invoke(
                command, context=configuration.context)
            print(f"AI: {response.get('output', response)}")
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    asyncio.run(bootstrap())
