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
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
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
    core_account_plugin_tool_names,
    core_token_plugin_tool_names,
)

load_dotenv(".env")


async def bootstrap():
    client = Client(Network("testnet"))
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))

    if operator_id and operator_key:
        client.set_operator(operator_id, operator_key)

    audit_hook = HcsAuditTrailHook(
        relevant_tools=[
            core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
            core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"],
        ],
        hcs_topic_id="0.0.????",
        # TODO: Replace it with your actual topic ID. Create one using the Hedera Portal Playground or Hedera Agent Kit
    )

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
        tools=[],
        context=Context(
            mode=AgentMode.AUTONOMOUS,
            account_id=str(operator_id),
            hooks=[audit_hook],
        ),
    )

    hedera_toolkit = HederaLangchainToolkit(client, configuration)

    all_tools = hedera_toolkit.get_tools()

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    agent = create_agent(
        model=llm,
        tools=all_tools,
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools. Remember that some of your actions (transfers, token creation) are automatically audited on the consensus service.",
        checkpointer=InMemorySaver(),
    )

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    response_parsing_service: ResponseParserService = ResponseParserService(
        tools=all_tools
    )

    print(
        "Hedera Agent CLI Chatbot with HcsAuditTrailHook Plugin Support — type 'exit' to quit"
    )
    print(
        "This agent has an audit hook on TRANSFER_HBAR_TOOL and CREATE_FUNGIBLE_TOKEN_TOOL."
    )

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

            if not parsed_data:
                print(f"AI: {response['messages'][-1].content}")
            else:
                tool_call = parsed_data[0]
                print(f"AI: {response['messages'][-1].content}")
                print("\n=== Tool Data ===")
                print(
                    "= Direct tool response =\n",
                    tool_call.parsedData.get(
                        "humanMessage", "No human message available"
                    ),
                )
                print("\n= Full tool response =")
                pprint(tool_call.parsedData)

        except Exception as e:
            print("Error:", e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())
