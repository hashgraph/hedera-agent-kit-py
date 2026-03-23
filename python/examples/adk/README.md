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

### Standard Plugin Agent

```bash
poetry run python plugin_tool_calling_agent.py
```

### Return Bytes Mode Agent (Human-in-the-loop)

This agent demonstrates "Return Bytes" mode, where the agent returns raw transaction bytes for the user to sign and execute manually, enabling human-in-the-loop transaction control.

```bash
poetry run python return_bytes_tool_calling_agent.py
```

### Audit Hook Agent

This agent demonstrates "Hooks" by logging actions using HcsAuditTrailHook.
> **Note**: You must create an HCS topic before running this agent. You can create one easily using the [Hedera Portal Playground](https://portal.hedera.com/playground) and then set it as the `hcs_topic_id` in the code.

```bash
poetry run python audit_hook_agent.py
```

### Policy Tool Calling Agent

This agent demonstrates "Policies" by applying `MaxRecipientsPolicy` on the base set of token and account tools it operates on.

```bash
poetry run python policy_tool_calling_agent.py
```

## Example Interactions

Once running, you can interact with the agent:

```
You: What's my HBAR balance?
You: Create a new topic with memo "My Updates"
You: Transfer 1 HBAR to account 0.0.12345
You: Create a fungible token called "TestToken" with symbol "TTK"
You: exit
```

## Available Plugins

This example loads all available plugins. For more information about the available plugins, see the [plugins](https://github.com/hashgraph/hedera-agent-kit-js/blob/main/docs/PLUGINS.md) directory.
