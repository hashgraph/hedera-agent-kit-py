from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, cast, Dict, Callable, Any

from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParametersNormalised,
    TransferHbarWithAllowanceParametersNormalised,
    AirdropFungibleTokenParametersNormalised,
    TransferFungibleTokenWithAllowanceParametersNormalised,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
    TransferNonFungibleTokenParametersNormalised,
)
from hedera_agent_kit.shared.policy import Policy
from hedera_agent_kit.shared.abstract_hook import PostParamsNormalizationParams
from hedera_agent_kit.plugins.core_account_plugin import core_account_plugin_tool_names
from hedera_agent_kit.plugins.core_token_plugin import core_token_plugin_tool_names

if TYPE_CHECKING:
    from hedera_agent_kit.shared.configuration import Context

logger = logging.getLogger(__name__)

_DEFAULT_RELEVANT_TOOLS: List[str] = [
    core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
    core_account_plugin_tool_names["TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"],
    core_token_plugin_tool_names["AIRDROP_FUNGIBLE_TOKEN_TOOL"],
    core_token_plugin_tool_names["TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL"],
    core_token_plugin_tool_names["TRANSFER_NFT_WITH_ALLOWANCE_TOOL"],
    core_token_plugin_tool_names["TRANSFER_NON_FUNGIBLE_TOKEN_TOOL"],
]


class MaxRecipientsPolicy(Policy):
    """
    Limits the maximum number of recipients allowed in a single transfer / airdrop call.

    Works for HBAR transfers, fungible-token transfers, NFT transfers and airdrops.
    The policy is evaluated *after* parameter normalization so it operates on the
    already-parsed SDK objects rather than raw LLM text.

    If you are adding custom tools using the `additional_tools` parameter, you must
    also provide a strategy to count the recipients using the `custom_strategies` parameter.

    Args:
        max_recipients (int): The maximum number of recipients allowed.
        additional_tools (List[str] | None): Optional list of tool names to apply the
            policy to, in addition to the default tools.
        custom_strategies (Dict[str, Callable[[Any], int]] | None): Optional dictionary
            mapping tool names to functions that calculate the number of recipients
            for the tool. Required for any tools provided in `additional_tools`.

    Example:
        ```python
        def my_custom_tool_strategy(normalized_params: Any) -> int:
            # Custom logic to count recipients from the normalized params
            return len(normalized_params.custom_recipients)

        policy = MaxRecipientsPolicy(
            max_recipients=5,
            additional_tools=["my_custom_tool"],
            custom_strategies={
                "my_custom_tool": my_custom_tool_strategy
            }
        )
        ```
    """

    @property
    def name(self) -> str:
        return "Max Recipients Policy"

    @property
    def description(self) -> str:
        return self._description

    @property
    def relevant_tools(self) -> List[str]:
        return self._relevant_tools

    def __init__(
        self,
        max_recipients: int,
        additional_tools: List[str] | None = None,
        custom_strategies: Dict[str, Callable[[Any], int]] | None = None,
    ) -> None:
        self._max_recipients: int = max_recipients
        self._description: str = (
            f"Limits the maximum number of recipients to {max_recipients}"
        )
        self._relevant_tools: List[str] = list(_DEFAULT_RELEVANT_TOOLS)
        if additional_tools:
            self._relevant_tools.extend(additional_tools)

        self._custom_strategies = custom_strategies or {}

    async def should_block_post_params_normalization(
        self,
        context: Context,
        params: PostParamsNormalizationParams,
        method: str,
    ) -> bool:
        try:
            normalized = params.normalized_params
            recipient_count = 0

            # 1. Custom Strategy override
            if method in self._custom_strategies:
                recipient_count = self._custom_strategies[method](normalized)
            # 2. Built-in tools
            elif method == core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]:
                normalized = cast(TransferHbarParametersNormalised, normalized)
                recipient_count += sum(
                    1 for v in normalized.hbar_transfers.values() if v > 0
                )
            elif (
                method
                == core_account_plugin_tool_names["TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"]
            ):
                normalized = cast(
                    TransferHbarWithAllowanceParametersNormalised, normalized
                )
                recipient_count += sum(
                    1 for v in normalized.hbar_approved_transfers.values() if v > 0
                )
            elif method == core_token_plugin_tool_names["AIRDROP_FUNGIBLE_TOKEN_TOOL"]:
                normalized = cast(AirdropFungibleTokenParametersNormalised, normalized)
                recipient_count += len(normalized.token_transfers)
            elif (
                method
                == core_token_plugin_tool_names[
                    "TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL"
                ]
            ):
                normalized = cast(
                    TransferFungibleTokenWithAllowanceParametersNormalised, normalized
                )
                for transfers in normalized.ft_approved_transfer.values():
                    recipient_count += sum(1 for v in transfers.values() if v > 0)
            elif (
                method
                == core_token_plugin_tool_names["TRANSFER_NFT_WITH_ALLOWANCE_TOOL"]
            ):
                normalized = cast(
                    TransferNonFungibleTokenWithAllowanceParametersNormalised,
                    normalized,
                )
                for transfers in normalized.nft_approved_transfer.values():
                    recipient_count += len(transfers)
            elif (
                method
                == core_token_plugin_tool_names["TRANSFER_NON_FUNGIBLE_TOKEN_TOOL"]
            ):
                normalized = cast(
                    TransferNonFungibleTokenParametersNormalised, normalized
                )
                for transfers in normalized.nft_transfers.values():
                    recipient_count += len(transfers)
            else:
                raise ValueError(
                    f"MaxRecipientsPolicy: unhandled tool '{method}'. "
                    "Please provide a custom counting strategy for this tool via the "
                    "'custom_strategies' constructor parameter."
                )

            if recipient_count > self._max_recipients:
                logger.info(
                    "MaxRecipientsPolicy: %s tool call rejected — expected max %d recipients, got %d",
                    method,
                    self._max_recipients,
                    recipient_count,
                )
                return True

            return False

        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError(
                f"MaxRecipientsPolicy: An unknown error occurred in MaxRecipientsPolicy in tool {method}"
            ) from exc
