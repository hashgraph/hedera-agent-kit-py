# Available Tools

The Hedera Agent Kit provides a comprehensive set of tools organized into **plugins** by the type of Hedera service they
interact with. These tools can be used by an AI agent, like the ones in the `python/examples` folder, and enable a user
to interact with Hedera services using natural language.

Want additional Hedera
tools? [Open an issue](https://github.com/hashgraph/hedera-agent-kit-py/issues/new?template=toolkit_feature_request.yml&labels=feature-request).

## Plugin Architecture

The tools are organized into plugins, each containing related functionality:

* **Core Account Plugin**: Tools for Hedera Account Service operations
* **Core Account Query Plugin**: Tools for querying Hedera Account Service related data
* **Core Consensus Plugin**: Tools for Hedera Consensus Service (HCS) operations
* **Core Consensus Query Plugin**: Tools for querying Hedera Consensus Service (HCS) related data
* **Core Token Plugin**: Tools for Hedera Token Service (HTS) operations
* **Core Token Query Plugin**: Tools for querying Hedera Token Service related data
* **Core EVM Plugin**: Tools for interacting with EVM smart contracts on Hedera (ERC-20 and ERC-721)
* **Core Misc Query Plugin**: Tools for fetching miscellaneous information from Hedera Mirror Node
* **Core Transaction Query Plugin**: Tools for handling Hedera transaction–related queries

See [an example of how to use plugins](../python/examples/langchain-classic/plugin_tool_calling_agent.py) as well as how
they can be used to build with [LangChain v1](../python/examples/langchain/plugin_tool_calling_agent.py)
or [LangChain Classic](../python/examples/langchain-classic/plugin_tool_calling_agent.py).

Plugins can be found in [python/hedera_agent_kit/plugins](../python/hedera_agent_kit/plugins)

---

## Plugins and Available Tools

### Core Account Plugin Tools (`core_account_plugin`)

This plugin provides tools for Hedera **Account Service operations**:

| Tool Name                                                                                         | Description                        | Details                                                                              |
|---------------------------------------------------------------------------------------------------|------------------------------------|--------------------------------------------------------------------------------------|
| [`TRANSFER_HBAR_TOOL`](./HEDERATOOLS.md#transfer_hbar_tool)                                       | Transfer HBAR between accounts     | [View Parameters & Examples](./HEDERATOOLS.md#transfer_hbar_tool)                    |
| [`APPROVE_HBAR_ALLOWANCE_TOOL`](./HEDERATOOLS.md#approve_hbar_allowance_tool)                     | Approve an HBAR spending allowance | [View Parameters & Examples](./HEDERATOOLS.md#approve_hbar_allowance_tool)           |
| [`DELETE_HBAR_ALLOWANCE_TOOL`](./HEDERATOOLS.md#delete_hbar_allowance_tool)                       | Delete an HBAR allowance           | [View Parameters & Examples](./HEDERATOOLS.md#delete_hbar_allowance_tool)            |
| [`TRANSFER_HBAR_WITH_ALLOWANCE_TOOL`](./HEDERATOOLS.md#transfer_hbar_with_allowance_tool)         | Transfer HBAR using an allowance   | [View Parameters & Examples](./HEDERATOOLS.md#transfer_hbar_with_allowance_tool)     |
| [`CREATE_ACCOUNT_TOOL`](./HEDERATOOLS.md#create_account_tool)                                     | Create a new Hedera account        | [View Parameters & Examples](./HEDERATOOLS.md#create_account_tool)                   |
| [`UPDATE_ACCOUNT_TOOL`](./HEDERATOOLS.md#update_account_tool)                                     | Update an account's metadata       | [View Parameters & Examples](./HEDERATOOLS.md#update_account_tool)                   |
| [`DELETE_ACCOUNT_TOOL`](./HEDERATOOLS.md#delete_account_tool)                                     | Delete an account                  | [View Parameters & Examples](./HEDERATOOLS.md#delete_account_tool)                   |
| [`SCHEDULE_DELETE_TOOL`](./HEDERATOOLS.md#schedule_delete_tool)                                   | Delete a scheduled transaction     | [View Parameters & Examples](./HEDERATOOLS.md#schedule_delete_tool)                  |
| [`APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL`](./HEDERATOOLS.md#approve_fungible_token_allowance_tool) | Approve token spending allowances  | [View Parameters & Examples](./HEDERATOOLS.md#approve_fungible_token_allowance_tool) |
| [`APPROVE_NFT_ALLOWANCE_TOOL`](./HEDERATOOLS.md#approve_nft_allowance_tool)                       | Approve NFT allowances             | [View Parameters & Examples](./HEDERATOOLS.md#approve_nft_allowance_tool)            |

---

### Core Account Query Plugin Tools (`core_account_query_plugin`)

This plugin provides tools for fetching **Account Service (HAS)** related information from Hedera Mirror Node.

| Tool Name                                                                                         | Description                               | Details                                                                              |
|---------------------------------------------------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------------------|
| [`GET_ACCOUNT_QUERY_TOOL`](./HEDERATOOLS.md#get_account_query_tool)                               | Returns comprehensive account information | [View Parameters & Examples](./HEDERATOOLS.md#get_account_query_tool)                |
| [`GET_HBAR_BALANCE_QUERY_TOOL`](./HEDERATOOLS.md#get_hbar_balance_query_tool)                     | Returns the HBAR balance for an account   | [View Parameters & Examples](./HEDERATOOLS.md#get_hbar_balance_query_tool)           |
| [`GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL`](./HEDERATOOLS.md#get_account_token_balances_query_tool) | Returns token balances for an account     | [View Parameters & Examples](./HEDERATOOLS.md#get_account_token_balances_query_tool) |

---

### Core Consensus Plugin Tools (`core_consensus_plugin`)

A plugin for **Consensus Service (HCS)**, enabling creation and management of topics.

| Tool Name                                                                 | Description                 | Details                                                                  |
|---------------------------------------------------------------------------|-----------------------------|--------------------------------------------------------------------------|
| [`CREATE_TOPIC_TOOL`](./HEDERATOOLS.md#create_topic_tool)                 | Create a new HCS topic      | [View Parameters & Examples](./HEDERATOOLS.md#create_topic_tool)         |
| [`SUBMIT_TOPIC_MESSAGE_TOOL`](./HEDERATOOLS.md#submit_topic_message_tool) | Submit a message to a topic | [View Parameters & Examples](./HEDERATOOLS.md#submit_topic_message_tool) |
| [`DELETE_TOPIC_TOOL`](./HEDERATOOLS.md#delete_topic_tool)                 | Delete a topic              | [View Parameters & Examples](./HEDERATOOLS.md#delete_topic_tool)         |
| [`UPDATE_TOPIC_TOOL`](./HEDERATOOLS.md#update_topic_tool)                 | Update a topic              | [View Parameters & Examples](./HEDERATOOLS.md#update_topic_tool)         |

---

### Core Consensus Query Plugin Tools (`core_consensus_query_plugin`)

This plugin provides tools for fetching **Consensus Service (HCS)** related information from Hedera Mirror Node.

| Tool Name                                                                 | Description                          | Details                                                                  |
|---------------------------------------------------------------------------|--------------------------------------|--------------------------------------------------------------------------|
| [`GET_TOPIC_INFO_QUERY_TOOL`](./HEDERATOOLS.md#get_topic_info_query_tool) | Returns information for an HCS topic | [View Parameters & Examples](./HEDERATOOLS.md#get_topic_info_query_tool) |

---

### Core Token Plugin Tools (`core_token_plugin`)

A plugin for the Hedera **Token Service (HTS)**, enabling creation and management of fungible and non-fungible tokens.

| Tool Name                                                                                                     | Description                            | Details                                                                                    |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------|--------------------------------------------------------------------------------------------|
| [`CREATE_FUNGIBLE_TOKEN_TOOL`](./HEDERATOOLS.md#create_fungible_token_tool)                                   | Creates a fungible token on Hedera     | [View Parameters & Examples](./HEDERATOOLS.md#create_fungible_token_tool)                  |
| [`CREATE_NON_FUNGIBLE_TOKEN_TOOL`](./HEDERATOOLS.md#create_non_fungible_token_tool)                           | Creates an NFT on Hedera               | [View Parameters & Examples](./HEDERATOOLS.md#create_non_fungible_token_tool)              |
| [`ASSOCIATE_TOKEN_TOOL`](./HEDERATOOLS.md#associate_token_tool)                                               | Associates tokens with an account      | [View Parameters & Examples](./HEDERATOOLS.md#associate_token_tool)                        |
| [`DISSOCIATE_TOKEN_TOOL`](./HEDERATOOLS.md#dissociate_token_tool)                                             | Dissociates tokens from an account     | [View Parameters & Examples](./HEDERATOOLS.md#dissociate_token_tool)                       |
| [`MINT_FUNGIBLE_TOKEN_TOOL`](./HEDERATOOLS.md#mint_fungible_token_tool)                                       | Mints additional fungible token supply | [View Parameters & Examples](./HEDERATOOLS.md#mint_fungible_token_tool)                    |
| [`MINT_NON_FUNGIBLE_TOKEN_TOOL`](./HEDERATOOLS.md#mint_non_fungible_token_tool)                               | Mints NFTs with metadata               | [View Parameters & Examples](./HEDERATOOLS.md#mint_non_fungible_token_tool)                |
| [`AIRDROP_FUNGIBLE_TOKEN_TOOL`](./HEDERATOOLS.md#airdrop_fungible_token_tool)                                 | Airdrops tokens to recipients          | [View Parameters & Examples](./HEDERATOOLS.md#airdrop_fungible_token_tool)                 |
| [`TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL`](./HEDERATOOLS.md#transfer_fungible_token_with_allowance_tool) | Transfer tokens using allowance        | [View Parameters & Examples](./HEDERATOOLS.md#transfer_fungible_token_with_allowance_tool) |
| [`TRANSFER_NFT_WITH_ALLOWANCE_TOOL`](./HEDERATOOLS.md#transfer_nft_with_allowance_tool)                       | Transfer NFTs using allowance          | [View Parameters & Examples](./HEDERATOOLS.md#transfer_nft_with_allowance_tool)            |
| [`DELETE_TOKEN_ALLOWANCE_TOOL`](./HEDERATOOLS.md#delete_token_allowance_tool)                                 | Delete token allowances                | [View Parameters & Examples](./HEDERATOOLS.md#delete_token_allowance_tool)                 |
| [`UPDATE_TOKEN_TOOL`](./HEDERATOOLS.md#update_token_tool)                                                     | Update token properties                | [View Parameters & Examples](./HEDERATOOLS.md#update_token_tool)                           |

---

### Core Token Query Plugin Tools (`core_token_query_plugin`)

This plugin provides tools for fetching **Token Service (HTS)** related information from Hedera Mirror Node.

| Tool Name                                                                           | Description              | Details                                                                       |
|-------------------------------------------------------------------------------------|--------------------------|-------------------------------------------------------------------------------|
| [`GET_TOKEN_INFO_QUERY_TOOL`](./HEDERATOOLS.md#get_token_info_query_tool)           | Returns token details    | [View Parameters & Examples](./HEDERATOOLS.md#get_token_info_query_tool)      |
| [`GET_PENDING_AIRDROP_QUERY_TOOL`](./HEDERATOOLS.md#get_pending_airdrop_query_tool) | Returns pending airdrops | [View Parameters & Examples](./HEDERATOOLS.md#get_pending_airdrop_query_tool) |

---

### Core EVM Plugin Tools (`core_evm_plugin`)

This plugin provides tools for interacting with EVM smart contracts on Hedera, including creating and managing ERC-20
and ERC-721 tokens via on-chain factory contracts.

| Tool Name                                                       | Description             | Details                                                             |
|-----------------------------------------------------------------|-------------------------|---------------------------------------------------------------------|
| [`CREATE_ERC20_TOOL`](./HEDERATOOLS.md#create_erc20_tool)       | Deploy an ERC-20 token  | [View Parameters & Examples](./HEDERATOOLS.md#create_erc20_tool)    |
| [`TRANSFER_ERC20_TOOL`](./HEDERATOOLS.md#transfer_erc20_tool)   | Transfer ERC-20 tokens  | [View Parameters & Examples](./HEDERATOOLS.md#transfer_erc20_tool)  |
| [`CREATE_ERC721_TOOL`](./HEDERATOOLS.md#create_erc721_tool)     | Deploy an ERC-721 NFT   | [View Parameters & Examples](./HEDERATOOLS.md#create_erc721_tool)   |
| [`TRANSFER_ERC721_TOOL`](./HEDERATOOLS.md#transfer_erc721_tool) | Transfer an ERC-721 NFT | [View Parameters & Examples](./HEDERATOOLS.md#transfer_erc721_tool) |

---

### Core EVM Query Plugin Tools (`core_evm_query_plugin`)

This plugin provides tools for querying EVM-related data on Hedera via the Mirror Node.

| Tool Name | Description | Details |
|-----------|-------------|---------|
| [`GET_CONTRACT_INFO_QUERY_TOOL`](./HEDERATOOLS.md#get_contract_info_query_tool) | Returns contract information | [View Parameters & Examples](./HEDERATOOLS.md#get_contract_info_query_tool) |

---

### Core Transaction Query Plugin Tools (`core_transaction_query_plugin`)

Tools for **transaction-related queries** on Hedera.

| Tool Name                                                                                 | Description                 | Details                                                                          |
|-------------------------------------------------------------------------------------------|-----------------------------|----------------------------------------------------------------------------------|
| [`GET_TRANSACTION_RECORD_QUERY_TOOL`](./HEDERATOOLS.md#get_transaction_record_query_tool) | Returns transaction details | [View Parameters & Examples](./HEDERATOOLS.md#get_transaction_record_query_tool) |

---

### Core Misc Query Plugin Tools (`core_misc_query_plugin`)

This plugin provides tools for fetching miscellaneous information from the Hedera Mirror Node.

| Tool Name                                                           | Description                | Details                                                               |
|---------------------------------------------------------------------|----------------------------|-----------------------------------------------------------------------|
| [`GET_EXCHANGE_RATE_TOOL`](./HEDERATOOLS.md#get_exchange_rate_tool) | Returns HBAR exchange rate | [View Parameters & Examples](./HEDERATOOLS.md#get_exchange_rate_tool) |

---

## Using Hedera Plugins in Python

Take a look at the
example [plugin_tool_calling_agent.py](../python/examples/langchain-classic/plugin_tool_calling_agent.py) for a complete
example of how to use the Hedera plugins.

First, import the core plugins and any specific tool names you need:

```python
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_account_plugin_tool_names,
    core_consensus_plugin,
    core_consensus_plugin_tool_names,
    core_token_plugin,
    core_token_plugin_tool_names,
    core_evm_plugin,
    core_evm_plugin_tool_names,
    core_account_query_plugin,
    core_consensus_query_plugin,
    core_token_query_plugin,
    core_misc_query_plugin,
    core_transaction_query_plugin,
)
from hedera_agent_kit.shared.configuration import AgentMode, Context, Configuration
```

You can pick and choose which tools from a plugin you want to enable:

```
CREATE_FUNGIBLE_TOKEN_TOOL = core_token_plugin_tool_names["CREATE_FUNGIBLE_TOKEN_TOOL"]
TRANSFER_HBAR_TOOL = core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
CREATE_TOPIC_TOOL = core_consensus_plugin_tool_names["CREATE_TOPIC_TOOL"]
GET_HBAR_BALANCE_QUERY_TOOL = core_account_query_plugin_tool_names["GET_HBAR_BALANCE_QUERY_TOOL"]
```

Then instantiate the HederaLangchainToolkit with your configuration:

```
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit

configuration = Configuration(
    tools=[
        CREATE_FUNGIBLE_TOKEN_TOOL,
        TRANSFER_HBAR_TOOL,
        CREATE_TOPIC_TOOL,
        GET_HBAR_BALANCE_QUERY_TOOL,
        # etc.
    ],  # use an empty array if you want to load all tools from plugins
    context=Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(operator_id),
    ),
    plugins=[
        core_account_plugin,
        core_account_query_plugin,
        core_consensus_plugin,
        core_consensus_query_plugin,
        core_token_plugin,
        core_token_query_plugin,
        core_evm_plugin,
        core_misc_query_plugin,
        core_transaction_query_plugin,
    ],
)

hedera_toolkit = HederaLangchainToolkit(
    client=client,
    configuration=configuration,
)

# Get the tools for use with LangChain
tools = hedera_toolkit.get_tools()
```

---

## Agent Modes

The Python SDK currently supports one agent mode:

| Mode                   | Description                                                     |
|------------------------|-----------------------------------------------------------------|
| `AgentMode.AUTONOMOUS` | The agent executes transactions directly on the Hedera network. |

> **Coming Soon:** `AgentMode.RETURN_BYTES` - In this mode, the agent creates the transaction and returns the bytes for
> the user to execute in another tool (human-in-the-loop pattern).