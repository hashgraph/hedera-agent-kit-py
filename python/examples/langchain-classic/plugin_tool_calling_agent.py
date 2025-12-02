import asyncio
import os

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory, RunnableConfig
from langchain_openai import ChatOpenAI

from hedera_agent_kit_py.langchain import HederaAgentKitTool
from hedera_agent_kit_py.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit_py.plugins import (
    core_account_plugin_tool_names,
    core_account_plugin,
    core_consensus_query_plugin,
    core_consensus_query_plugin_tool_names,
    core_account_query_plugin,
    core_account_query_plugin_tool_names,
    core_consensus_plugin_tool_names,
    core_consensus_plugin,
    core_evm_plugin_tool_names,
    core_evm_plugin,
    core_misc_query_plugin_tool_names,
    core_misc_query_plugin,
    core_transaction_query_plugin,
    core_transaction_query_plugin_tool_names,
    core_token_query_plugin_tool_names,
    core_token_query_plugin,
    core_token_plugin,
    core_token_plugin_tool_names,
)


from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

CREATE_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"]
DELETE_ACCOUNT_TOOL = core_account_plugin_tool_names["DELETE_ACCOUNT_TOOL"]
CREATE_ACCOUNT_TOOL = core_account_plugin_tool_names["CREATE_ACCOUNT_TOOL"]
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
UPDATE_ACCOUNT_TOOL = core_account_plugin_tool_names["UPDATE_ACCOUNT_TOOL"]
CREATE_TOPIC_TOOL = core_consensus_plugin_tool_names["CREATE_TOPIC_TOOL"]
DELETE_TOPIC_TOOL = core_consensus_plugin_tool_names["DELETE_TOPIC_TOOL"]
GET_HBAR_BALANCE_QUERY_TOOL = core_account_query_plugin_tool_names[
    "GET_HBAR_BALANCE_QUERY_TOOL"
]
CREATE_ERC20_TOOL = core_evm_plugin_tool_names["CREATE_ERC20_TOOL"]
SUBMIT_TOPIC_MESSAGE_TOOL = core_consensus_plugin_tool_names[
    "SUBMIT_TOPIC_MESSAGE_TOOL"
]
GET_EXCHANGE_RATE_TOOL = core_misc_query_plugin_tool_names["GET_EXCHANGE_RATE_TOOL"]
GET_TOPIC_INFO_QUERY_TOOL = core_consensus_query_plugin_tool_names[
    "GET_TOPIC_INFO_QUERY_TOOL"
]

GET_ACCOUNT_QUERY_TOOL = core_account_query_plugin_tool_names["GET_ACCOUNT_QUERY_TOOL"]

GET_TRANSACTION_RECORD_QUERY_TOOL = core_transaction_query_plugin_tool_names[
    "GET_TRANSACTION_RECORD_QUERY_TOOL"
]
AIRDROP_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names[
    "AIRDROP_FUNGIBLE_TOKEN_TOOL"
]

GET_TOKEN_INFO_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_TOKEN_INFO_QUERY_TOOL"
]
DISSOCIATE_TOKEN_TOOL = core_token_plugin_tool_names["DISSOCIATE_TOKEN_TOOL"]
GET_PENDING_AIRDROP_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_PENDING_AIRDROP_QUERY_TOOL"
]

DELETE_HBAR_ALLOWANCE_TOOL = core_account_plugin_tool_names[
    "DELETE_HBAR_ALLOWANCE_TOOL"
]

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
        tools=[
            TRANSFER_HBAR_TOOL,
            CREATE_ACCOUNT_TOOL,
            CREATE_TOPIC_TOOL,
            GET_HBAR_BALANCE_QUERY_TOOL,
            GET_TOPIC_INFO_QUERY_TOOL,
            GET_EXCHANGE_RATE_TOOL,
            UPDATE_ACCOUNT_TOOL,
            DELETE_ACCOUNT_TOOL,
            DELETE_TOPIC_TOOL,
            CREATE_ERC20_TOOL,
            SUBMIT_TOPIC_MESSAGE_TOOL,
            GET_ACCOUNT_QUERY_TOOL,
            CREATE_FUNGIBLE_TOKEN_TOOL,
            GET_TRANSACTION_RECORD_QUERY_TOOL,
            GET_TOKEN_INFO_QUERY_TOOL,
            DISSOCIATE_TOKEN_TOOL,
            GET_PENDING_AIRDROP_QUERY_TOOL,
            DELETE_HBAR_ALLOWANCE_TOOL,
            AIRDROP_FUNGIBLE_TOKEN_TOOL,
        ],
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

    # Prepare Hedera LangChain toolkit
    hedera_toolkit: HederaLangchainToolkit = HederaLangchainToolkit(
        client=client, configuration=configuration
    )

    # Fetch LangChain tools from toolkit
    tools: list[HederaAgentKitTool] = hedera_toolkit.get_tools()

    model.bind_tools(tools)
    prompt = ChatPromptTemplate("You are a helpful assistant with access to Hedera blockchain tools and plugin tools")

    # Create the underlying tool-calling agent
    agent = create_tool_calling_agent(model, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)
    memory = InMemoryChatMessageHistory(session_id="test-session")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant."),
            # First put the history
            ("placeholder", "{chat_history}"),
            # Then the new input
            ("human", "{input}"),
            # Finally the scratchpad
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        lambda session_id: memory,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    print("Hedera Agent CLI Chatbot with Plugin Support — type 'exit' to quit")
    print("Available plugin tools:")
    print("- example_greeting_tool: Generate personalized greetings")
    print(
        "- example_hbar_transfer_tool: Transfer HBAR to account 0.0.800 (demonstrates transaction strategy)"
    )
    print("")


    # CLI loop
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            agent_with_chat_history.invoke(
                {"input": "Hi, I'm polly! What's the output of magic_function of 3?"}, config=config
            )



        except Exception as e:
            print("Error:", e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())
