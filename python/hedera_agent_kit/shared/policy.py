from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, List

from hedera_agent_kit.shared.hook import (
    AbstractHook,
    PostCoreActionParams,
    PostParamsNormalizationParams,
    PostSecondaryActionParams,
    PreToolExecutionParams,
)

if TYPE_CHECKING:
    from .configuration import Context


class AbstractPolicy(AbstractHook, ABC):
    """
    Policy extends Hook and throws errors when validation fails.
    """

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        return ""

    @property
    def relevant_tools(self) -> List[str]:
        raise NotImplementedError

    async def should_block_pre_tool_execution(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> bool:
        """
        Default implementation - no validation at PreToolExecution.
        Override in derived classes to implement custom logic.
        """
        return False

    async def should_block_post_params_normalization(
        self, context: Context, params: PostParamsNormalizationParams, method: str
    ) -> bool:
        """
        Default implementation - no validation at PostParamsNormalization.
        Override in derived classes to implement custom logic.
        """
        return False

    async def should_block_post_core_action(
        self, context: Context, params: PostCoreActionParams, method: str
    ) -> bool:
        """
        Default implementation - no validation at PostCoreAction.
        Override in derived classes to implement custom logic.
        """
        return False

    async def should_block_post_secondary_action(
        self, context: Context, params: PostSecondaryActionParams, method: str
    ) -> bool:
        """
        Default implementation - no validation at PostSecondaryAction.
        Override in derived classes to implement custom logic.
        """
        return False

    async def pre_tool_execution_hook(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        should_block = await self.should_block_pre_tool_execution(
            context, params, method
        )
        if should_block:
            desc = f" ({self.description})" if self.description else ""
            raise ValueError(f"Action blocked by policy: {self.name}{desc}")

    async def post_params_normalization_hook(
        self, context: Context, params: PostParamsNormalizationParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        should_block = await self.should_block_post_params_normalization(
            context, params, method
        )
        if should_block:
            desc = f" ({self.description})" if self.description else ""
            raise ValueError(f"Action blocked by policy: {self.name}{desc}")

    async def post_core_action_hook(
        self, context: Context, params: PostCoreActionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        should_block = await self.should_block_post_core_action(context, params, method)
        if should_block:
            desc = f" ({self.description})" if self.description else ""
            raise ValueError(f"Action blocked by policy: {self.name}{desc}")

    async def post_secondary_action_hook(
        self, context: Context, params: PostSecondaryActionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        should_block = await self.should_block_post_secondary_action(
            context, params, method
        )
        if should_block:
            desc = f" ({self.description})" if self.description else ""
            raise ValueError(f"Action blocked by policy: {self.name}{desc}")
