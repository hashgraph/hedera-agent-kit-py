# Migrating Custom Tools to BaseToolV2 (Recommended, Non-Breaking)

> [!IMPORTANT]
> **This is NOT a breaking change.** Tools that directly implement the `Tool` interface continue to work exactly as before. However, they will **not** benefit from the hooks and policies system (e.g., `HcsAuditTrailHook`, `MaxRecipientsPolicy`, `RejectToolPolicy`) introduced in the latest version. To enable those features, migrate your tool to the `BaseToolV2` abstract class, which itself implements the `Tool` interface.

## Why migrate?

- Unlock **hooks** (logging, audit trails, metrics) and **policies** (blocking rules, rate limits)
- Enforce a consistent, structured tool lifecycle across your plugin
- Benefit from built-in error handling and hook dispatching
- Improve code maintainability by separating concerns into distinct lifecycle stages

## What is `BaseToolV2`?

`BaseToolV2` is an abstract class that **implements** the `Tool` interface. This means any class extending `BaseToolV2` is a drop-in replacement everywhere a `Tool` is expected — including inside `Plugin.get_tools()`. The class enforces a 7-stage lifecycle:

```text
[1] pre_tool_execution_hook       ← hooks & policies intercept here
[2] normalize_params               ← your logic
[3] post_params_normalization_hook ← hooks & policies intercept here
[4] core_action                    ← your logic
[5] post_core_action_hook          ← hooks & policies intercept here
[6] secondary_action               ← your logic (optional, e.g. tx signing)
[7] post_tool_execution_hook       ← hooks & policies intercept here
```

Hooks and policies tap into stages 1, 3, 5, and 7 automatically — **you never call them manually**.

## Step-by-step migration

Below is a fully annotated before/after comparison using the `transfer_hbar` tool as the reference example.

### Before (Old style — direct `Tool` implementation)

```python
"""Utilities for building and executing HBAR transfer operations via the Agent Kit.

This module exposes:
- transfer_hbar_prompt: Generate a prompt/description for the transfer tool.
- transfer_hbar: Execute an HBAR transfer transaction.
- TransferHbarTool: Tool wrapper exposing the transfer operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
# ── The old approach imported the base Tool class ──────────────────────────
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


# ── Tool description / prompt ──────────────────────────────────────────────
def transfer_hbar_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the HBAR transfer tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information or scheduling capabilities.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This async tool will transfer HBAR to an account.

Parameters:
- transfers (list of dicts, required): Each dict must contain:
    - account_id (str): Recipient account ID
    - amount (float or str): Amount of HBAR to transfer
- {source_account_desc}
- transaction_memo (str, optional): Optional memo for the transfer transaction
{scheduled_desc}

{usage_instructions}
"""


# ── Post-processing helper ─────────────────────────────────────────────────
def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a transfer transaction result.

    Args:
        response: The raw response returned by the transaction execution, which
            may contain a schedule_id if the transaction was scheduled.

    Returns:
        A concise message describing the status and any relevant identifiers
        (e.g., transaction ID, schedule ID).
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled HBAR transfer created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return f"HBAR successfully transferred.\nTransaction ID: {response.transaction_id}"


# ── Standalone execute function — ALL logic lives here ─────────────────────
# This monolithic function cannot be split into hookable lifecycle stages,
# so hooks and policies have no entry points.
async def transfer_hbar(
    client: Client,
    context: Context,
    params: TransferHbarParameters,
) -> ToolResponse:
    """Execute an HBAR transfer using normalized parameters and a built transaction.

    Args:
        client: Hedera client used to execute transactions.
        context: Runtime context providing configuration and defaults.
        params: User-supplied parameters describing the transfer(s) to perform.

    Returns:
        A ToolResponse wrapping the raw transaction response and a human-friendly
        message indicating success or failure.

    Notes:
        This function captures exceptions and returns a failure ToolResponse
        rather than raising, to keep tool behavior consistent for callers.
        It accepts raw params, validates, and normalizes them before performing the transaction.
    """
    try:
        # Normalize parameters
        normalised_params: TransferHbarParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_hbar(
                params, context, client
            )
        )

        # Build transaction
        tx: Transaction = HederaBuilder.transfer_hbar(normalised_params)

        # Execute transaction and post-process result
        return await handle_transaction(tx, client, context, post_process)

    except Exception as e:
        message: str = f"Failed to transfer HBAR: {str(e)}"
        print("[transfer_hbar_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_HBAR_TOOL: str = "transfer_hbar_tool"


# ── Tool class directly implements the Tool interface ─────────────────────
# ✗ No hook/policy support — execute() is opaque to the framework
class TransferHbarTool(Tool):
    """Tool wrapper that exposes the HBAR transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = TRANSFER_HBAR_TOOL
        self.name: str = "Transfer HBAR"
        self.description: str = transfer_hbar_prompt(context)
        self.parameters: type[TransferHbarParameters] = TransferHbarParameters
        self.outputParser = transaction_tool_output_parser

    # ── All logic is in a single execute() method ─────────────────────────
    # This approach works but doesn't expose lifecycle hooks to the framework
    async def execute(
        self, client: Client, context: Context, params: TransferHbarParameters
    ) -> ToolResponse:
        """Execute the HBAR transfer using the provided client, context, and params.

        Args:
            client: Hedera client used to execute transactions.
            context: Runtime context providing configuration and defaults.
            params: Transfer parameters accepted by this tool.

        Returns:
            The result of the transfer as a ToolResponse, including a human-readable
            message and error information if applicable.
        """
        # All logic delegated to a standalone function
        return await transfer_hbar(client, context, params)
```

