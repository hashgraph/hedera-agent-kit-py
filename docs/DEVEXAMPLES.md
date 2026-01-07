# Developer Examples

## 📦 Clone & Test the SDK Examples

### 1 – Install

```bash
git clone https://github.com/hashgraph/hedera-agent-kit-py.git
```

**Requirements**
- Python 3.10 or higher (up to 3.13)
- [Poetry](https://python-poetry.org/docs/#installation) - Python dependency management tool

**Repo Dependencies**
* [Hiero SDK Python](https://github.com/hiero-ledger/hiero-sdk-python) and Hedera API
* [LangChain Tools](https://python.langchain.com/docs/concepts/tools/)
* python-dotenv

### 2 – Configure

#### For Agent Examples

**LangChain v1** (with LangGraph)
Copy `python/examples/langchain/.env.example` to `python/examples/langchain/.env`:

```bash
cd python/examples/langchain
cp .env.example .env
```

**LangChain Classic** (v0.3)
Copy `python/examples/langchain-classic/.env.example` to `python/examples/langchain-classic/.env`:

```bash
cd python/examples/langchain-classic
cp .env.example .env
```

Add your [Hedera API](https://portal.hedera.com/dashboard) and [OpenAI](https://platform.openai.com/api-keys) keys:

```env
ACCOUNT_ID=0.0.xxxxx
PRIVATE_KEY=302e... # DER encoded private key
OPENAI_API_KEY=sk-proj-...
```

> [!NOTE]
> **Using Hex Encoded Keys (ECDSA/ED25519)?**
> The `PrivateKey.from_string()` method used in the examples expects a DER encoded key string.
> If you are using a hex encoded private key, you should update the code to use the specific factory method:
> - `PrivateKey.from_ed25519(bytes.fromhex(os.getenv("PRIVATE_KEY")))`
> - `PrivateKey.from_ecdsa(bytes.fromhex(os.getenv("PRIVATE_KEY")))`

### 3 – Choose an Example

Try out one or more of the example agents:

* **Option A -** [Plugin Tool Calling Agent (LangChain v1)](#option-a-run-the-plugin-tool-calling-agent-langchain-v1)
* **Option B -** [Tool Calling Agent (LangChain Classic)](#option-b-run-the-tool-calling-agent-langchain-classic)
* **Option C -** [Plugin Tool Calling Agent (LangChain Classic)](#option-c-run-the-plugin-tool-calling-agent-langchain-classic)
* **Option D -** [Structured Chat Agent (LangChain Classic)](#option-d-run-the-structured-chat-agent-langchain-classic)

> **Coming Soon:** Google ADK (Agents Development Kit) integration is planned for a future release.


> **Coming Soon:** Return Bytes mode is planned for a future release. In this mode agents will create the transaction requested in natural language and return the bytes to the user to execute the transaction in another tool.
---

### Option A: Run the Plugin Tool Calling Agent (LangChain v1)

This agent uses LangChain v1 with LangGraph support, featuring plugin-based tool management and in-memory conversation state. Uses GPT-4o-mini as the default LLM.

Found at `python/examples/langchain/plugin_tool_calling_agent.py`.

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/langchain
poetry install
```

2. Then, run the example:

```bash
poetry run python plugin_tool_calling_agent.py
```

3. Interact with the agent. Try out some interactions by asking questions:
   * _What can you help me do with Hedera?_
   * _What's my current HBAR balance?_
   * _Create a new topic called 'Daily Updates'_
   * _Submit the message 'Hello World' to topic 0.0.12345_
   * _Create a fungible token called 'MyToken' with symbol 'MTK'_
   * _Check my balance and then create a topic for announcements_

---

### Option B: Run the Tool Calling Agent (LangChain Classic)

The basic tool-calling agent demonstrates core functionality with LangChain Classic. This is a simple template you can use with other LLMs.

Found at `python/examples/langchain-classic/tool_calling_agent.py`.

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/langchain-classic
poetry install
```

2. Then, run the example:

```bash
poetry run python tool_calling_agent.py
```

---

### Option C: Run the Plugin Tool Calling Agent (LangChain Classic)

Enhanced tool-calling agent with plugin support for extended functionality. Uses conversation memory and GPT-4o-mini.

Found at `python/examples/langchain-classic/plugin_tool_calling_agent.py`.

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/langchain-classic
poetry install
```

2. Then, run the example:

```bash
poetry run python plugin_tool_calling_agent.py
```

You can modify the `plugin_tool_calling_agent.py` file to customize which tools are available:

```python
from hedera_agent_kit.plugins import (
    core_token_plugin_tool_names,
    core_consensus_plugin_tool_names,
    core_account_plugin_tool_names,
    # ... other plugins
)

CREATE_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"]
CREATE_TOPIC_TOOL = core_consensus_plugin_tool_names["CREATE_TOPIC_TOOL"]
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
```

And configure which plugins to load:

```python
configuration: Configuration = Configuration(
    tools=[],  # Empty = load all tools from plugins
    plugins=[
        core_consensus_plugin,
        core_account_plugin,
        core_token_plugin,
        # Add or remove plugins as needed
    ],
    context=Context(mode=AgentMode.AUTONOMOUS, account_id=str(operator_id)),
)
```

---

### Option D: Run the Structured Chat Agent (LangChain Classic)

The structured chat agent enables you to interact with the Hedera blockchain using GPT-4 as the LLM. This agent uses conversation memory for multi-turn interactions.

Found at `python/examples/langchain-classic/structured_chat_agent.py`.

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/langchain-classic
poetry install
```

2. Then, run the example:

```bash
poetry run python structured_chat_agent.py
```

---

## Example Interactions

Once you run any of the agents, you'll enter an interactive CLI chatbot. You can:

- Ask questions about Hedera operations
- Request to create accounts, topics, or tokens
- Transfer HBAR
- Query balances and account information
- Type `exit` or `quit` to end the session

### Sample Commands

```
You: Create a new account with 10 HBAR
You: What is my HBAR balance?
You: Transfer 5 HBAR to account 0.0.800
You: Create a new topic with memo "My first topic"
You: Create a fungible token with 1000 initial supply
You: exit
```

---

## Additional LLM Providers

The Python examples support multiple LLM providers through LangChain:

- **OpenAI** (default): `langchain-openai`
- **Anthropic**: `langchain-anthropic`
- **Groq**: `langchain-groq`

To use a different provider, modify the model initialization in the script and set the appropriate API key in your `.env` file:

```python
# OpenAI (default)
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4o-mini")

# Anthropic
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-3-sonnet-20240229")

# Groq
from langchain_groq import ChatGroq
model = ChatGroq(model="llama-3.1-70b-versatile")
```

---

## Available Plugins

The Hedera Agent Kit includes these built-in plugins:

| Plugin | Description |
|--------|-------------|
| `core_account_plugin` | Account creation, deletion, updates, HBAR transfers |
| `core_account_query_plugin` | Query HBAR balance, account info |
| `core_consensus_plugin` | Topic creation, deletion, message submission |
| `core_consensus_query_plugin` | Query topic info and messages |
| `core_token_plugin` | Token creation, transfers, minting, airdrops |
| `core_token_query_plugin` | Query token info and balances |
| `core_evm_plugin` | ERC20/ERC721 smart contract interactions |
| `core_misc_query_plugin` | Exchange rates and misc queries |
| `core_transaction_query_plugin` | Transaction record queries |

For a complete list of available tools, see [HEDERAPLUGINS.md](./HEDERAPLUGINS.md).
