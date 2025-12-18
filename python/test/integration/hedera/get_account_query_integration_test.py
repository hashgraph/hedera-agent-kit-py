import pytest
from hiero_sdk_python import PrivateKey

from hedera_agent_kit.plugins.core_account_query_plugin import GetAccountQueryTool
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.parameter_schemas import (
    AccountQueryParameters,
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from hedera_agent_kit.shared.models import ToolResponse


@pytest.fixture(scope="module")
async def setup_operator(operator_client, operator_wrapper):
    # operator_client and operator_wrapper are provided by conftest.py (session scope)
    yield {"client": operator_client, "wrapper": operator_wrapper}


@pytest.mark.asyncio
async def test_get_account_info_for_valid_account(setup_operator):
    operator_client = setup_operator["client"]
    operator_wrapper = setup_operator["wrapper"]

    # Create a fresh account
    private_key = PrivateKey.generate_ed25519()
    created_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(key=private_key.public_key())
    )
    created_account_id = created_resp.account_id
    await wait(MIRROR_NODE_WAITING_TIME)

    custom_client = get_custom_client(created_account_id, private_key)
    context = Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(custom_client.operator_account_id)
    )

    tool = GetAccountQueryTool(context)
    params = AccountQueryParameters(account_id=str(created_account_id))
    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert result is not None
    assert result.extra is not None
    assert result.extra["account"]["account_id"] == str(created_account_id)
    assert "Details for" in result.human_message
    assert "Balance:" in result.human_message
    assert "Public Key:" in result.human_message
    assert "EVM address:" in result.human_message

    custom_client.close()


@pytest.mark.asyncio
async def test_get_account_info_for_nonexistent_account(setup_operator):
    operator_client = setup_operator["client"]
    context = Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(operator_client.operator_account_id)
    )

    tool = GetAccountQueryTool(context)
    params = AccountQueryParameters(account_id="0.0.999999999")
    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert "Failed to get account query" in result.human_message


@pytest.mark.asyncio
async def test_get_account_info_for_operator_account(setup_operator):
    operator_client = setup_operator["client"]
    context = Context(
        mode=AgentMode.AUTONOMOUS, account_id=str(operator_client.operator_account_id)
    )

    tool = GetAccountQueryTool(context)
    operator_id = str(operator_client.operator_account_id)
    params = AccountQueryParameters(account_id=operator_id)

    result: ToolResponse = await tool.execute(operator_client, context, params)

    assert result.extra["account"]["account_id"] == operator_id
    assert "Details for" in result.human_message
    assert "Balance:" in result.human_message
    assert "Public Key:" in result.human_message
    assert "EVM address:" in result.human_message
