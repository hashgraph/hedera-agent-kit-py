# 🧠 Hedera Agent Kit (Python)

**Python ≥3.10**
**License:** Apache 2.0

---

This is the **Python edition** of the [Hedera Agent Kit for TypeScript/JavaScript](https://github.com/hedera-dev/hedera-agent-kit).

It will provide a flexible and extensible framework for building **AI-powered Hedera agents**.

Planned features include:

* 🔌 **Third-party plugin support**
* 🧠 **Integration with LangChain**, **MCP**, and other AI frameworks
* 🪙 **Tools for interacting with Hedera services**, including:

  * Token creation and management
  * Smart contract execution
  * Account operations
  * Topic (HCS) creation and messaging

---

## Getting Started

[Install Poetry](https://python-poetry.org/docs/#installation) and run the following commands:

```bash
git clone https://github.com/hashgraph/hedera-agent-kit-py
cd hedera-agent-kit-py
poetry install
poetry run python -m hedera_agent_kit.examples.langchain.plugin_tool_calling_agent
```

> Those steps are just a placeholder. The tool calling agent is not yet implemented.

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