### After (New style — `BaseToolV2` class)

```python
"""Utilities for building and executing HBAR transfer operations via the Agent Kit.

This module exposes:
- transfer_hbar_prompt: Generate a prompt/description for the transfer tool.
- transfer_hbar: Execute an HBAR transfer transaction.
- TransferHbarTool: Tool wrapper exposing the transfer operation to the runtime.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
# ── Import BaseToolV2 instead of the raw Tool class ────────────────────────
# BaseToolV2 implements Tool, so this remains fully backward-compatible.
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from typing import Any
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator


# ── Tool description / prompt (unchanged from old style) ───────────────────
def transfer_hbar_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the HBAR transfer tool.

    Args:
        context: Optional contextual configuration that may influence the prompt,
            such as default account information or scheduling capabilities.

    Returns:
        A string describing the tool, its parameters, and usage instructions.
    """
    context_snippet: str = PromptGenerator.get_context_snippet(context)
    source_account_desc: str = PromptGenerator.get_account_parameter_description(
        "source_account_id", context
    )
    usage_instructions: str = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc: str = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This async tool will transfer HBAR to an account.

Parameters:
- transfers (list of dicts, required): Each dict must contain:
    - account_id (str): Recipient account ID
    - amount (float or str): Amount of HBAR to transfer
- {source_account_desc}
- transaction_memo (str, optional): Optional memo for the transfer transaction
{scheduled_desc}

{usage_instructions}
"""


# ── Post-processing helper (unchanged from old style) ──────────────────────
def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for a transfer transaction result.

    Args:
        response: The raw response returned by the transaction execution, which
            may contain a schedule_id if the transaction was scheduled.

    Returns:
        A concise message describing the status and any relevant identifiers
        (e.g., transaction ID, schedule ID).
    """
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled HBAR transfer created successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return f"HBAR successfully transferred.\nTransaction ID: {response.transaction_id}"


TRANSFER_HBAR_TOOL: str = "transfer_hbar_tool"


# ── Extend BaseToolV2 instead of Tool ──────────────────────────────────────
# BaseToolV2 implements Tool, so this is a drop-in replacement.
class TransferHbarTool(BaseToolV2):
    """Tool wrapper that exposes the HBAR transfer capability to the Agent runtime."""

    # ── Required fields from the Tool interface ────────────────────────────
    def __init__(self, context: Context):
        """Initialize the tool metadata and parameter specification.

        Args:
            context: Runtime context used to tailor the tool description.
        """
        self.method: str = TRANSFER_HBAR_TOOL
        self.name: str = "Transfer HBAR"
        self.description: str = transfer_hbar_prompt(context)
        self.parameters: type[TransferHbarParameters] = TransferHbarParameters
        self.outputParser = transaction_tool_output_parser
        # Note: Context-dependent fields are computed once at construction time,
        # exactly as the old style did.

    # ── Stage 2: Parameter normalization ───────────────────────────────────
    # Called by BaseToolV2.execute() between pre_tool_execution_hook and
    # post_params_normalization_hook. Return the normalized params object.
    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> TransferHbarParametersNormalised:
        """Normalize and validate input parameters.

        This method is called automatically by the BaseToolV2 lifecycle.
        Hooks registered in the context will be executed before and after this stage.
        """
        return await HederaParameterNormaliser.normalise_transfer_hbar(
            params, context, client
        )

    # ── Stage 4: Core action ───────────────────────────────────────────────
    # Build the transaction (or perform the query). Do NOT sign/submit here.
    # BaseToolV2 will call post_core_action_hook after this returns.
    async def core_action(
        self,
        normalized_params: TransferHbarParametersNormalised,
        context: Context,
        client: Client,
    ) -> Transaction:
        """Build the HBAR transfer transaction.

        This method is called automatically by the BaseToolV2 lifecycle.
        Hooks registered in the context will be executed after this stage.
        """
        return HederaBuilder.transfer_hbar(normalized_params)

    # ── Stage 6: Secondary action ──────────────────────────────────────────
    # Sign and submit the transaction (or any post-core step).
    # BaseToolV2.should_secondary_action() returns True by default; override it
    # in query-only tools to skip this stage entirely.
    async def secondary_action(
        self, transaction: Transaction, client: Client, context: Context
    ) -> ToolResponse:
        """Sign and submit the transaction.

        This method is called automatically by the BaseToolV2 lifecycle if
        should_secondary_action() returns True (default behavior for transaction tools).
        Hooks registered in the context will be executed after this stage.
        """
        return await handle_transaction(transaction, client, context, post_process)

    # ── Error handling ─────────────────────────────────────────────────────
    # Override BaseToolV2.handle_error() for tool-specific error messages.
    # If you omit this, BaseToolV2 provides a sensible default.
    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        """Handle errors that occur during any stage of the lifecycle.

        This method is called automatically when an exception is raised.
        """
        message: str = f"Failed to transfer HBAR: {str(error)}"
        print("[transfer_hbar_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )
```

