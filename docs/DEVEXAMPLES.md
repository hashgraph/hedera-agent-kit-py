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

**Google ADK**
Copy `python/examples/adk/.env.example` to `python/examples/adk/.env`:

```bash
cd python/examples/adk
cp .env.example .env
```

Add your credentials to the `.env` file based on the framework you're using (e.g., [Hedera Account](https://portal.hedera.com/dashboard), [OpenAI](https://platform.openai.com/api-keys) for Langchain, [Google AI Studio](https://aistudio.google.com/) for ADK):

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
* **Option E -** [Preconfigured MCPs Agent (LangChain v1)](#option-e-run-the-preconfigured-mcps-agent-langchain-v1)
* **Option F -** [Plugin Tool Calling Agent (Google ADK)](#option-f-run-the-plugin-tool-calling-agent-google-adk)
* **Option G -** [Return Bytes Mode Agents (ADK & LangChain)](#option-g-run-the-return-bytes-mode-agents-human-in-the-loop)
* **Option H -** [Try out the Audit Hook Agent](#option-h-try-out-the-audit-hook-agent)
* **Option I -** [Try out the Policy Agent](#option-i-try-out-the-policy-agent)

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

### Option E: Run the Preconfigured MCPs Agent (LangChain v1)

This agent demonstrates how to integrate **Hederion MCP** and **Hgraph MCP** using a LangChain v1 agent and the Hedera Agent Kit SDK.

Found at `python/examples/langchain/hedera_mcp_agent.py`.

#### Key Features

* **Hederion MCP:** Acts as a proxy, wrapping internal logic into a single query tool and processing requests on the backend.
* **Hgraph MCP:** Exposes multiple granular query tools, allowing the LangChain agent to handle specific parameters directly.
* **Integration:** Tools are fetched and adapted using the `langchain-mcp-adapters` library.

#### Prerequisites & Notes

* **Mainnet Only:** These MCPs are configured for Mainnet; all queries will be executed on the Hedera Mainnet.
* **API Key:** Hgraph MCP requires a `HGRAPH_API_KEY`. Obtain one at the [Hgraph Dashboard](https://dashboard.hgraph.com/) and add it to your `.env` file.
* **Documentation:**
  * [Hgraph Agent Docs](https://docs.hgraph.com/agent)
  * [Hederion Home](https://hederion.com/)

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/langchain
poetry install
```

2. Then, run the example:

```bash
poetry run python hedera_mcp_agent.py
```

---

### Option F: Run the Plugin Tool Calling Agent (Google ADK)

This agent demonstrates how to use the Hedera Agent Kit with Google's Agent Development Kit (ADK) and the Gemini model.

Found at `python/examples/adk/plugin_tool_calling_agent.py`.

1. First, go into the directory where the example is and install dependencies:

```bash
cd python/examples/adk
poetry install
```

2. Then, run the example:

```bash
poetry run python plugin_tool_calling_agent.py
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

### Option G: Run the Return Bytes Mode Agents (Human-in-the-loop)

These agents demonstrate "Return Bytes" mode, where the agent returns raw transaction bytes for the user to sign and execute manually, enabling human-in-the-loop transaction control.

#### 1. LangChain v1 Return Bytes
Found at `python/examples/langchain/return_bytes_tool_calling_agent.py`.

```bash
cd python/examples/langchain
poetry run python return_bytes_tool_calling_agent.py
```

#### 2. LangChain Classic Return Bytes
Found at `python/examples/langchain-classic/return_bytes_tool_calling_agent.py`.

```bash
cd python/examples/langchain-classic
poetry run python return_bytes_tool_calling_agent.py
```

#### 3. Google ADK Return Bytes
Found at `python/examples/adk/return_bytes_tool_calling_agent.py`.

```bash
cd python/examples/adk
poetry run python return_bytes_tool_calling_agent.py
```

---

### Option H: Try out the Audit Hook Agent

This example demonstrates how to use the `HcsAuditTrailHook` to create an immutable audit trail of agent actions on the Hedera Consensus Service (HCS). Every tool execution is logged to an HCS topic, providing a transparent and tamper-proof record.

**Found at:**
- `python/examples/adk/audit_hook_agent.py`
- `python/examples/langchain/audit_hook_agent.py`

For a deep dive into how hooks and policies work, see [docs/HOOKS_AND_POLICIES.md](./HOOKS_AND_POLICIES.md).

#### Running the Example

1. **Create an HCS Topic**: You must create an HCS topic before running this example.
2. **Configure Environment**: Update `audit_hook_agent.py` and replace `0.0.???` with your actual topic ID.
3. Run the agent using poetry:

```bash
cd python/examples/langchain
poetry run python audit_hook_agent.py
```

---

### Option I: Try out the Policy Agent

This example demonstrates how to use the `MaxRecipientsPolicy` to restrict the number of recipients in transfer and airdrop operations. It enforces the policy by intercepting the operations prior to execution.

**Found at:**
- `python/examples/adk/policy_tool_calling_agent.py`
- `python/examples/langchain/policy_tool_calling_agent.py`

For a deep dive into how hooks and policies work, see [docs/HOOKS_AND_POLICIES.md](./HOOKS_AND_POLICIES.md).

#### Running the Example

Run the agent using poetry:

```bash
cd python/examples/langchain
poetry run python policy_tool_calling_agent.py
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

## Hooks and Policies

For a deep dive into how hooks and policies work, and how they can enforce security, compliance, and other business rules, see [docs/HOOKS_AND_POLICIES.md](./HOOKS_AND_POLICIES.md).

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
