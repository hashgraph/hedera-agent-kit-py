# Hedera Tools - Detailed Reference

This document provides detailed parameter specifications and example prompts for all tools in the Hedera Agent Kit.

For a high-level overview of available plugins, see [HEDERAPLUGINS.md](./HEDERAPLUGINS.md).

---

## Table of Contents

- [Account Tools](#account-tools)
  - [TRANSFER_HBAR_TOOL](#transfer_hbar_tool)
  - [CREATE_ACCOUNT_TOOL](#create_account_tool)
  - [UPDATE_ACCOUNT_TOOL](#update_account_tool)
  - [DELETE_ACCOUNT_TOOL](#delete_account_tool)
  - [APPROVE_HBAR_ALLOWANCE_TOOL](#approve_hbar_allowance_tool)
  - [DELETE_HBAR_ALLOWANCE_TOOL](#delete_hbar_allowance_tool)
  - [TRANSFER_HBAR_WITH_ALLOWANCE_TOOL](#transfer_hbar_with_allowance_tool)
  - [APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL](#approve_fungible_token_allowance_tool)
  - [APPROVE_NFT_ALLOWANCE_TOOL](#approve_nft_allowance_tool)
  - [SCHEDULE_DELETE_TOOL](#schedule_delete_tool)
  - [SIGN_SCHEDULE_TRANSACTION_TOOL](#sign_schedule_transaction_tool)
- [Account Query Tools](#account-query-tools)
  - [GET_HBAR_BALANCE_QUERY_TOOL](#get_hbar_balance_query_tool)
  - [GET_ACCOUNT_QUERY_TOOL](#get_account_query_tool)
  - [GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL](#get_account_token_balances_query_tool)
- [Consensus Tools](#consensus-tools)
  - [CREATE_TOPIC_TOOL](#create_topic_tool)
  - [SUBMIT_TOPIC_MESSAGE_TOOL](#submit_topic_message_tool)
  - [DELETE_TOPIC_TOOL](#delete_topic_tool)
  - [UPDATE_TOPIC_TOOL](#update_topic_tool)
- [Consensus Query Tools](#consensus-query-tools)
  - [GET_TOPIC_INFO_QUERY_TOOL](#get_topic_info_query_tool)
- [Token Tools](#token-tools)
  - [CREATE_FUNGIBLE_TOKEN_TOOL](#create_fungible_token_tool)
  - [CREATE_NON_FUNGIBLE_TOKEN_TOOL](#create_non_fungible_token_tool)
  - [MINT_FUNGIBLE_TOKEN_TOOL](#mint_fungible_token_tool)
  - [MINT_NON_FUNGIBLE_TOKEN_TOOL](#mint_non_fungible_token_tool)
  - [ASSOCIATE_TOKEN_TOOL](#associate_token_tool)
  - [DISSOCIATE_TOKEN_TOOL](#dissociate_token_tool)
  - [AIRDROP_FUNGIBLE_TOKEN_TOOL](#airdrop_fungible_token_tool)
  - [TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL](#transfer_fungible_token_with_allowance_tool)
  - [TRANSFER_NFT_WITH_ALLOWANCE_TOOL](#transfer_nft_with_allowance_tool)
  - [DELETE_TOKEN_ALLOWANCE_TOOL](#delete_token_allowance_tool)
  - [TRANSFER_NON_FUNGIBLE_TOKEN_TOOL](#transfer_non_fungible_token_tool)
- [Token Query Tools](#token-query-tools)
  - [GET_TOKEN_INFO_QUERY_TOOL](#get_token_info_query_tool)
  - [GET_PENDING_AIRDROP_QUERY_TOOL](#get_pending_airdrop_query_tool)
- [EVM Tools](#evm-tools)
  - [CREATE_ERC20_TOOL](#create_erc20_tool)
  - [TRANSFER_ERC20_TOOL](#transfer_erc20_tool)
  - [CREATE_ERC721_TOOL](#create_erc721_tool)
  - [MINT_ERC721_TOOL](#mint_erc721_tool)
  - [TRANSFER_ERC721_TOOL](#transfer_erc721_tool)
- [EVM Query Tools](#evm-query-tools)
  - [GET_CONTRACT_INFO_QUERY_TOOL](#get_contract_info_query_tool)
- [Transaction Query Tools](#transaction-query-tools)
  - [GET_TRANSACTION_RECORD_QUERY_TOOL](#get_transaction_record_query_tool)
- [Misc Query Tools](#misc-query-tools)
  - [GET_EXCHANGE_RATE_TOOL](#get_exchange_rate_tool)

---

## Account Tools

### TRANSFER_HBAR_TOOL

Transfer HBAR between accounts.

#### Parameters

| Parameter           | Type         | Required | Description                                                                             |
|---------------------|--------------|----------|-----------------------------------------------------------------------------------------|
| `transfers`         | `List[dict]` | ✅        | Array of transfers. Each transfer has `account_id` (str) and `amount` (float, in HBAR). |
| `source_account_id` | `str`        | ❌        | Account ID of the HBAR owner (defaults to operator).                                    |
| `transaction_memo`  | `str`        | ❌        | Memo to include with the transaction.                                                   |

#### Example Prompts

```
Transfer 0.1 HBAR to 0.0.12345
Transfer 0.05 HBAR to 0.0.12345 with memo "Payment for services"
Can you move 0.05 HBARs to account with ID 0.0.12345?
```

---

### CREATE_ACCOUNT_TOOL

Creates a new Hedera account.

#### Parameters

| Parameter                          | Type    | Required | Default      | Description                                          |
|------------------------------------|---------|----------|--------------|------------------------------------------------------|
| `public_key`                       | `str`   | ❌        | operator key | Account public key.                                  |
| `account_memo`                     | `str`   | ❌        | `None`       | Memo for the account (max 100 chars).                |
| `initial_balance`                  | `float` | ❌        | `0`          | Initial HBAR balance.                                |
| `max_automatic_token_associations` | `int`   | ❌        | `-1`         | Max automatic token associations (-1 for unlimited). |

#### Example Prompts

```
Create a new Hedera account
Create a new account with 10 HBAR
Create an account with memo "My primary account" and 5 HBAR initial balance
```

---

### UPDATE_ACCOUNT_TOOL

Update an account's metadata.

#### Parameters

| Parameter                          | Type   | Required | Description                                  |
|------------------------------------|--------|----------|----------------------------------------------|
| `account_id`                       | `str`  | ❌        | Account ID to update (defaults to operator). |
| `max_automatic_token_associations` | `int`  | ❌        | Max automatic token associations.            |
| `staked_account_id`                | `str`  | ❌        | Account to stake to.                         |
| `account_memo`                     | `str`  | ❌        | New account memo.                            |
| `decline_staking_reward`           | `bool` | ❌        | Whether to decline staking rewards.          |

#### Example Prompts

```
Update account 0.0.12345 to have max auto associations of 10
Set my account memo to "Updated account"
```

---

### DELETE_ACCOUNT_TOOL

Delete an account and transfer its assets.

#### Parameters

| Parameter             | Type  | Required | Description                                                    |
|-----------------------|-------|----------|----------------------------------------------------------------|
| `account_id`          | `str` | ✅        | The account ID to delete.                                      |
| `transfer_account_id` | `str` | ❌        | Account to transfer remaining funds to (defaults to operator). |

#### Example Prompts

```
Delete account 0.0.12345
Delete account 0.0.12345 and transfer funds to 0.0.67890
```

---

### APPROVE_HBAR_ALLOWANCE_TOOL

Approve an HBAR spending allowance for a spender account.

#### Parameters

| Parameter            | Type    | Required | Description                              |
|----------------------|---------|----------|------------------------------------------|
| `owner_account_id`   | `str`   | ❌        | Owner account ID (defaults to operator). |
| `spender_account_id` | `str`   | ✅        | Spender account ID.                      |
| `amount`             | `float` | ✅        | Amount of HBAR to approve (must be ≥ 0). |
| `transaction_memo`   | `str`   | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Approve 5 HBAR allowance for account 0.0.12345
Allow account 0.0.12345 to spend up to 10 HBAR from my account
```

---

### DELETE_HBAR_ALLOWANCE_TOOL

Delete an HBAR allowance from an owner to a spender.

#### Parameters

| Parameter            | Type  | Required | Description                              |
|----------------------|-------|----------|------------------------------------------|
| `owner_account_id`   | `str` | ❌        | Owner account ID (defaults to operator). |
| `spender_account_id` | `str` | ✅        | Spender account ID.                      |
| `transaction_memo`   | `str` | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Delete HBAR allowance for spender 0.0.12345
Remove the HBAR spending permission for account 0.0.12345
```

---

### TRANSFER_HBAR_WITH_ALLOWANCE_TOOL

Transfer HBAR using an existing allowance.

#### Parameters

| Parameter           | Type         | Required | Description                                                           |
|---------------------|--------------|----------|-----------------------------------------------------------------------|
| `transfers`         | `List[dict]` | ✅        | Array of transfers. Each has `account_id` (str) and `amount` (float). |
| `source_account_id` | `str`        | ✅        | Account ID of the allowance granter.                                  |
| `transaction_memo`  | `str`        | ❌        | Memo for the transaction.                                             |

#### Example Prompts

```
Transfer 2 HBAR from 0.0.12345 to 0.0.67890 using allowance
Use my allowance to send 1 HBAR from 0.0.12345 to 0.0.67890
```

---

### APPROVE_FUNGIBLE_TOKEN_ALLOWANCE_TOOL

Approve fungible token spending allowances.

#### Parameters

| Parameter            | Type         | Required | Description                              |
|----------------------|--------------|----------|------------------------------------------|
| `owner_account_id`   | `str`        | ❌        | Owner account ID (defaults to operator). |
| `spender_account_id` | `str`        | ✅        | Spender account ID.                      |
| `token_approvals`    | `List[dict]` | ✅        | List of `{token_id, amount}` objects.    |
| `transaction_memo`   | `str`        | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Approve 100 tokens of 0.0.12345 for spender 0.0.67890
Allow account 0.0.67890 to spend 50 tokens of token 0.0.12345
```

---

### APPROVE_NFT_ALLOWANCE_TOOL

Approve an NFT allowance for specific serials or all serials.

#### Parameters

| Parameter            | Type        | Required | Description                              |
|----------------------|-------------|----------|------------------------------------------|
| `owner_account_id`   | `str`       | ❌        | Owner account ID (defaults to operator). |
| `spender_account_id` | `str`       | ✅        | Spender account ID.                      |
| `token_id`           | `str`       | ✅        | NFT token ID.                            |
| `all_serials`        | `bool`      | ❌        | Approve all serials (default: `False`).  |
| `serial_numbers`     | `List[int]` | ❌        | Specific serial numbers to approve.      |
| `transaction_memo`   | `str`       | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Approve NFT 0.0.12345 serial 1 for spender 0.0.67890
Allow account 0.0.67890 to transfer all my NFTs from collection 0.0.12345
```

---

### SCHEDULE_DELETE_TOOL

Delete a scheduled transaction.

#### Parameters

| Parameter     | Type  | Required | Description                                             |
|---------------|-------|----------|---------------------------------------------------------|
| `schedule_id` | `str` | ✅        | The schedule ID of the scheduled transaction to delete. |

#### Example Prompts

```
Delete scheduled transaction 0.0.12345
Cancel schedule 0.0.12345
```

---

### SIGN_SCHEDULE_TRANSACTION_TOOL

Sign a scheduled transaction to add your signature to an existing schedule.

#### Parameters

| Parameter     | Type  | Required | Description                                           |
|---------------|-------|----------|-------------------------------------------------------|
| `schedule_id` | `str` | ✅        | The schedule ID of the scheduled transaction to sign. |

#### Example Prompts

```
Sign scheduled transaction 0.0.12345
Add my signature to schedule 0.0.12345
```

---

## Account Query Tools

### GET_HBAR_BALANCE_QUERY_TOOL

Get the HBAR balance of an account.

#### Parameters

| Parameter    | Type  | Required | Description                                 |
|--------------|-------|----------|---------------------------------------------|
| `account_id` | `str` | ❌        | Account ID to query (defaults to operator). |

#### Example Prompts

```
What is the HBAR balance of 0.0.12345?
Check my HBAR balance
How much HBAR does account 0.0.12345 have?
```

---

### GET_ACCOUNT_QUERY_TOOL

Get comprehensive account information.

#### Parameters

| Parameter    | Type  | Required | Description          |
|--------------|-------|----------|----------------------|
| `account_id` | `str` | ✅        | Account ID to query. |

#### Example Prompts

```
Get account info for 0.0.12345
Show me details about account 0.0.12345
```

---

### GET_ACCOUNT_TOKEN_BALANCES_QUERY_TOOL

Get token balances for an account.

#### Parameters

| Parameter    | Type  | Required | Description                                 |
|--------------|-------|----------|---------------------------------------------|
| `account_id` | `str` | ❌        | Account ID to query (defaults to operator). |
| `token_id`   | `str` | ❌        | Token ID to filter by.                      |

#### Example Prompts

```
What tokens does account 0.0.12345 hold?
Get token balances for 0.0.12345
Show my token balances
```

---

## Consensus Tools

### CREATE_TOPIC_TOOL

Create a new HCS topic.

#### Parameters

| Parameter          | Type   | Required | Default | Description                  |
|--------------------|--------|----------|---------|------------------------------|
| `is_submit_key`    | `bool` | ❌        | `False` | Whether to set a submit key. |
| `topic_memo`       | `str`  | ❌        | `None`  | Memo for the topic.          |
| `transaction_memo` | `str`  | ❌        | `None`  | Memo for the transaction.    |

#### Example Prompts

```
Create a new Hedera topic
Create a topic with memo "E2E test topic" and set submit key
Create a topic with memo "E2E test topic" and do not restrict submit access
```

---

### SUBMIT_TOPIC_MESSAGE_TOOL

Submit a message to an HCS topic.

#### Parameters

| Parameter          | Type  | Required | Description               |
|--------------------|-------|----------|---------------------------|
| `topic_id`         | `str` | ✅        | Topic ID to submit to.    |
| `message`          | `str` | ✅        | Message content.          |
| `transaction_memo` | `str` | ❌        | Memo for the transaction. |

#### Example Prompts

```
Submit "Hello World" to topic 0.0.12345
Post a message "Daily update" to topic 0.0.12345
```

---

### DELETE_TOPIC_TOOL

Delete an HCS topic.

#### Parameters

| Parameter  | Type  | Required | Description         |
|------------|-------|----------|---------------------|
| `topic_id` | `str` | ✅        | Topic ID to delete. |

#### Example Prompts

```
Delete topic 0.0.12345
Remove topic 0.0.12345
```

---

### UPDATE_TOPIC_TOOL

Update an HCS topic.

#### Parameters

| Parameter               | Type            | Required | Description                                                              |
|-------------------------|-----------------|----------|--------------------------------------------------------------------------|
| `topic_id`              | `str`           | ✅        | Topic ID to update.                                                      |
| `topic_memo`            | `str`           | ❌        | New topic memo.                                                          |
| `admin_key`             | `bool\|str`     | ❌        | New admin key (`True` = use operator key, or provide public key string). |
| `submit_key`            | `bool\|str`     | ❌        | New submit key.                                                          |
| `auto_renew_account_id` | `str`           | ❌        | Auto-renew account ID.                                                   |
| `auto_renew_period`     | `int`           | ❌        | Auto-renew period in seconds.                                            |
| `expiration_time`       | `str\|datetime` | ❌        | New expiration time (ISO 8601).                                          |

#### Example Prompts

```
Update topic 0.0.12345 memo to "New memo"
Set admin key on topic 0.0.12345 using my key
```

---

## Consensus Query Tools

### GET_TOPIC_INFO_QUERY_TOOL

Get information about an HCS topic.

#### Parameters

| Parameter  | Type  | Required | Description        |
|------------|-------|----------|--------------------|
| `topic_id` | `str` | ✅        | Topic ID to query. |

#### Example Prompts

```
Get info for topic 0.0.12345
What is the memo of topic 0.0.12345?
```

---

## Token Tools

### CREATE_FUNGIBLE_TOKEN_TOOL

Create a fungible token on Hedera.

#### Parameters

| Parameter             | Type   | Required | Default   | Description                     |
|-----------------------|--------|----------|-----------|---------------------------------|
| `token_name`          | `str`  | ✅        | -         | Token name.                     |
| `token_symbol`        | `str`  | ✅        | -         | Token symbol.                   |
| `initial_supply`      | `int`  | ❌        | `0`       | Initial supply (display units). |
| `supply_type`         | `int`  | ❌        | `1`       | `0` = infinite, `1` = finite.   |
| `max_supply`          | `int`  | ❌        | `1000000` | Maximum supply (display units). |
| `decimals`            | `int`  | ❌        | `0`       | Number of decimals.             |
| `treasury_account_id` | `str`  | ❌        | operator  | Treasury account.               |
| `is_supply_key`       | `bool` | ❌        | `None`    | Whether to set supply key.      |

#### Example Prompts

```
Create a fungible token named MyToken with symbol MTK
Create a fungible token GoldCoin with symbol GLD, initial supply 1000, decimals 2, finite supply with max supply 5000
Create a fungible token named MyToken with symbol MTK. Schedule the transaction instead of executing it immediately.
```

---

### CREATE_NON_FUNGIBLE_TOKEN_TOOL

Create a non-fungible token (NFT) on Hedera.

#### Parameters

| Parameter             | Type  | Required | Default           | Description                   |
|-----------------------|-------|----------|-------------------|-------------------------------|
| `token_name`          | `str` | ✅        | -                 | Token name.                   |
| `token_symbol`        | `str` | ✅        | -                 | Token symbol.                 |
| `supply_type`         | `int` | ❌        | `1`               | `0` = infinite, `1` = finite. |
| `max_supply`          | `int` | ❌        | `100` (if finite) | Maximum supply.               |
| `treasury_account_id` | `str` | ❌        | operator          | Treasury account.             |

#### Example Prompts

```
Create an NFT collection named MyNFT with symbol MNFT
Create an NFT named ArtCollection with symbol ART and max supply 1000
```

---

### MINT_FUNGIBLE_TOKEN_TOOL

Mint additional supply of a fungible token.

#### Parameters

| Parameter  | Type    | Required | Description                     |
|------------|---------|----------|---------------------------------|
| `token_id` | `str`   | ✅        | Token ID to mint.               |
| `amount`   | `float` | ✅        | Amount to mint (display units). |

#### Example Prompts

```
Mint 100 tokens of 0.0.12345
Add 500 supply to token 0.0.12345
```

---

### MINT_NON_FUNGIBLE_TOKEN_TOOL

Mint NFTs with metadata.

#### Parameters

| Parameter  | Type        | Required | Description                      |
|------------|-------------|----------|----------------------------------|
| `token_id` | `str`       | ✅        | NFT token ID.                    |
| `uris`     | `List[str]` | ✅        | Array of metadata URIs (max 10). |

#### Example Prompts

```
Mint NFT 0.0.12345 with metadata ipfs://QmTest123
Mint 3 NFTs for token 0.0.12345 with URIs ["ipfs://a", "ipfs://b", "ipfs://c"]
```

---

### ASSOCIATE_TOKEN_TOOL

Associate tokens with an account.

#### Parameters

| Parameter    | Type        | Required | Description                                  |
|--------------|-------------|----------|----------------------------------------------|
| `token_ids`  | `List[str]` | ✅        | Token IDs to associate.                      |
| `account_id` | `str`       | ❌        | Account to associate (defaults to operator). |

#### Example Prompts

```
Associate token 0.0.12345 with my account
Associate tokens 0.0.12345 and 0.0.67890 with account 0.0.11111
```

---

### DISSOCIATE_TOKEN_TOOL

Dissociate tokens from an account.

#### Parameters

| Parameter          | Type        | Required | Description                                        |
|--------------------|-------------|----------|----------------------------------------------------|
| `token_ids`        | `List[str]` | ✅        | Token IDs to dissociate.                           |
| `account_id`       | `str`       | ❌        | Account to dissociate from (defaults to operator). |
| `transaction_memo` | `str`       | ❌        | Memo for the transaction.                          |

#### Example Prompts

```
Dissociate token 0.0.12345 from my account
Remove token 0.0.12345 association from account 0.0.67890
```

---

### AIRDROP_FUNGIBLE_TOKEN_TOOL

Airdrop fungible tokens to multiple recipients.

#### Parameters

| Parameter           | Type         | Required | Description                              |
|---------------------|--------------|----------|------------------------------------------|
| `token_id`          | `str`        | ✅        | Token ID to airdrop.                     |
| `recipients`        | `List[dict]` | ✅        | Array of `{account_id, amount}` objects. |
| `source_account_id` | `str`        | ❌        | Source account (defaults to operator).   |
| `transaction_memo`  | `str`        | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Airdrop 100 tokens of 0.0.12345 to accounts 0.0.11111 and 0.0.22222
Send 50 tokens each of 0.0.12345 to three accounts
```

---

### TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL

Transfer fungible tokens using an allowance.

#### Parameters

| Parameter           | Type         | Required | Description                              |
|---------------------|--------------|----------|------------------------------------------|
| `token_id`          | `str`        | ✅        | Token ID to transfer.                    |
| `source_account_id` | `str`        | ✅        | Token owner account ID.                  |
| `transfers`         | `List[dict]` | ✅        | Array of `{account_id, amount}` objects. |
| `transaction_memo`  | `str`        | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Transfer 50 tokens of 0.0.12345 from 0.0.11111 to 0.0.22222 using allowance
Use my token allowance to send 100 tokens from 0.0.11111
```

---

### TRANSFER_NFT_WITH_ALLOWANCE_TOOL

Transfer NFTs using an allowance.

#### Parameters

| Parameter           | Type         | Required | Description                                    |
|---------------------|--------------|----------|------------------------------------------------|
| `source_account_id` | `str`        | ✅        | NFT owner account ID.                          |
| `token_id`          | `str`        | ✅        | NFT token ID.                                  |
| `recipients`        | `List[dict]` | ✅        | Array of `{recipient, serial_number}` objects. |
| `transaction_memo`  | `str`        | ❌        | Memo for the transaction.                      |

#### Example Prompts

```
Transfer NFT 0.0.12345 serial 1 from 0.0.11111 to 0.0.22222 using allowance
Use allowance to send NFT serial 5 from owner 0.0.11111
```

---

### DELETE_TOKEN_ALLOWANCE_TOOL

Delete fungible token allowances.

#### Parameters

| Parameter            | Type        | Required | Description                              |
|----------------------|-------------|----------|------------------------------------------|
| `owner_account_id`   | `str`       | ❌        | Owner account ID (defaults to operator). |
| `spender_account_id` | `str`       | ✅        | Spender account ID.                      |
| `token_ids`          | `List[str]` | ✅        | Token IDs to remove allowances for.      |
| `transaction_memo`   | `str`       | ❌        | Memo for the transaction.                |

#### Example Prompts

```
Delete token allowance for token 0.0.12345 from spender 0.0.67890
Remove all token allowances for spender 0.0.67890
```

---

### TRANSFER_NON_FUNGIBLE_TOKEN_TOOL

Transfer non-fungible tokens (NFTs). Support transferring multiple NFTs (from one collection) to multiple recipients in a single transaction.

#### Parameters

| Parameter           | Type         | Required | Description                                                             |
|---------------------|--------------|----------|-------------------------------------------------------------------------|
| `token_id`          | `str`        | ✅        | The NFT token ID to transfer (e.g., "0.0.12345").                       |
| `recipients`        | `List[dict]` | ✅        | List of objects specifying recipients and serial numbers.               |
| `source_account_id` | `str`        | ❌        | Account ID of the NFT owner (defaults to operator).                     |
| `transaction_memo`  | `str`        | ❌        | Memo for the transaction.                                               |

#### Example Prompts

```
Transfer NFT 0.0.12345 serial 1 to 0.0.67890
Send NFT 0.0.12345 serial 2 from 0.0.11111 to 0.0.22222
```

---

## Token Query Tools

### GET_TOKEN_INFO_QUERY_TOOL

Get information about a token.

#### Parameters

| Parameter  | Type  | Required | Description        |
|------------|-------|----------|--------------------|
| `token_id` | `str` | ✅        | Token ID to query. |

#### Example Prompts

```
Get info for token 0.0.12345
What is the total supply of token 0.0.12345?
```

---

### GET_PENDING_AIRDROP_QUERY_TOOL

Get pending airdrops for an account.

#### Parameters

| Parameter    | Type  | Required | Description                                 |
|--------------|-------|----------|---------------------------------------------|
| `account_id` | `str` | ❌        | Account ID to query (defaults to operator). |

#### Example Prompts

```
Show pending airdrops for account 0.0.12345
What airdrops are pending for my account?
```

---

## EVM Tools

### CREATE_ERC20_TOOL

Deploy an ERC-20 token via factory contract.

#### Parameters

| Parameter        | Type  | Required | Default | Description                  |
|------------------|-------|----------|---------|------------------------------|
| `token_name`     | `str` | ✅        | -       | Token name.                  |
| `token_symbol`   | `str` | ✅        | -       | Token symbol.                |
| `decimals`       | `int` | ❌        | `18`    | Number of decimals.          |
| `initial_supply` | `int` | ❌        | `0`     | Initial supply (base units). |

#### Example Prompts

```
Create an ERC20 token named MyERC20 with symbol M20
Create an ERC20 token GoldToken with symbol GLD, decimals 2, initial supply 1000
Create an ERC20 token named "MyToken" with symbol MTK. Schedule this transaction instead of executing it immediately.
```

---

### TRANSFER_ERC20_TOOL

Transfer ERC-20 tokens.

#### Parameters

| Parameter           | Type  | Required | Description                                                                                                      |
|---------------------|-------|----------|------------------------------------------------------------------------------------------------------------------|
| `contract_id`       | `str` | ✅        | ERC-20 contract ID (EVM address or Hedera ID).                                                                   |
| `recipient_address` | `str` | ✅        | Recipient address (EVM or Hedera ID).                                                                            |
| `amount`            | `int` | ✅        | Amount to transfer in **base units** (smallest denomination, e.g., for 18 decimals: 1 token = 10^18 base units). |

> [!IMPORTANT]
> The `amount` parameter accepts values in **base units** (the smallest token denomination), not display units. For example, if the token has 18 decimals and you want to transfer 1 token, you must pass `1000000000000000000` (10^18).

#### Example Prompts

```
Transfer 100 tokens of contract 0.0.12345 to 0.0.67890
Send 50 ERC20 tokens from 0x1234... to 0x5678...
```

---

### CREATE_ERC721_TOOL

Deploy an ERC-721 (NFT) token via factory contract.

#### Parameters

| Parameter      | Type  | Required | Default | Description                  |
|----------------|-------|----------|---------|------------------------------|
| `token_name`   | `str` | ✅        | -       | Token name.                  |
| `token_symbol` | `str` | ✅        | -       | Token symbol.                |
| `base_uri`     | `str` | ❌        | `""`    | Base URI for token metadata. |

#### Example Prompts

```
Create an ERC721 token named MyNFT with symbol MNFT
Create an ERC721 collection called ArtDrops with symbol AD and base URI ipfs://Qm...
```

---

### MINT_ERC721_TOOL

Mint a new ERC-721 NFT by calling the `safeMint(to)` function on the contract.

#### Parameters

| Parameter     | Type  | Required | Default  | Description                                                |
|---------------|-------|----------|----------|------------------------------------------------------------|
| `contract_id` | `str` | ✅        | -        | The ID of the ERC-721 contract (EVM address or Hedera ID). |
| `to_address`  | `str` | ❌        | operator | Address to which the token will be minted.                 |

#### Example Prompts

```
Mint ERC721 token 0.0.6486793 to 0xd94dc7f82f103757f715514e4a37186be6e4580b
Mint ERC721 token 0.0.6486793 to Hedera account ID 0.0.2222222
Mint ERC721 token 0.0.9999
```

---

### TRANSFER_ERC721_TOOL

Transfer an ERC-721 NFT.

#### Parameters

| Parameter      | Type  | Required | Description                                                           |
|----------------|-------|----------|-----------------------------------------------------------------------|
| `contract_id`  | `str` | ✅        | ERC-721 contract ID (EVM address or Hedera ID).                       |
| `from_address` | `str` | ❌        | Sender address (defaults to operator).                                |
| `to_address`   | `str` | ✅        | Recipient address (EVM or Hedera ID).                                 |
| `token_id`     | `int` | ✅        | The ID of the specific NFT within the ERC-721 collection to transfer. |

> [!NOTE]
> In ERC-721 collections, token IDs typically start from **0** (or 1, depending on the contract implementation). The first minted NFT is usually token ID 0.

#### Example Prompts

```
Transfer ERC721 token 0 from contract 0.0.12345 to 0.0.67890
Send NFT #5 from 0x1234... to 0x5678...
```

---

## EVM Query Tools

### GET_CONTRACT_INFO_QUERY_TOOL

Get information about an EVM contract on Hedera.

#### Parameters

| Parameter     | Type  | Required | Description                              |
|---------------|-------|----------|------------------------------------------|
| `contract_id` | `str` | ✅        | The contract ID or EVM address to query. |

#### Example Prompts

```
Get contract info for 0.0.12345
What is the contract information for 0x1234...?
Show details of contract 0.0.12345
```

---

## Transaction Query Tools

### GET_TRANSACTION_RECORD_QUERY_TOOL

Get details for a transaction.

#### Parameters

| Parameter           | Type  | Required | Description              |
|---------------------|-------|----------|--------------------------|
| `transaction_id`    | `str` | ✅        | Transaction ID to query. |
| `transaction_nonce` | `int` | ❌        | Transaction nonce.       |

#### Example Prompts

```
Get transaction record for 0.0.12345@1234567890.123456789
Show details of transaction 0.0.12345@1234567890.123456789
```

---

## Misc Query Tools

### GET_EXCHANGE_RATE_TOOL

Get the HBAR exchange rate.

#### Parameters

| Parameter   | Type  | Required | Description                                                   |
|-------------|-------|----------|---------------------------------------------------------------|
| `timestamp` | `int` | ❌        | Timestamp (seconds or nanos since epoch) for historical rate. |

#### Example Prompts

```
What is the current HBAR exchange rate?
Get the HBAR to USD rate
What was the exchange rate at timestamp 1234567890?
```