## What changed – summary

| Aspect | Old style (`Tool`) | New style (`BaseToolV2`) |
|---|---|---|
| Declaration | Class extending `Tool` | Class extending `BaseToolV2` |
| Import | `from hedera_agent_kit.shared.tool import Tool` | `from hedera_agent_kit.shared.tool_v2 import BaseToolV2` |
| Lifecycle stages | All inside a single `execute()` method | Split into `normalize_params`, `core_action`, `secondary_action` |
| Hook/Policy support | ✗ None | ✓ Automatic at stages 1, 3, 5, 7 |
| Error handling | Manual `try/except` inside `execute()` (or delegated to standalone function) | Override `handle_error()` (BaseToolV2 provides a default) |
| Breaking change? | — | **No** — `BaseToolV2` implements `Tool` |

## Migrating a query-only tool

For tools that only read data (no transaction signing), override `should_secondary_action` to skip stage 6:

```python
class MyQueryTool(BaseToolV2):
    """Example query-only tool that doesn't require transaction signing."""

    def __init__(self, context: Context):
        self.method = "my_query_tool"
        self.name = "My Query Tool"
        self.description = "Queries data from Hedera"
        self.parameters = MyQueryParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> Any:
        """Normalize query parameters."""
        return await HederaParameterNormaliser.normalise_my_query(
            params, context, client
        )

    async def core_action(
        self, normalized_params: Any, context: Context, client: Client
    ) -> Any:
        """Perform the query and return the result directly."""
        # For query tools, core_action performs the entire operation
        # and returns the final result
        query_result = await some_hedera_query(normalized_params, client)
        return ToolResponse(
            human_message=f"Query successful: {query_result}",
            raw=query_result,
        )

    async def should_secondary_action(
        self, core_result: Any, context: Context
    ) -> bool:
        """Skip secondary action for query tools.

        Query tools don't need transaction signing, so we skip stage 6.
        """
        return False

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> Any:
        """No-op for query tools.

        This method is still required by the abstract class but won't be called
        if should_secondary_action() returns False.
        """
        return core_result
```

## Key benefits of migrating

1. **Automatic hook execution**: Your tool will automatically participate in all registered hooks (audit trails, logging, metrics, etc.) without any additional code.

2. **Policy enforcement**: Policies like `RejectToolPolicy` or `MaxRecipientsPolicy` can intercept and validate your tool's execution at any lifecycle stage.

3. **Cleaner separation of concerns**: Logic is split into distinct stages (normalization, core action, secondary action), making the code easier to understand and test.

4. **Consistent error handling**: The framework provides centralized error handling that you can override when needed.

5. **Future-proof**: As the Hedera Agent Kit evolves, new hooks and policies will automatically work with your migrated tools.

## Migration checklist

- [ ] Change import from `Tool` to `BaseToolV2`
- [ ] Extract parameter normalization logic into `normalize_params()` method
- [ ] Extract core logic (transaction building or query execution) into `core_action()` method
- [ ] Move transaction signing/submission into `secondary_action()` method (transaction tools only)
- [ ] For query tools, implement `should_secondary_action()` to return `False`
- [ ] (Optional) Override `handle_error()` for custom error messages
- [ ] Remove the standalone `execute()` method implementation
- [ ] Remove any standalone function that contained the monolithic logic (optional, can keep for backward compatibility if needed)
- [ ] Test with hooks and policies enabled to ensure proper integration

## Additional resources

- [Hooks and Policies Guide](./HOOKS_AND_POLICIES.md) - Learn how to create and use hooks and policies
- [Tool Interface Documentation](../python/hedera_agent_kit/shared/tool.py) - Base `Tool` class reference
- [BaseToolV2 Implementation](../python/hedera_agent_kit/shared/tool_v2.py) - `BaseToolV2` class reference
