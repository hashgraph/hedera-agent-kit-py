
import sys
import os
import argparse
from dotenv import load_dotenv

# Redirect stdout to stderr immediately to avoid polluting an MCP channel
original_stdout = sys.stdout
sys.stdout = sys.stderr

from hiero_sdk_python import Client, Network, AccountId, PrivateKey
from hedera_agent_kit.mcp import HederaMCPToolkit
from hedera_agent_kit.shared.configuration import Configuration, Context
from hedera_agent_kit.plugins import (
    core_token_plugin,
    core_account_plugin,
    core_consensus_plugin, core_consensus_query_plugin,
)

def log(message: str, level: str = "info"):
    prefix = "❌" if level == "error" else "⚠️" if level == "warn" else "✅"
    sys.stderr.write(f"{prefix} {message}\n")

def parse_args():
    parser = argparse.ArgumentParser(description="Hedera MCP Server")
    parser.add_argument("--tools", type=str, help="Comma-separated list of tools to enable")
    parser.add_argument("--agent-mode", type=str,  choices=["autonomous", "returnBytes"], default="autonomous", help="Agent mode")
    parser.add_argument("--account-id", type=str, help="Hedera Account ID")
    parser.add_argument("--public-key", type=str, help="Public Key")
    parser.add_argument("--ledger-id", type=str, choices=["testnet", "mainnet"], default="testnet", help="Ledger ID")
    return parser.parse_args()

def main():
    load_dotenv(os.path.join(os.getcwd(), ".env")) # or parent .env
    load_dotenv(os.path.join(os.path.dirname(os.getcwd()), ".env"))
    
    args = parse_args()
    
    # Client setup
    if args.ledger_id == "mainnet":
        network: Network = Network(
            network="mainnet"
        )
        client: Client = Client(network)
        log("Using Mainnet", "info")
    else:
        network: Network = Network(
            network="testnet"
        )
        client: Client = Client(network)
        log("Using Testnet", "info")

    operator_id = os.getenv("HEDERA_OPERATOR_ID")
    operator_key = os.getenv("HEDERA_OPERATOR_KEY")

    if operator_id and operator_key:
        try:
            client.set_operator(AccountId.from_string(operator_id),PrivateKey.from_string(operator_key))
            log(f"Operator set: {operator_id}", "info")
        except Exception as e:
             log(f"Failed to set operator: {e}", "error")
             raise
    else:
        log("No operator credentials found in environment variables", "warn")
    
    context = Context(
        account_id=operator_id,
        account_public_key=PrivateKey.from_string(operator_key).public_key().to_string(),
        mode=args.agent_mode
    )

    tools_list = args.tools.split(",") if args.tools and args.tools != "all" else None
    
    config = Configuration(
        tools=tools_list,
        context=context,
        plugins=[core_token_plugin, core_account_plugin, core_consensus_plugin, core_consensus_query_plugin]
    )

    server = HederaMCPToolkit(client, config)

    sys.stdout = original_stdout
    
    log("Hedera MCP Server running on stdio", "info")
    # Run the server
    server.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Error initializing Hedera MCP server: {str(e)}", "error")
        sys.exit(1)
