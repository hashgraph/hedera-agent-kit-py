# Hedera Agent Kit - Google ADK Example

This example demonstrates using the Hedera Agent Kit with Google's Agent Development Kit (ADK) and Gemini models.

## Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- A Hedera testnet account from [portal.hedera.com](https://portal.hedera.com/dashboard)
- A Google AI API key from [Google AI Studio](https://aistudio.google.com/)

## Setup

1. Install dependencies:

```bash
poetry install
```

2. Configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
ACCOUNT_ID=0.0.xxxxx
PRIVATE_KEY=302e...
GOOGLE_API_KEY=your-google-api-key
```

## Run the Example

```bash
poetry run python plugin_tool_calling_agent.py
```

## Example Interactions

Once running, you can interact with the agent:

```
You: What's my HBAR balance?
You: Create a new topic called "My Updates"
You: Transfer 1 HBAR to account 0.0.12345
You: Create a fungible token called "TestToken" with symbol "TTK"
You: exit
```

## Available Plugins

This example loads all available plugins:

| Plugin                          | Description                                         |
|---------------------------------|-----------------------------------------------------|
| `core_account_plugin`           | Account creation, deletion, updates, HBAR transfers |
| `core_account_query_plugin`     | Query HBAR balance, account info                    |
| `core_consensus_plugin`         | Topic creation, deletion, message submission        |
| `core_consensus_query_plugin`   | Query topic info and messages                       |
| `core_token_plugin`             | Token creation, transfers, minting, airdrops        |
| `core_token_query_plugin`       | Query token info and balances                       |
| `core_evm_plugin`               | ERC20/ERC721 smart contract interactions            |
| `core_evm_query_plugin`         | Query EVM contract info                             |
| `core_misc_query_plugin`        | Exchange rates and misc queries                     |
| `core_transaction_query_plugin` | Transaction record queries                          |
