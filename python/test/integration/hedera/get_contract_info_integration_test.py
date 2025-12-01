import pytest
from hiero_sdk_python import PrivateKey, Hbar

from hedera_agent_kit_py.plugins.core_evm_query_plugin import (
    GetContractInfoQueryTool,
)
from hedera_agent_kit_py.shared.configuration import Context, AgentMode
from hedera_agent_kit_py.shared.parameter_schemas import CreateAccountParametersNormalised
from test import HederaOperationsWrapper
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key_pair.public_key(),
            initial_balance=Hbar(30, in_tinybars=False),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)

    context = Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(executor_account_id),
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_account_id": executor_account_id,
        "operator_wrapper": operator_wrapper,
        "context": context,
    }

    await return_hbars_and_delete_account(
        HederaOperationsWrapper(executor_client),
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


@pytest.mark.asyncio
async def test_fetch_contract_info_success(setup_accounts):
    """Fetch info for a known contract id and verify success message content."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    # Using a known public contract ID on testnet (verified)
    contract_id = "0.0.7350754"

    tool = GetContractInfoQueryTool(context)
    # Pass a plain dict for params; the tool implementation accesses params via `.get()`
    result = await tool.execute(
        executor_client,
        context,
        {"contract_id": contract_id},
    )

    assert result.error is None
    assert "Contract Info Query Result:" in result.human_message
    assert f"- Contract ID: {contract_id}" in result.human_message


@pytest.mark.asyncio
async def test_fail_for_nonexistent_contract(setup_accounts):
    """Expect a failure message when querying a non-existent contract id."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    tool = GetContractInfoQueryTool(context)
    # Pass a plain dict for params; the tool implementation accesses params via `.get()`
    result = await tool.execute(
        executor_client,
        context,
        {"contract_id": "0.0.999999999"},
    )

    assert "Failed to get contract info" in result.human_message
