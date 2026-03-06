"""Integration tests for MaxRecipientsPolicy with TransferHbarTool.

These tests execute against the real Hedera testnet and verify that the policy
correctly blocks or allows tool calls based on the number of recipients.
"""

from __future__ import annotations

import pytest

from hedera_agent_kit.plugins.core_account_plugin import TransferHbarTool
from hedera_agent_kit.policies.max_recipients_policy import MaxRecipientsPolicy
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.parameter_schemas import (
    TransferHbarParameters,
    TransferHbarEntry,
)
from hedera_agent_kit.shared.models import ToolResponse


# operator_client fixture is session-scoped and provided by test/conftest.py


@pytest.mark.asyncio
async def test_blocks_transfer_hbar_tool_when_recipients_exceed_limit(operator_client):
    """Policy with max=1 must block a 2-recipient HBAR transfer."""
    policy = MaxRecipientsPolicy(1)
    context = Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(operator_client.operator_account_id),
        hooks=[policy],
    )

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[
            TransferHbarEntry(account_id="0.0.1", amount=0.1),
            TransferHbarEntry(account_id="0.0.2", amount=0.1),
        ]
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert result.error is not None
    assert "blocked by policy: Max Recipients Policy" in result.error
    assert "Limits the maximum number of recipients to 1" in result.error


@pytest.mark.asyncio
async def test_allows_transfer_hbar_tool_when_recipients_within_limit(operator_client):
    """Policy with max=10 must allow a 1-recipient HBAR transfer."""
    policy = MaxRecipientsPolicy(10)
    context = Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(operator_client.operator_account_id),
        hooks=[policy],
    )

    tool = TransferHbarTool(context)
    params = TransferHbarParameters(
        transfers=[
            TransferHbarEntry(account_id="0.0.1", amount=0.1),
        ]
    )

    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert result.error is None or "blocked by policy" not in result.error
