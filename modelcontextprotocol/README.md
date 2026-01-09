# Hedera MCP Server

This directory contains the MCP server implementation for Hedera Agent Kit.

## Usage

```bash
poetry install
poetry run python server.py --ledger-id testnet --tools all
```

## Antigravity (VS Code) Configuration

To use this MCP server in Antigravity or VS Code, add the following to your MCP settings configuration file (e.g. `~/.gemini/antigravity/mcp_config.json` or VS Code settings).

**Important**: You must use **absolute paths** for both the python script and the working directory.

```json
{
	"mcpServers": {
		"hedera-py": {
			"command": "/ABSOLUTE/PATH/TO/poetry",
			"args": [
				"-C",
				"/ABSOLUTE/PATH/TO/hedera-agent-kit-py/modelcontextprotocol",
				"run",
				"python",
				"server.py"
			],
			"env": {
				"HEDERA_OPERATOR_ID": "0.0.xxxxx",
				"HEDERA_OPERATOR_KEY": "302e..."
			}
		}
	}
}
```

## Available Tools

The server defaults to a minimal set of plugins (Token, Account, Consensus) to stay within tool limits (e.g. Antigravity is limited to 100 tools).

To enable more capabilities (EVM, Queries, etc.), you must manually update `server.py` to import and register additional plugins from `hedera_agent_kit.plugins`.

Available plugins include:
- `core_evm_plugin`
- `core_token_query_plugin`
- `core_account_query_plugin`
- `core_consensus_query_plugin`
- `core_transaction_query_plugin`
- `core_misc_query_plugin`

You can filter enabled tools using the `--tools` argument.

## Configuration Arguments

The `server.py` script accepts the following command-line arguments:

| Argument | Description | Default | Choices |
| :--- | :--- | :--- | :--- |
| `--tools` | Comma-separated list of tools to enable. | All available | `all` or specific tool names |
| `--agent-mode` | Execution mode for the agent. | `autonomous` | `autonomous`, `returnBytes` |
| `--account-id` | Hedera Account ID to use for operations. | None | Valid Account ID (e.g. `0.0.1234`) |
| `--public-key` | Public Key for the account. **Must be DER encoded.** | None | DER encoded string |
| `--ledger-id` | Network to connect to. | `testnet` | `testnet`, `mainnet` |

### Key Formats

Both **ECDSA** and **ED25519** keys are supported. For **HEX** format of keys changes to the `server.py` code are required. Follow https://github.com/hiero-ledger/hiero-sdk-python for more information on `Client.set_operator` method.

