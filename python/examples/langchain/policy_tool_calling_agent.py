import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit.langchain import HederaAgentKitTool
from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.plugins import core_account_plugin, core_token_plugin
from hedera_agent_kit.policies import MaxRecipientsPolicy
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration

load_dotenv(".env")


async def bootstrap():
    # Initialize LLM
    model: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")

    # Hedera Client setup (Testnet)
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
            mode=AgentMode.AUTONOMOUS,
            account_id=str(operator_id),
            hooks=[policy],
        ),
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
        system_prompt=(
            "You are a helpful assistant with access to Hedera blockchain tools. "
            "You can help users perform transactions. "
            "IMPORTANT: A MaxRecipientsPolicy is active. You are STRICTLY forbidden from "
            "submitting any transfer (HBAR or Token, with or without allowance) to more than 2 recipients at once."
        ),
        checkpointer=InMemorySaver(),
    )

    response_parsing_service: ResponseParserService = ResponseParserService(tools=tools)

    print("Hedera Agent CLI Chatbot with Policy Enforcement — type 'exit' to quit")
    print("This agent explicitly loads tools related to Transfers and Airdrops.")
    print("MaxRecipientsPolicy is ACTIVE: All transfers to >2 recipients are blocked.")
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
