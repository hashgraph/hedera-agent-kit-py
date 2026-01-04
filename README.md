# Hedera Agent Kit (Python)

![PyPI version](https://badgen.net/pypi/v/hedera-agent-kit)
![license](https://badgen.net/github/license/hashgraph/hedera-agent-kit-py)
![Python](https://badgen.net/badge/python/3.10%2B/blue)

> Build Hedera-powered AI agents **in under a minute**.

## 📋 Contents

- [Key Features](#key-features)
- [About the Agent Kit Functionality](#agent-kit-functionality)
- [Developer Examples](#developer-examples)
- [🚀 60-Second Quick-Start](#-60-second-quick-start)
- [Agent Execution Modes](#agent-execution-modes)
- [Hedera Plugins & Tools](#hedera-plugins--tools)
- [Creating Plugins & Contributing](#creating-plugins--contributing)
- [License](#license)
- [Credits](#credits)

---

## Key Features

This is the **Python edition** of the [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit-js), providing a flexible and extensible framework for building **AI-powered Hedera agents**.

- 🔌 **Plugin architecture** for easy extensibility
- 🧠 **LangChain integration** with support for multiple AI frameworks
- 🪙 **Comprehensive Hedera tools**, including:
  - Token creation and management (HTS)
  - Smart contract execution (EVM)
  - Account operations
  - Topic (HCS) creation and messaging
  - Transaction scheduling
  - Allowances and approvals

---

## Agent Kit Functionality

The list of currently available Hedera plugins and functionality can be found in the [Plugins & Tools section](#hedera-plugins--tools) of this page.

👉 See [docs/HEDERAPLUGINS.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/HEDERAPLUGINS.md) for the full catalogue & usage examples.

Want to add more functionality from Hedera Services? [Open an issue](https://github.com/hashgraph/hedera-agent-kit-py/issues/new?template=toolkit_feature_request.yml&labels=feature-request)!

---

### Third Party Plugins

- CoinCap Plugin - provides access to the [**CoinCap API service**](https://www.coincap.io) to access cryptocurrency market data. It exposes the action (`get HBAR price in USD`) to get the current price of HBAR in USD currency, by using it you can ask your agent to get your current HBAR balance expressed in USD.
  - PyPI: [https://pypi.org/project/coincap-hedera-agent-kit-plugin](https://pypi.org/project/coincap-hedera-agent-kit-plugin)
  - Source: [https://github.com/henrytongv/hedera-agent-kit-py](https://github.com/henrytongv/hedera-agent-kit-py)
  - ✅ Tested/endorsed version of plugin: coincap-hedera-agent-kit-plugin==0.8

---

## Developer Examples

You can try out examples of the different types of agents you can build by following the instructions in the [Developer Examples](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md) doc in this repo.

First follow instructions in the [Developer Examples to clone and configure the example](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md), then choose from one of the examples to run:

- **Option A -** [Plugin Tool Calling Agent (LangChain v1)](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md#option-a-run-the-plugin-tool-calling-agent-langchain-v1)
- **Option B -** [Tool Calling Agent (LangChain Classic)](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md#option-b-run-the-tool-calling-agent-langchain-classic)
- **Option C -** [Plugin Tool Calling Agent (LangChain Classic)](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md#option-c-run-the-plugin-tool-calling-agent-langchain-classic)
- **Option D -** [Structured Chat Agent (LangChain Classic)](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/DEVEXAMPLES.md#option-d-run-the-structured-chat-agent-langchain-classic)

---

## 🚀 60-Second Quick-Start

See more info at [https://pypi.org/project/hedera-agent-kit/](https://pypi.org/project/hedera-agent-kit/)

### 🆓 Free AI Options Available!

- **Ollama**: 100% free, runs on your computer, no API key needed
- **[Groq](https://console.groq.com/keys)**: Offers generous free tier with API key
- **[Claude](https://console.anthropic.com/settings/keys) & [OpenAI](https://platform.openai.com/api-keys)**: Paid options for production use

### 1 – Project Setup

Create a directory for your project:

```bash
mkdir hello-hedera-agent-kit
cd hello-hedera-agent-kit
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install dependencies:

```bash
pip install hedera-agent-kit langchain langchain-openai langgraph python-dotenv
```

### 2 – Configure: Add Environment Variables

Create an `.env` file in the root directory of your project:

```bash
touch .env
```

If you already have a **testnet** account, you can use it. Otherwise, you can create a new one at [https://portal.hedera.com/dashboard](https://portal.hedera.com/dashboard)

Add the following to the .env file:

```env
# Required: Hedera credentials (get free testnet account at https://portal.hedera.com/dashboard)
ACCOUNT_ID="0.0.xxxxx"
PRIVATE_KEY="302..." # DER encoded private key (e.g. from Hedera Portal)

# Optional: Add the API key for your chosen AI provider
OPENAI_API_KEY="sk-proj-..."      # For OpenAI (https://platform.openai.com/api-keys)
ANTHROPIC_API_KEY="sk-ant-..."    # For Claude (https://console.anthropic.com)
GROQ_API_KEY="gsk_..."            # For Groq free tier (https://console.groq.com/keys)
# Ollama doesn't need an API key (runs locally)
```


> NOTE:
> **Using Hex Encoded Keys (ECDSA/ED25519)?**
> The `PrivateKey.from_string()` method used in the examples expects a DER encoded key string.
> If you are using a hex encoded private key (common in some wallets), you should update the code to use the specific factory method:
> - `PrivateKey.from_ed25519(bytes.fromhex(os.getenv("PRIVATE_KEY")))`
> - `PrivateKey.from_ecdsa(bytes.fromhex(os.getenv("PRIVATE_KEY")))`


### 3 – Simple "Hello Hedera Agent Kit" Example

Create a new file called `main.py`:

```bash
touch main.py
```

Add the following code:

```python
# main.py
import asyncio
import os

from dotenv import load_dotenv
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_account_query_plugin,
    core_token_plugin,
    core_consensus_plugin,
)
from hedera_agent_kit.shared.configuration import Configuration, Context, AgentMode
from hiero_sdk_python import Client, Network, AccountId, PrivateKey
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


async def main():
    # Hedera client setup (Testnet by default)
    account_id = AccountId.from_string(os.getenv("ACCOUNT_ID"))
    private_key = PrivateKey.from_string(os.getenv("PRIVATE_KEY"))
    client = Client(Network(network="testnet"))
    client.set_operator(account_id, private_key)

    # Prepare Hedera toolkit
    hedera_toolkit = HederaLangchainToolkit(
        client=client,
        configuration=Configuration(
            tools=[],  # Empty = load all tools from plugins
            plugins=[
                core_account_plugin,
                core_account_query_plugin,
                core_token_plugin,
                core_consensus_plugin,
            ],
            context=Context(
                mode=AgentMode.AUTONOMOUS,
                account_id=str(account_id),
            ),
        ),
    )

    tools = hedera_toolkit.get_tools()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        checkpointer=MemorySaver(),
        system_prompt="You are a helpful assistant with access to Hedera blockchain tools and plugin tools",
    )

    print("Sending a message to the agent...")

    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's my balance?"}]},
        config={"configurable": {"thread_id": "1"}},
    )

    final_message_content = response["messages"][-1].content
    print("\n--- Agent Response ---")
    print(final_message_content)
    print("----------------------")


if __name__ == "__main__":
    asyncio.run(main())
```

### 4 – Run Your "Hello Hedera Agent Kit" Example

From the root directory, run your example agent:

```bash
python main.py
```

If you would like, try adding in other prompts to the agent to see what it can do:

```python
# original
response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "what's my balance?"}]},
    config={"configurable": {"thread_id": "1"}},
)

# or
response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "create a new token called 'TestToken' with symbol 'TEST'"}]},
    config={"configurable": {"thread_id": "1"}},
)

# or
response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "transfer 5 HBAR to account 0.0.1234"}]},
    config={"configurable": {"thread_id": "1"}},
)

# or
response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "create a new topic for project updates"}]},
    config={"configurable": {"thread_id": "1"}},
)
```

> To get other Hedera Agent Kit tools working, take a look at the example agent implementations at [https://github.com/hashgraph/hedera-agent-kit-py/tree/main/python/examples](https://github.com/hashgraph/hedera-agent-kit-py/tree/main/python/examples)

---

## About the Agent Kit

### Agent Execution Modes

This tool has two execution modes with AI agents; autonomous execution and return bytes:

| Mode | Description |
|------|-------------|
| `AgentMode.AUTONOMOUS` | The transaction will be executed autonomously using the operator account. |
| `AgentMode.RETURN_BYTES` | *(Coming Soon)* The transaction bytes will be returned for the user to sign and execute. |

### Hedera Plugins & Tools

The Hedera Agent Kit provides a set of tools, bundled into plugins, to interact with the Hedera network. See how to build your own plugins in [docs/HEDERAPLUGINS.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/HEDERAPLUGINS.md)

Currently, the following plugins are available:

#### Core Account Plugin: Tools for Hedera Account Service operations

- Transfer HBAR
- Create, Update, Delete Account
- Approve and Delete Allowances

#### Core Consensus Plugin: Tools for Hedera Consensus Service (HCS) operations

- Create, Update, Delete Topic
- Submit a message to a Topic

#### Core Token Plugin: Tools for Hedera Token Service operations

- Create Fungible and Non-Fungible Tokens
- Mint Tokens
- Associate and Dissociate Tokens
- Airdrop Fungible Tokens
- Transfer with Allowances

#### Core EVM Plugin: Tools for EVM smart contract operations

- Create and Transfer ERC-20 Tokens
- Create and Transfer ERC-721 Tokens

#### Core Query Plugins: Tools for querying Hedera network data

- Get Account Info and HBAR Balance
- Get Token Info and Balances
- Get Topic Info
- Get Transaction Records
- Get Exchange Rate

_See more in [docs/HEDERAPLUGINS.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/HEDERAPLUGINS.md) and [docs/HEDERATOOLS.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/HEDERATOOLS.md)_

---

## Creating Plugins & Contributing

- You can find a guide for creating plugins in [docs/HEDERAPLUGINS.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/docs/HEDERAPLUGINS.md)

- If you would like to contribute and suggest improvements for the Python SDK, see [CONTRIBUTING.md](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/CONTRIBUTING.md) for details on how to contribute to the Hedera Agent Kit.

---

## License

Apache 2.0

---

## Credits

Special thanks to the developers of the [Stripe Agent Toolkit](https://github.com/stripe/agent-toolkit) who provided the inspiration for the architecture and patterns used in this project.
