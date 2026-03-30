from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hiero_sdk_python import Client

from hedera_agent_kit.hooks.abstract_hook import (
    PostCoreActionParams,
    PostParamsNormalizationParams,
    PostSecondaryActionParams,
    PreToolExecutionParams,
)
from .configuration import Context
from .models import ToolResponse
from .tool import Tool


class BaseToolV2(Tool, ABC):
    """
    Abstract BaseToolV2 that implements the full hooks execution lifecycle.
    """

    async def execute(
        self, client: Client, context: Context, params: Any
    ) -> ToolResponse:
        """
        Orchestrates the tool execution lifecycle.
        """
        try:
            # 1. Pre-Execution Hook
            await self.pre_tool_execution_hook(
                PreToolExecutionParams(
                    context=context,
                    raw_params=params,
                    client=client,
                    method=self.method,
                )
            )

            # 2. Normalize Parameters
            normalized_params = await self.normalize_params(
                params=params, context=context, client=client
            )

            # 3. Post-Normalization Hook
            await self.post_params_normalization_hook(
                PostParamsNormalizationParams(
                    context=context,
                    raw_params=params,
                    normalized_params=normalized_params,
                    client=client,
                    method=self.method,
                )
            )

            # 4. Core Action
            core_action_result = await self.core_action(
                normalized_params=normalized_params, context=context, client=client
            )

            # 5. Post-Core-Action Hook
            await self.post_core_action_hook(
                PostCoreActionParams(
                    context=context,
                    raw_params=params,
                    normalized_params=normalized_params,
                    core_action_result=core_action_result,
                    client=client,
                    method=self.method,
                )
            )

            # 6. Secondary Action (Optional)
            result = core_action_result
            if await self.should_secondary_action(core_action_result, context):
                result = await self.secondary_action(
                    core_action_result, client=client, context=context
                )

            # 7. Post-Tool-Execution Hook (Returns a final result)
            tool_result = await self.post_tool_execution_hook(
                PostSecondaryActionParams(
                    context=context,
                    raw_params=params,
                    normalized_params=normalized_params,
                    core_action_result=core_action_result,
                    tool_result=result,
                    client=client,
                    method=self.method,
                )
            )

            return tool_result

        except Exception as e:
            return await self.handle_error(e, context)

    # --- Abstract Methods ---
    @abstractmethod
    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> Any:
        """Normalize input parameters."""
        pass

    @abstractmethod
    async def core_action(
        self, normalized_params: Any, context: Context, client: Client
    ) -> Any:
        """Execute the core logic of the tool."""
        pass

    # --- Virtual Methods (Can be overridden) ---

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        """Determine if a secondary action should run. Defaults to True."""
        return True

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> Any:
        """Execute optional secondary actions (e.g., signing transactions created in core_action)."""
        pass

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        """Handle execution errors."""
        desc = f"Failed to execute {self.name}"
        message = f"{desc}: {str(error)}"
        print(f"[{self.method}] {message}")
        return ToolResponse(human_message=message, error=message)

    # --- Lifecycle Hooks ---
    async def _execute_hooks(
        self,
        context: Context,
        hook_executor: Any,  # Callable that takes (hook, method) and returns awaitable
    ) -> None:
        """
        Generic hook execution method that executes hooks on all registered hooks.
        Hook-agnostic: just awaits the hook executor without caring about the result.
        """
        if not context.hooks:
            return

        for hook in context.hooks:
            await hook_executor(hook, self.method)

    async def pre_tool_execution_hook(self, params: PreToolExecutionParams) -> None:
        await self._execute_hooks(
            params.context,
            lambda h, m: h.pre_tool_execution_hook(params.context, params, m),
        )

    async def post_params_normalization_hook(
        self, params: PostParamsNormalizationParams
    ) -> None:
        await self._execute_hooks(
            params.context,
            lambda h, m: h.post_params_normalization_hook(params.context, params, m),
        )

    async def post_core_action_hook(self, params: PostCoreActionParams) -> None:
        await self._execute_hooks(
            params.context,
            lambda h, m: h.post_core_action_hook(params.context, params, m),
        )

    async def post_tool_execution_hook(
        self, params: PostSecondaryActionParams
    ) -> ToolResponse:
        await self._execute_hooks(
            params.context,
            lambda h, m: h.post_secondary_action_hook(params.context, params, m),
        )
        return params.tool_result
