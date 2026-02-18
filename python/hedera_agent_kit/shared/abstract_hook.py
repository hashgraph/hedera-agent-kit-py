from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, List, TypeVar

if TYPE_CHECKING:
    from .configuration import Context

TParams = TypeVar("TParams")
TNormalizedParams = TypeVar("TNormalizedParams")


@dataclass
class PreToolExecutionParams(Generic[TParams]):
    context: Context
    raw_params: TParams


@dataclass
class PostParamsNormalizationParams(Generic[TParams, TNormalizedParams]):
    context: Context
    raw_params: TParams
    normalized_params: TNormalizedParams


@dataclass
class PostCoreActionParams(Generic[TParams, TNormalizedParams]):
    context: Context
    raw_params: TParams
    normalized_params: TNormalizedParams
    core_action_result: Any


@dataclass
class PostSecondaryActionParams(Generic[TParams, TNormalizedParams]):
    context: Context
    raw_params: TParams
    normalized_params: TNormalizedParams
    core_action_result: Any
    tool_result: Any


class AbstractHook(ABC):
    """
    Abstract class for defining hooks that can be used to extend the functionality of the Hedera-Agent-Kit.
    Hooks are executed in the order they are defined in the relevant tool's class.
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

    async def pre_tool_execution_hook(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

    async def post_params_normalization_hook(
        self, context: Context, params: PostParamsNormalizationParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

    async def post_core_action_hook(
        self, context: Context, params: PostCoreActionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

    async def post_secondary_action_hook(
        self, context: Context, params: PostSecondaryActionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return
