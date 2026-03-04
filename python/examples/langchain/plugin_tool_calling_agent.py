import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Client, Network, AccountId, PrivateKey
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit import Configuration, Context
from hedera_agent_kit.langchain import HederaLangchainToolkit
from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.configuration import AgentMode
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

# Load environment variables
load_dotenv(".env")


# This example demonstrates how to use the Hedera Agent Kit with a comprehensive set of core plugins.
# It is configured for Testnet use with an autonomous agent mode.
async def bootstrap():
    # 1. Initialize Hedera Client
    client = Client(Network("testnet"))

    # Set operator credentials
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

    if operator_id and operator_key:
        client.set_operator(operator_id, operator_key)

    # 2. Define Configuration with Plugins
    # We load the full suite of Hedera core plugins for account, token, and consensus management.
    configuration: Configuration = Configuration(
        plugins=[
            core_account_plugin,
            core_account_query_plugin,
            core_consensus_plugin,
            core_consensus_query_plugin,
            core_token_plugin,
            core_token_query_plugin,
            core_evm_plugin,
            core_evm_query_plugin,
            core_transaction_query_plugin,
            core_misc_query_plugin,
        ],
        tools=[],  # will load all tools from selected plugins automatically
        context=Context(
            mode=AgentMode.AUTONOMOUS,
            account_id=str(operator_id),
            account_public_key=str(operator_key),  # optional
        ),
    )

    # 3. Initialize Toolkit
    hedera_toolkit = HederaLangchainToolkit(client, configuration)

    # 4. Fetch Tools
    # Standard Hedera Tools from the plugins defined above
    all_tools = hedera_toolkit.get_tools()
    print(f"Loaded {len(all_tools)} Hedera Agent Kit tools.")
    print(f"Total tools: {len(all_tools)}")

    # 5. Create Agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    agent = create_agent(
        model=llm,
        tools=all_tools,
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools and plugin tools.",
        checkpointer=InMemorySaver(),
    )

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    response_parsing_service: ResponseParserService = ResponseParserService(
        tools=all_tools
    )

    print("Hedera Agent CLI Chatbot with Plugin Support — type 'exit' to quit")
    print("Ready to handle HBAR transfers, token queries, and consensus topics.")

    # 6. Run Agent CLI loop
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

            # Parse the response to extract tool execution data
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
                    "= Direct tool response =\n",
                    tool_call.parsedData.get(
                        "humanMessage", "No human message available"
                    ),
                )  # <- deterministic tool human-readable response.
                print("\n= Full tool response =")
                pprint(
                    tool_call.parsedData
                )  # <- full object for convenient tool response extraction

        except Exception as e:
            print("Error:", e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())
