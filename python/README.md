# 🧠 Hedera Agent Kit (Python)

[![PyPI version](https://badge.fury.io/py/hedera-agent-kit.svg)](https://pypi.org/project/hedera-agent-kit/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

---

This is the **Python edition** of the [Hedera Agent Kit for TypeScript/JavaScript](https://github.com/hedera-dev/hedera-agent-kit).

A flexible and extensible framework for building **AI-powered Hedera agents**.

**Features:**

* 🔌 **Plugin architecture** for easy extensibility
* 🧠 **LangChain integration** with support for multiple AI frameworks
* 🪙 **Comprehensive Hedera tools**, including:
  * Token creation and management (HTS)
  * Smart contract execution (EVM)
  * Account operations
  * Topic (HCS) creation and messaging
  * Transaction scheduling
  * Allowances and approvals

---

## 🚀 Getting Started

### Installation

Install the Hedera Agent Kit from PyPI:

```bash
pip install hedera-agent-kit
```

**Requirements:**
- Python ≥3.10
- Hedera testnet or mainnet account ([create one here](https://portal.hedera.com))

> **Note:**
> This package uses **Hiero SDK 0.1.9** from PyPI.
>
> **Current Limitation:** The kit currently supports **autonomous mode only** (transactions are automatically executed). The **return bytes mode** (where users must sign transaction bytes separately) is not yet supported, as it requires additional Hiero SDK features not available in version 0.1.9.

---

### Quick Start Example

```python
import os
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import Configuration, Context, AgentMode
from hedera_agent_kit.plugins import core_account_plugin, core_token_plugin
from hiero_sdk_python import AccountId, PrivateKey, Client, Network

# Set up Hedera client
account_id = AccountId.from_string(os.getenv("ACCOUNT_ID"))
private_key = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))
client = Client(Network(network="testnet"))
client.set_operator(account_id, private_key)

# Configure the toolkit
config = Configuration(
    plugins=[core_account_plugin, core_token_plugin],
    context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(account_id))
)

# Create toolkit and get tools
toolkit = HederaLangchainToolkit(client=client, configuration=config)
tools = toolkit.get_tools()
```

---

## 🛠️ Development Setup

If you want to contribute or run examples from the repository:

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/hashgraph/hedera-agent-kit-py.git
cd hedera-agent-kit-py/python
```

### 2️⃣ Install with Poetry

```bash
poetry install
```

This creates a Poetry-managed virtual environment with all dependencies.

---

### 3️⃣ Configure Environment Variables

The LangChain examples require API keys and credentials to connect to Hedera and OpenAI.

Copy the example file and edit your own `.env`:

```bash
cd examples/langchain
cp .env.example .env
```

Then open `.env` and fill in your details:

```dotenv
ACCOUNT_ID="0.0."        # your operator account ID from https://portal.hedera.com/dashboard
PRIVATE_KEY="303..."     # ECDSA encoded private key
OPENAI_API_KEY="sk-proj-"  # your OpenAI API key
```

> ⚠️ Never commit your `.env` file — it contains sensitive credentials.

---

### 4️⃣ Run the LangChain Examples

From the `python/examples/langchain` directory:

```bash
poetry run python plugin_tool_calling_agent.py
```

This launches an example agent, demonstrating how to use the Hedera Agent Kit with LangChain tools and plugins.

---

## 📚 Usage

After installing via pip, you can use the toolkit in your Python projects:

```python
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import Configuration, Context, AgentMode
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_token_plugin,
    core_consensus_plugin,
    core_evm_plugin,
)
```

See the [examples directory](https://github.com/hashgraph/hedera-agent-kit-py/tree/main/python/examples) for complete working examples with LangChain.

---

## Plugins and Available Tools

### Core Account Plugin Tools (`core_account_plugin`)

This plugin provides tools for Hedera **Account Service operations**:

| Tool Name                        | Description                                                                                                    | Usage                                                                                                                                                                                                                                       |
|----------------------------------|----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---


### Core Account Query Plugin Tools (`core_account_query-plugin`)

This plugin provides tools for fetching **Account Service (HAS)** related information from Hedera Mirror Node.

| Tool Name                               | Description                                                          | Usage                                                                                                                   |
|-----------------------------------------|----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|



### Core Consensus Plugin Tools (`core_consensus_plugin`)

A plugin for **Consensus Service (HCS)**, enabling creation and posting to topics.

| Tool Name                   | Description                                       | Usage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|-----------------------------|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|



### Core Consensus Query Plugin Tools (`core_consensus_query-plugin`)

This plugin provides tools for fetching **Consensus Service (HCS)** related information from Hedera Mirror Node.

| Tool Name                       | Description                                                          | Usage                                                                                                      |
|---------------------------------|----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|


### Core Token Plugin Tools (`core_token_plugin`)

A plugin for the Hedera **Token Service (HTS)**, enabling creation and management of fungible and non-fungible tokens.

| Tool Name                                     | Description                                                   | Usage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-----------------------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

### Core Token Query Plugin Tools (`core_token_query_plugin`)

This plugin provides tools for fetching **Token Service (HTS)** related information from Hedera Mirror Node.

| Tool Name                   | Description                                   | Usage                                                    |
|-----------------------------|-----------------------------------------------|----------------------------------------------------------|


---

### Core EVM Plugin Tools (`core_evm_plugin`)

This plugin provides tools for interacting with EVM smart contracts on Hedera, including creating and managing ERC-20
and ERC-721 tokens via on-chain factory contracts and standard function calls.

| Tool Name              | Description                                           | Usage                                                                                                                                           |
|------------------------|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|


---


### Core EVM Query Plugin Tools (`core_evm_query_plugin`)

This plugin provides tools for fetching EVM smart contract-related information from Hedera Mirror Node.

| Tool Name                      | Description                               | Usage                               |
|--------------------------------|-------------------------------------------|-------------------------------------|

---

### Core Transactions Plugin Tools (`core_transactions_plugin`)

Tools for **transaction-related operations** on Hedera.

| Tool Name                           | Description                                | Usage                                                                         |
|-------------------------------------|--------------------------------------------|-------------------------------------------------------------------------------|



### Core Misc Queries Plugin Tools (`core_misc_query_plugin`)

This plugin provides tools for fetching miscellaneous information from the Hedera Mirror Node.

| Tool Name                | Description                                   | Usage                                                                                     |
|--------------------------|-----------------------------------------------|-------------------------------------------------------------------------------------------|



## Scheduled Transactions

Scheduled transactions are **not separate tools** — they use the *same tools* you already know, but with **additional optional parameters** passed in a
`schedulingParams` object.

From the user's perspective, scheduling simply means asking to **execute a transaction later**, or **once all signatures
are collected**, instead of immediately.

If `schedulingParams.isScheduled` is `false` or omitted, all other scheduling parameters are ignored.

---

**Example usage in plain english**

```
Schedule a mint for token 0.0.5005 with metadata https://example.com/nft/1.json
```

```
Schedule Mint 0.0.5005 with metadata: ipfs://baf/metadata.json. Make it expire at 11.11.2025 10:00:00 and wait for its expiration time with executing it.
```

```
Schedule mint for token 0.0.5005 with URI ipfs://QmTest123 and use my operator key as admin key
```

```
Schedule mint NFT 0.0.5005 with metadata https://example.com/nft.json and set admin key to 302a300506032b6570032100e0c8ec2758a5879ffac226a13c0c516b799e72e35141a0dd828f94d37988a4b7
```

```
Schedule mint NFT for token 0.0.5005 with metadata ipfs://QmTest456 and let account 0.0.1234 pay for it
```

