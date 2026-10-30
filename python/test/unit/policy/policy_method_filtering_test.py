from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from hedera_agent_kit.shared.hook import PreToolExecutionParams
from hedera_agent_kit.shared.policy import AbstractPolicy


class TrackingPolicy(AbstractPolicy):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "Tracking Policy"

    @property
    def relevant_tools(self) -> list[str]:
        return ["transfer_hbar_tool"]

    async def should_block_pre_tool_execution(
        self, context: object, params: PreToolExecutionParams, method: str
    ) -> bool:
        self.calls += 1
        return False


@pytest.mark.asyncio
async def test_policy_logs_debug_when_method_name_does_not_match(caplog):
    policy = TrackingPolicy()
    context = object()
    params = MagicMock(spec=PreToolExecutionParams)

    with caplog.at_level(logging.DEBUG):
        await policy.pre_tool_execution_hook(context, params, "transfer_hbar")

    assert policy.calls == 0
    assert "skipped pre_tool_execution_hook" in caplog.text
    assert "transfer_hbar" in caplog.text
    assert "transfer_hbar_tool" in caplog.text


@pytest.mark.asyncio
async def test_policy_runs_when_exact_tool_method_matches(caplog):
    policy = TrackingPolicy()
    context = object()
    params = MagicMock(spec=PreToolExecutionParams)

    with caplog.at_level(logging.DEBUG):
        await policy.pre_tool_execution_hook(context, params, "transfer_hbar_tool")

    assert policy.calls == 1
    assert "skipped pre_tool_execution_hook" not in caplog.text
