# Agent Hooks and Policies

The Hedera Agent Kit provides a flexible and powerful system for putting limits on tool usage and enforcing business logic, effectively enabling you to limit the functionality of AI agents through **Hooks** and **Policies**. These hooks and policies can be used to enforce security, compliance, and other business rules.

---

## Table of Contents

### Part 1: For Hooks and Policies Users
- [Quick Overview](#quick-overview)
- [When Hooks and Policies are Called](#when-hooks-and-policies-are-called)
- [How to Use Hooks and Policies](#how-to-use-hooks-and-policies)
- [Available Hooks and Policies](#available-hooks-and-policies)
  - [HcsAuditTrailHook](#1-hcsaudittrailhook-hook)
  - [MaxRecipientsPolicy](#2-maxrecipientspolicy-policy)
  - [RejectToolPolicy](#3-rejecttoolpolicy-policy)

### Part 2: For Policy and Hook Developers
- [Tool Lifecycle Deep Dive](#tool-lifecycle-deep-dive)
- [Hook Parameter Structures](#hook-parameter-structures)
- [Hooks vs. Policies](#hooks-vs-policies)
- [Type Safety & Multi-Tool Context](#type-safety--multi-tool-context)
- [Creating New Hooks/Policies](#creating-new-hookspolicies)
- [Adding to the Registry](#how-to-add-to-this-registry)

---

# Part 1: For Hooks and Policies Users

## Quick Overview

**Hooks** and **Policies** let you customize how tools behave:

- **Hooks**: Extensions that observe and modify tool execution (logging, tracking, etc.)
- **Policies**: Validation rules that can **block** tool execution if certain conditions aren't met

> [!NOTE]
> Only tools extending `ToolV2` (or the underlying abstract tool system) support hooks and policies.

## When Hooks and Policies are Called

Hooks can execute at 4 different points during a tool's lifecycle:

1. **Pre-Tool Execution** - Before anything happens, when parameters are passed.
2. **Post-Parameter Normalization** - After parameters are validated and cleaned.
3. **Post-Core Action** - After the main logic executes (e.g., transaction created), before tool execution when a transaction has been formed.
4. **Post-Tool Execution** - After everything completes; after tool execution when a transaction has been signed and submitted.

## How to Use Hooks and Policies

Add hooks and policies to your agent's context during initialization:

```python
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy
from hedera_agent_kit.policies.reject_tool_policy import RejectToolPolicy
from hedera_agent_kit.shared.configuration import Context

context = Context(
    account_id="0.0.1234",
    hooks=[
        HcsAuditTrailHook(['transfer_hbar'], '0.0.12345'),
        MaxRecipientsPolicy(5),
        RejectToolPolicy(['delete_account']),
    ]
)
```

## Available Hooks and Policies

### 1. `HcsAuditTrailHook` (Hook)

**Description**:
Provides an immutable audit trail by logging tool executions to a Hedera Consensus Service (HCS) topic.

> [!IMPORTANT]
> **Autonomous Mode Only**: This hook is strictly available in `AUTONOMOUS` mode. It will throw an error if used in `RETURN_BYTES` mode.

> [!WARNING]
> **HIP-991 (Paid Topics)**: If a paid topic is used, it will incur submission fees. Ensure you have sufficient funds to avoid draining the account.

**Prerequisites**:

1. **Topic Creation**: The HCS topic must be created before initializing the hook. You can do this:
   - Using the [Hedera Portal Playground](https://portal.hedera.com/playground)
   - Using the [Hedera Portal Agent Lab](https://dev.portal.hedera.com/agent-lab)
   - Using the Hedera SDK or another Hedera Agent Kit agent.
2. **Permissions**: The Hedera account associated with the agent's operator account must have permissions to submit messages to the topic.

**Parameters**:

- `relevant_tools`: `List[str]` - List of tools to audit (e.g., `['transfer_hbar', 'create_token']`).
- `hcs_topic_id`: `str` - The pre-created Hedera topic ID (e.g., `'0.0.12345'`).

**Example Usage**:

```python
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.shared.configuration import Context

audit_hook = HcsAuditTrailHook(
    relevant_tools=['transfer_hbar', 'create_token'],
    hcs_topic_id='0.0.12345'
)

context = Context(
    account_id="0.0.1234",
    hooks=[audit_hook]
)
```

---

### 2. `MaxRecipientsPolicy` (Policy)

**Description**:
A security policy that limits the number of recipients in transfer and airdrop operations. It blocks requests that exceed a defined threshold to prevent massive unauthorized transfers.

**Default Supported Tools**:
By default, the policy knows how to count recipients for tools matching the following names:
- `transfer_hbar`
- `transfer_hbar_with_allowance`
- `airdrop_fungible_token`
- `transfer_fungible_token_with_allowance`
- `transfer_nft_with_allowance`
- `transfer_non_fungible_token`

**Parameters**:

- `max_recipients`: `int` - Maximum number of recipients allowed.
- `additional_tools`: `List[str]` - (Optional) Extra tools to apply this policy to.
- `custom_strategies`: `Dict[str, Callable[[Any], int]]` - (Optional) A mapping of tool names to functions that count recipients. **If you add tools via `additional_tools`, you must provide a strategy for each one**, otherwise the policy will throw an error at runtime.

**Example with Custom Strategies**:

```python
from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy

# Basic usage with default tools only
basic_policy = MaxRecipientsPolicy(max_recipients=5)

# With custom tool - strategy is REQUIRED
extended_policy = MaxRecipientsPolicy(
    max_recipients=5,
    additional_tools=['my_custom_bulk_tool'],
    custom_strategies={
        'my_custom_bulk_tool': lambda params: len(params.get('recipients', []))
    }
)
```

> [!TIP]
> **Example Project**: See [`python/examples/langchain/policy_tool_calling_agent.py`](../python/examples/langchain/policy_tool_calling_agent.py) and [`python/examples/adk/policy_tool_calling_agent.py`](../python/examples/adk/policy_tool_calling_agent.py) for complete working examples of this policy in action.

---

### 3. `RejectToolPolicy` (Policy)

**Description**:
A restrictive policy used to explicitly disable specific tools. Even if a tool is technically available in a plugin, this policy ensures the agent cannot execute it under any circumstances.

**Parameters**:

- `relevant_tools`: `List[str]` - The list of tool methods to be blocked (e.g., `['delete_account', 'freeze_token']`).

**Example Usage**:

```python
from hedera_agent_kit.policies.reject_tool_policy import RejectToolPolicy
from hedera_agent_kit.shared.configuration import Context

safety_policy = RejectToolPolicy(['delete_account'])

context = Context(
    account_id="0.0.1234",
    hooks=[safety_policy]
)
```

---

# Part 2: For Policy and Hook Developers

## Tool Lifecycle Deep Dive

Every tool in the kit follows a standardized 7-stage lifecycle:

```text
[1. Pre-Tool Execution] --------> Hook: pre_tool_execution_hook
         |
[2. Parameter Normalization]
         |
[3. Post-Parameter Normalization] --> Hook: post_params_normalization_hook
         |
[4. Core Action]
         |
[5. Post-Core Action] --------------> Hook: post_core_action_hook
         |
[6. Secondary Action]
         |
[7. Post-Tool Execution] -----------> Hook: post_secondary_action_hook
         |
[Result Returned]
```

**Stage Details:**

1. **Pre-Tool Execution**: Before any processing begins. Use for early validation or logging.
2. **Parameter Normalization**: The tool validates and cleans user input (not hookable).
3. **Post-Parameter Normalization**: After parameters are normalized. Use for parameter-based validation.
4. **Core Action**: Primary business logic executes (e.g., creating a transaction).
5. **Post-Core Action**: After core logic completes. Use to inspect or modify the result before submission.
6. **Secondary Action**: Transaction signing/submission happens (not hookable).
7. **Post-Tool Execution**: After everything completes. Use for final logging or cleanup.

## Hook Parameter Structures

Each hook receives specialized parameter objects and the **`method`** name (str) representing the tool being executed.

| Hook Stage | Params Object Contains | Method Parameter | Use Case |
|:---|:---|:---|:---|
| `pre_tool_execution_hook` | `context`, `raw_params`, `client` | `method: str` | Early validation, logging initial state |
| `post_params_normalization_hook` | `context`, `raw_params`, `normalized_params`, `client` | `method: str` | Parameter-based policies, data enrichment |
| `post_core_action_hook` | `context`, `raw_params`, `normalized_params`, `core_action_result`, `client` | `method: str` | Inspect/modify transaction before submission |
| `post_secondary_action_hook`| `context`, `raw_params`, `normalized_params`, `core_action_result`, `tool_result`, `client`| `method: str` | Final logging, audit trails, cleanup |

> [!TIP]
> Use the `method` parameter to filter execution and safely access parameters.

---

## Hooks vs. Policies

### Hooks (`AbstractHook`)

Hooks are **non-blocking extensions** that observe and modify execution flow. They can:
- Log data
- Modify context state
- Enrich parameters
- Track metrics

They should not stop execution unless an error occurs.
**Example**: `HcsAuditTrailHook` logs execution details to an HCS topic without blocking.

### Policies (`Policy`)

Policies are specialized Hooks designed to **validate** and **block** execution. They use `should_block...` methods that return boolean values. If `True` is returned, the `Policy` base class raises a ValueError, immediately halting the tool's lifecycle.

> [!IMPORTANT]
> **Policy Implementation Rule**: When creating a custom Policy, you **should** define logic in at least one of the `should_block...` methods (e.g., `should_block_pre_tool_execution`). You **must not** override the native hook methods (e.g., `pre_tool_execution_hook`) as the `Policy` base class uses these internally to trigger the blocking logic and raise errors.

**Available `should_block...` methods:**
- `should_block_pre_tool_execution()`
- `should_block_post_params_normalization()`
- `should_block_post_core_action()`
- `should_block_post_secondary_action()`

---

## Type Safety & Multi-Tool Context

When a hook targets multiple tools, you handle the various parameter structures using one of three patterns:

### 1. Universal Logic

**Approach**: Focus on the `context` for state management or apply generic processing (like stringification) to `raw_params`.
**Example**: `HcsAuditTrailHook` logs all inputs to HCS without needing to know each tool's schema.

### 2. Conditional Logic (Type Guards)

**Approach**: Check the `method` parameter and route accordingly.

```python
async def post_params_normalization_hook(
    self, context: Context, params: PostParamsNormalizationParams, method: str
) -> Any:
    if method in ['transfer_hbar', 'transfer_hbar_with_allowance']:
        # Shared structure logic
        transfers = params.normalized_params['transfers']
        total = sum(t['amount'] for t in transfers)
        print(f"Total HBAR being transferred: {total}")
```

### 3. Strategy Pattern (Dependency Injection)

**Approach**: Accept a **Strategy Map** (Dict) during initialization that maps tool names to handling functions. (`MaxRecipientsPolicy` uses this approach via `custom_strategies`.)

---

## Creating New Hooks/Policies

### Template for New Hook

```python
from typing import Any
from hedera_agent_kit.hooks.abstract_hook import (
    AbstractHook, PreToolExecutionParams, PostParamsNormalizationParams,
    PostCoreActionParams, PostSecondaryActionParams
)
from hedera_agent_kit.shared.configuration import Context

class MyCustomHook(AbstractHook):
    @property
    def name(self) -> str:
        return 'My Custom Hook'

    @property
    def description(self) -> str:
        return 'Detailed explanation of what this hook does'

    @property
    def relevant_tools(self) -> list[str]:
        return ['create_account', 'transfer_hbar']

    async def pre_tool_execution_hook(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        # Access client from params
        client = params.client
        raw_params = params.raw_params
        # Your logic here
```

### Template for New Policy

```python
from hedera_agent_kit.shared.policy import Policy
from hedera_agent_kit.hooks.abstract_hook import PreToolExecutionParams
from hedera_agent_kit.shared.configuration import Context

class MyCustomPolicy(Policy):
    @property
    def name(self) -> str:
        return 'My Custom Policy'

    @property
    def description(self) -> str:
        return 'Detailed explanation of what this policy blocks'

    @property
    def relevant_tools(self) -> list[str]:
        return ['transfer_hbar', 'transfer_fungible_token']

    async def should_block_pre_tool_execution(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> bool:
        """Return True to BLOCK execution, False to ALLOW."""
        raw_params = params.raw_params

        # Example: block specific accounts
        # return raw_params.get('account_id') == '0.0.blocked'

        return False
```

---

## 📝 How to Add to this Registry

When adding a new Hook or Policy:

1. **Implementation**: Add the implementation file to `hedera_agent_kit/hooks` or `hedera_agent_kit/policies`.
2. **Export**: Export it in `__init__.py`.
3. **Documentation**: Add a new section in [Part 1: Available Hooks and Policies](#available-hooks-and-policies).
4. **Testing**: Add unit tests in the corresponding test directory.
5. **Update**: Ensure your `relevant_tools` are clearly defined.
