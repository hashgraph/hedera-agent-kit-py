"""Unit tests for RejectToolPolicy."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from hedera_agent_kit.policies.reject_tool_policy import RejectToolPolicy
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.hooks.abstract_hook import PreToolExecutionParams

import pytest


def _make_context() -> Context:
    return Context(mode=AgentMode.AUTONOMOUS)


def test_reject_tool_policy_initialization():
    """Test that the policy initializes correctly with the given tools."""
    relevant_tools = ["tool_a", "tool_b", "tool_c"]
    policy = RejectToolPolicy(relevant_tools)

    assert policy.relevant_tools == relevant_tools


@pytest.mark.asyncio
async def test_should_block_pre_tool_execution(caplog):
    """Test that the policy always blocks execution for relevant tools and logs appropriately."""
    relevant_tools = ["test_tool"]
    policy = RejectToolPolicy(relevant_tools)

    context = _make_context()
    params = MagicMock(spec=PreToolExecutionParams)

    with caplog.at_level(logging.INFO):
        # The hook should always return True regardless of the method passed
        result = await policy.should_block_pre_tool_execution(
            context, params, "test_tool"
        )

        assert result is True
        assert (
            "RejectToolPolicy: test_tool tool call rejected - tool not allowed"
            in caplog.text
        )


@pytest.mark.asyncio
async def test_should_block_pre_tool_execution_different_tool():
    """Test that the policy blocks execution even if a different tool name is passed."""
    policy = RejectToolPolicy(["test_tool"])
    context = _make_context()
    params = MagicMock(spec=PreToolExecutionParams)

    result = await policy.should_block_pre_tool_execution(
        context, params, "another_tool"
    )

    assert result is True
