# LangChain v1 Examples

This directory contains examples of using Hedera Agent Kit with LangChain v1 and LangGraph agents.

## Prerequisites

- Python 3.10 or higher (up to 3.13)
- [Poetry](https://python-poetry.org/docs/#installation) - Python dependency management tool
- Hedera Testnet account (get one from [Hedera Portal](https://portal.hedera.com/))
- OpenAI API key (or Anthropic/Groq API key for alternative models)

## Setup

### 1. Install Poetry

If you don't have Poetry installed, install it following the [official installation guide](https://python-poetry.org/docs/#installation).

### 2. Configure Environment Variables

Create a `.env` file based on the `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file and fill in your credentials:

```env
ACCOUNT_ID="0.0.xxxxx"  # Your Hedera testnet account ID from https://portal.hedera.com/dashboard
PRIVATE_KEY="302..."     # Your ECDSA encoded private key
OPENAI_API_KEY="sk-proj-..."  # Your OpenAI API key
```

### 3. Install Dependencies

```bash
poetry install
```

## Available Agent Scripts

This folder contains one agent example:

### Plugin Tool Calling Agent (`plugin_tool_calling_agent.py`)

LangChain v1 agent with LangGraph support, featuring plugin-based tool management and in-memory conversation state.

```bash
poetry run python plugin_tool_calling_agent.py
```

## Usage

Once you run the script, you'll enter an interactive CLI chatbot. You can:

- Ask questions about Hedera operations
- Request to create accounts, topics, or tokens
- Transfer HBAR
- Query balances and account information
- Type `exit` or `quit` to end the session

## Example Interactions

```
You: Create a new account with 10 HBAR
You: What is my HBAR balance?
You: Transfer 5 HBAR to account 0.0.800
You: Create a new topic with memo "My first topic"
You: exit
```

## Additional LLM Providers

This example supports multiple LLM providers through LangChain:

- **OpenAI** (default): `langchain-openai`
- **Anthropic**: `langchain-anthropic`
- **Groq**: `langchain-groq`

To use a different provider, modify the model initialization in the script and set the appropriate API key in your `.env` file.
