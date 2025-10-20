# Available Tools

The Hedera Agent Kit provides a comprehensive set of tools organized into **plugins** by the type of Hedera service they
interact with. These tools can be used by an AI agent, like the ones in the `typescript/examples` folder, and enable a
user to interact with Hedera services using natural language.

Want additional Hedera
tools? [Open an issue](https://github.com/hedera-dev/hedera-agent-kit-py/issues/new?template=toolkit_feature_request.yml&labels=feature-request).

## Plugin Architecture

The tools are now organized into plugins, each containing related functionality:

* **Core Account Plugin**: Tools for Hedera Account Service operations
* **Core Account Query Plugin**: Tools for querying Hedera Account Service related data
* **Core Consensus Plugin**: Tools for Hedera Consensus Service (HCS) operations
* **Core Consensus Query Plugin**: Tools for querying Hedera Consensus Service (HCS) related data
* **Core Token Plugin**: Tools for Hedera Token Service (HTS) operations
* **Core Token Query Plugin**: Tools for querying Hedera Token Service related data
* **Core EVM Plugin**: Tools for interacting with EVM smart contracts on Hedera (ERC-20 and ERC-721)
* **Core EVM Query Plugin**: Tools for querying smart contract-related data on Hedera
* **Core Transactions Plugin**: Tools for handling Hedera transaction–related operations