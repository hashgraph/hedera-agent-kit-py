import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv
from hiero_sdk_python import Network, AccountId, PrivateKey, Client, Transaction, TopicCreateTransaction, TransactionId
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
    )
    client: Client = Client(network)
    client.set_operator(operator_id, operator_key)

    tx = TopicCreateTransaction().set_memo("Test Topic Creation")
    tx_id = TransactionId.generate(client.operator_account_id)
    tx.set_transaction_id(tx_id)
    tx.node_account_id = AccountId.from_string("0.0.3")
    tx.freeze()
    unsigned_bytes = tx.to_bytes()

    print(f"Transaction bytes: {unsigned_bytes.hex()}")

    tx2 = Transaction.from_bytes(unsigned_bytes)
    receipt = tx2.execute(client)
    print(receipt)

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
        context=Context(mode=AgentMode.RETURN_BYTES, account_id=str(operator_id)),
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

            if not parsed_data:
                print(f"AI: {response['messages'][-1].content}")
                continue

            tool_call = parsed_data[0]

            ## 1. Handle case when NO tool was called (simple chat)
            if not tool_call:
                print(f"AI: {response['messages'][-1].content}")
                continue

            pprint(tool_call.parsedData)

            ##  2. Handle RETURN_BYTES mode

            raw_response = tool_call.parsedData.get('raw')
            bytes_hex_string = raw_response.get("bytes_data") if raw_response else None

            if bytes_hex_string:
                print('Transaction bytes found. Executing...')

                # Convert hex string to raw bytes
                unsigned_bytes = bytes.fromhex(bytes_hex_string)

                # Reconstruct a transaction object from bytes
                tx = Transaction.from_bytes(unsigned_bytes)

                # Sign the transaction with the operator's private key
                tx = tx.sign(client.operator_private_key)

                # Execute the transaction
                result = tx.execute(client)
                receipt = result.receipt

                print(f"Transaction executed successfully with receipt: {receipt}")
                print(f"Transaction ID: {receipt.transactionId}")

            ## 3. Handle QUERY tool calls
            else:
                print(
                    f"AI: {response['messages'][-1].content}"
                )  # <- agent response text generated based on the tool call response
                print("\n=== Tool Data ===")
                print(
                    "= Direct tool response =\n", tool_call.parsedData.get("humanMessage", "N/A")
                )
                print("\n= Full tool response =")
                pprint(
                    tool_call.parsedData
                )

        except Exception as e:
            print("Error:", e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(bootstrap())