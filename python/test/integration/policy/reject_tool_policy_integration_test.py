"""Integration tests for RejectToolPolicy.

These tests verify that the policy correctly blocks tool calls based on the method name
before they execute against the Hedera network.
"""

from __future__ import annotations

import pytest

from hedera_agent_kit.plugins.core_account_plugin import TransferHbarTool
from hedera_agent_kit.policies.reject_tool_policy import RejectToolPolicy
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarEntry,
)


@pytest.mark.asyncio
async def test_blocks_tool_when_in_relevant_tools(operator_client):
    """Policy must block execution when the tool name matches the rejected list."""
    policy = RejectToolPolicy(["transfer_hbar_tool"])
    context = Context(
        mode=AgentMode.AUTONOMOUS,
        hooks=[policy],
    )

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[TransferHbarEntry(account_id="0.0.1234", amount=1.0)],
        transaction_memo="Test blocked transaction",
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert result.error is not None
    assert "Action blocked by policy: Reject Tool Policy" in result.error


@pytest.mark.asyncio
async def test_allows_tool_when_not_in_relevant_tools(operator_client):
    """Policy should not block execution for tools that are not in the rejected list."""
    policy = RejectToolPolicy(["some_other_tool"])
    context = Context(
        mode=AgentMode.AUTONOMOUS,
        hooks=[policy],
    )

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[
            TransferHbarEntry(
                account_id="INVALID_ACCOUNT_ID_SO_IT_DOESNT_EXECUTE", amount=1.0
            )
        ],
        transaction_memo="Test allowed transaction",
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)

    # It should fail because the account doesn't exist/can't parse it
    # but NOT because of the RejectToolPolicy.
    if result.error is not None:
        assert "Action blocked by policy: Reject Tool Policy" not in result.error
