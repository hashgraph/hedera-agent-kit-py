"""Unit tests for MaxRecipientsPolicy — mirrors the TypeScript SDK test suite structure."""

from __future__ import annotations

from typing import Any

import pytest
import asyncio
from unittest.mock import MagicMock

from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy
from hedera_agent_kit.shared.configuration import AgentMode, Context
from hedera_agent_kit.hooks.abstract_hook import PostParamsNormalizationParams
from hedera_agent_kit.plugins.core_account_plugin import core_account_plugin_tool_names
from hedera_agent_kit.plugins.core_token_plugin import core_token_plugin_tool_names


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context() -> Context:
    return Context(mode=AgentMode.AUTONOMOUS)


def _make_params(normalized: Any) -> PostParamsNormalizationParams:
    """Build a PostParamsNormalizationParams with the given normalised mock."""
    params = MagicMock(spec=PostParamsNormalizationParams)
    params.normalized_params = normalized
    return params


def _block(
    policy: MaxRecipientsPolicy,
    context: Context,
    params: PostParamsNormalizationParams,
    method: str,
) -> bool:
    """Helper to run the async policy check synchronously in tests."""
    return asyncio.run(
        policy.should_block_post_params_normalization(context, params, method)
    )


# ---------------------------------------------------------------------------
# TRANSFER_HBAR_TOOL
# ---------------------------------------------------------------------------


class TestTransferHbarTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        # Sender is negative, recipients are positive
        normalized.hbar_transfers = {"0.0.100": -2, "0.0.1": 1, "0.0.2": 1}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
            )
            is True
        )

    def test_does_not_block_when_recipients_within_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(2)
        normalized = MagicMock()
        normalized.hbar_transfers = {"0.0.100": -2, "0.0.1": 1, "0.0.2": 1}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
            )
            is False
        )

    def test_does_not_count_zero_amount_as_recipient(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        normalized.hbar_transfers = {"0.0.100": -1, "0.0.1": 1, "0.0.2": 0}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"],
            )
            is False
        )


# ---------------------------------------------------------------------------
# TRANSFER_HBAR_WITH_ALLOWANCE_TOOL
# ---------------------------------------------------------------------------


class TestTransferHbarWithAllowanceTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        normalized.hbar_approved_transfers = {"0.0.100": -2, "0.0.1": 1, "0.0.2": 1}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_account_plugin_tool_names["TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"],
            )
            is True
        )

    def test_does_not_block_when_recipients_within_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(2)
        normalized = MagicMock()
        normalized.hbar_approved_transfers = {"0.0.100": -2, "0.0.1": 1, "0.0.2": 1}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_account_plugin_tool_names["TRANSFER_HBAR_WITH_ALLOWANCE_TOOL"],
            )
            is False
        )


# ---------------------------------------------------------------------------
# AIRDROP_FUNGIBLE_TOKEN_TOOL
# ---------------------------------------------------------------------------


class TestAirdropFungibleTokenTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        # Airdrop normaliser produces a list of TokenTransfer objects
        normalized.token_transfers = [MagicMock(amount=25), MagicMock(amount=25)]
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names["AIRDROP_FUNGIBLE_TOKEN_TOOL"],
            )
            is True
        )

    def test_does_not_block_when_recipients_within_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(2)
        normalized = MagicMock()
        normalized.token_transfers = [MagicMock(amount=25), MagicMock(amount=25)]
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names["AIRDROP_FUNGIBLE_TOKEN_TOOL"],
            )
            is False
        )


# ---------------------------------------------------------------------------
# TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL
# ---------------------------------------------------------------------------


class TestTransferFungibleTokenWithAllowanceTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        normalized.ft_approved_transfer = {
            "0.0.999": {"0.0.100": -50, "0.0.1": 25, "0.0.2": 25}
        }
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names[
                    "TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL"
                ],
            )
            is True
        )

    def test_does_not_block_when_recipients_within_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(2)
        normalized = MagicMock()
        normalized.ft_approved_transfer = {
            "0.0.999": {"0.0.100": -50, "0.0.1": 25, "0.0.2": 25}
        }
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names[
                    "TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL"
                ],
            )
            is False
        )


# ---------------------------------------------------------------------------
# TRANSFER_NFT_WITH_ALLOWANCE_TOOL
# ---------------------------------------------------------------------------


class TestNftWithAllowanceTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        # Length of the list dictates recipient count
        normalized.nft_approved_transfer = {"0.0.999": [MagicMock(), MagicMock()]}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names["TRANSFER_NFT_WITH_ALLOWANCE_TOOL"],
            )
            is True
        )

    def test_does_not_block_when_recipients_within_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(2)
        normalized = MagicMock()
        normalized.nft_approved_transfer = {"0.0.999": [MagicMock(), MagicMock()]}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names["TRANSFER_NFT_WITH_ALLOWANCE_TOOL"],
            )
            is False
        )


# ---------------------------------------------------------------------------
# TRANSFER_NON_FUNGIBLE_TOKEN_TOOL
# ---------------------------------------------------------------------------


class TestNonFungibleTokenTool:
    def test_blocks_when_recipients_exceed_max(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        normalized = MagicMock()
        normalized.nft_transfers = {"0.0.999": [MagicMock(), MagicMock()]}
        params = _make_params(normalized)

        assert (
            _block(
                policy,
                context,
                params,
                core_token_plugin_tool_names["TRANSFER_NON_FUNGIBLE_TOKEN_TOOL"],
            )
            is True
        )


# ---------------------------------------------------------------------------
# Error handling / Unhandled Tools
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_raises_if_tool_not_handled(self):
        context = _make_context()
        policy = MaxRecipientsPolicy(1)
        params = _make_params({})

        with pytest.raises(ValueError, match="unhandled tool 'unknown_tool'"):
            _block(policy, context, params, "unknown_tool")


# ---------------------------------------------------------------------------
# Constructor / custom strategies
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_includes_additional_tools(self):
        policy = MaxRecipientsPolicy(1, additional_tools=["custom_tool"])
        assert "custom_tool" in policy.relevant_tools
        assert (
            core_account_plugin_tool_names["TRANSFER_HBAR_TOOL"]
            in policy.relevant_tools
        )

    def test_description_reflects_max_recipients(self):
        policy = MaxRecipientsPolicy(5)
        assert "5" in policy.description

    def test_uses_custom_strategy_for_unhandled_tool(self):
        # A custom strategy that just counts the length of a 'custom_recipients' list
        def my_strategy(normalized) -> int:
            return len(normalized.custom_recipients)

        policy = MaxRecipientsPolicy(
            max_recipients=2,
            additional_tools=["my_custom_tool"],
            custom_strategies={"my_custom_tool": my_strategy},
        )

        context = _make_context()

        # Test case 1: Should block (3 recipients > 2)
        normalized_block = MagicMock()
        normalized_block.custom_recipients = [1, 2, 3]
        params_block = _make_params(normalized_block)

        assert _block(policy, context, params_block, "my_custom_tool") is True

        # Test case 2: Should not block (2 recipients <= 2)
        normalized_allow = MagicMock()
        normalized_allow.custom_recipients = [1, 2]
        params_allow = _make_params(normalized_allow)

        assert _block(policy, context, params_allow, "my_custom_tool") is False
