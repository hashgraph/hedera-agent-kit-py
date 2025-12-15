import pytest
from hiero_sdk_python import PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService

from hedera_agent_kit.plugins.core_evm_query_plugin import (
    GetContractInfoQueryTool,
)
from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateERC20Parameters,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def erc20_contract():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Executor account (Agent performing transfers)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    params = CreateERC20Parameters(
        token_name="E2EInfoToken",
        token_symbol="EIT",
        decimals=18,
        initial_supply=1000,
    )

    create_result = await executor_wrapper.create_erc20(params)

    erc20_address = create_result.get("erc20_address")
    if not erc20_address:
        raise Exception("Failed to create ERC20 for get_contract_info_e2e tests")

    # Wait for mirror node to index the new contract
    await wait(MIRROR_NODE_WAITING_TIME)

    return erc20_address


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key_pair.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
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
async def test_fetch_contract_info_success(setup_accounts, erc20_contract):
    """Fetch info for a known contract id and verify success message content."""
    executor_client = setup_accounts["executor_client"]
    context = setup_accounts["context"]

    # Using contract ID deployed on testnet (verified)
    contract_id = str(erc20_contract)

    tool = GetContractInfoQueryTool(context)
    # Pass a plain dict for params; the tool implementation accesses params via `.get()`
    result = await tool.execute(
        executor_client,
        context,
        {"contract_id": contract_id},
    )

    assert result.error is None
    assert "Contract Info Query Result:" in result.human_message
    assert f"- EVM Address: {contract_id}" in result.human_message


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
