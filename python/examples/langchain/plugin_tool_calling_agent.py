import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit_py.langchain import HederaAgentKitTool
from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
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
)

from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")

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

GET_TOKEN_INFO_QUERY_TOOL = core_token_query_plugin_tool_names[
    "GET_TOKEN_INFO_QUERY_TOOL"
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
            GET_TRANSACTION_RECORD_QUERY_TOOL,
            GET_TOKEN_INFO_QUERY_TOOL,
        ],
        plugins=[
            core_consensus_plugin,
            core_account_query_plugin,
            core_consensus_query_plugin,
            core_misc_query_plugin,
            core_evm_plugin,
            core_account_plugin,
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

    # Create the underlying tool-calling agent
    agent = create_agent(
        model,
        tools=tools,
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools and plugin tools",
        checkpointer=InMemorySaver(),
    )

    response_parsing_service: ResponseParserService = ResponseParserService(tools=tools)

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

            parsed_data = response_parsing_service.parse_new_tool_messages(response)

            ## 1. Handle case when NO tool was called (simple chat)
            if not parsed_data:
                print(f"AI: {response['messages'][-1].content}")

            ## 2. Handle tool calls
            else:
                tool_call = parsed_data[0]
                print(
                    f"AI: {response['messages'][-1].content}"
                )  # <- agent response text generated based on the tool call response
                print("\n=== Tool Data ===")
                print(
                    "= Direct tool response =\n", tool_call.parsedData["humanMessage"]
                )  # <- you can use this string for a deterministic tool human-readable response.
                print("\n= Full tool response =")
                pprint(
                    tool_call.parsedData
                )  # <- you can use this object for convenient tool response extraction

        except Exception as e:
            print("Error:", e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())
