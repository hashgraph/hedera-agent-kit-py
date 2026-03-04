import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Client, Network, AccountId, PrivateKey
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit import Configuration, HederaMCPServer, Context
from hedera_agent_kit.langchain import HederaLangchainToolkit
from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.plugins import core_misc_query_plugin

# Load environment variables
load_dotenv(".env")

# Ensure HGRAPH_API_KEY is set for HGRAPH_MCP_MAINNET
if "HGRAPH_API_KEY" not in os.environ:
    print("Warning: HGRAPH_API_KEY not set. HGRAPH_MCP_MAINNET might fail.")


# This example demonstrates how to use the Hedera Agent Kit with predefined HGRPAH MCP tools.
# The example is configured with a testnet client, but all the HGRAPH MCP provides mainnet query tools.
# You can use it with your testnet account to query the mainnet information for testing purposes.
async def bootstrap():
    # 1. Initialize Hedera Client (Mainnet for this example as HGRAPH MCP is on Mainnet)
    client = Client(Network("testnet"))

    # Set operator if available, otherwise read-only (which might limit some tools)
    operator_id: AccountId = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    operator_key: PrivateKey = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))
    if operator_id and operator_key:
        client.set_operator(operator_id, operator_key)

    # 2. Define Configuration with MCP Servers
    configuration: Configuration = Configuration(
        plugins=[core_misc_query_plugin],  # load some example tools
        tools=[],  # will load all tools from selected plugins
        mcp_servers=[
            HederaMCPServer.HEDERION_MCP_MAINNET,
            HederaMCPServer.HGRAPH_MCP_MAINNET,  # requires HGRAPH_API_KEY env var
        ],  # only mainnet servers are available
        context=Context(
            account_id=str(operator_id),
            account_public_key=str(operator_key),  # optional
        ),
    )

    # 3. Initialize Toolkit
    hedera_toolkit = HederaLangchainToolkit(client, configuration)

    # 4. Fetch Tools
    # Standard Hedera Tools
    hak_tools = hedera_toolkit.get_tools()
    print(f"Loaded {len(hak_tools)} Hedera Agent Kit tools.")

    # External MCP Tools
    try:
        mcp_tools = await hedera_toolkit.get_mcp_tools()
        print(f"Loaded {len(mcp_tools)} external MCP tools.")
    except Exception as e:
        print(f"Failed to load MCP tools: {e}")
        mcp_tools = []

    all_tools = hak_tools + mcp_tools
    print(f"Total tools: {len(all_tools)}")

    # 5. Create Agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    agent = create_agent(
        model=llm,
        tools=all_tools,
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools and external MCP tools.",
        checkpointer=InMemorySaver(),
    )

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    response_parsing_service: ResponseParserService = ResponseParserService(
        tools=all_tools
    )

    print("Hedera Agent CLI Chatbot with Plugin Support — type 'exit' to quit")

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

            # note: the external mcp tools do not support the response parsing fully
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
