# LangChain Classic Examples

This directory contains examples of using Hedera Agent Kit with LangChain Classic agents.

## Prerequisites

- Python 3.8 or higher
- [Poetry](https://python-poetry.org/docs/#installation) - Python dependency management tool
- Hedera Testnet account (get one from [Hedera Portal](https://portal.hedera.com/))
- OpenAI API key

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

This folder contains three agent examples:

### 1. Tool Calling Agent (`tool_calling_agent.py`)

Basic tool-calling agent that demonstrates the core functionality.

```bash
poetry run python tool_calling_agent.py
```

### 2. Plugin Tool Calling Agent (`plugin_tool_calling_agent.py`)

Enhanced tool-calling agent with plugin support for extended functionality.

```bash
poetry run python plugin_tool_calling_agent.py
```

### 3. Structured Chat Agent (`structured_chat_agent.py`)

Agent with structured chat capabilities and conversation memory.

```bash
poetry run python structured_chat_agent.py
```

## Usage

Once you run any of the scripts, you'll enter an interactive CLI chatbot. You can:

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
