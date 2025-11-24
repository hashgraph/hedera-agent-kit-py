import pytest
from hiero_sdk_python import (
    Client,
    PrivateKey,
    Hbar,
    SupplyType,
)
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams

from hedera_agent_kit_py.plugins.core_token_query_plugin import GetTokenInfoQueryTool
from hedera_agent_kit_py.shared import AgentMode
from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.models import ToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateFungibleTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    GetTokenInfoParameters,
)
from test import HederaOperationsWrapper, wait
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


@pytest.fixture(scope="module")
async def setup_accounts():
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Setup executor account (the one querying)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(20)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))

    # Define standard token params for tests
    ft_params = TokenParams(
        token_name="QueryTestToken",
        token_symbol="QTEST",
        initial_supply=100,
        decimals=2,
        max_supply=1000,
        supply_type=SupplyType.FINITE,
        treasury_account_id=executor_account_id,
    )

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "context": context,
        "FT_PARAMS": ft_params,
    }

    # Teardown
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()
    operator_client.close()


async def create_test_token(
    executor_wrapper: HederaOperationsWrapper,
    executor_client: Client,
    ft_params: TokenParams,
):
    # Use executor's key for admin/supply
    public_key = executor_client.operator_private_key.public_key()

    keys = TokenKeys(
        supply_key=public_key,
        admin_key=public_key,
    )

    create_params = CreateFungibleTokenParametersNormalised(
        token_params=ft_params, keys=keys
    )

    resp = await executor_wrapper.create_fungible_token(create_params)
    return resp.token_id


@pytest.mark.asyncio
async def test_get_token_info_success(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    executor_wrapper: HederaOperationsWrapper = setup_accounts["executor_wrapper"]
    context: Context = setup_accounts["context"]
    ft_params: TokenParams = setup_accounts["FT_PARAMS"]

    # 1. Create a token to query
    token_id = await create_test_token(executor_wrapper, executor_client, ft_params)

    # 2. Wait for Mirror Node to ingest the token creation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Execute Tool
    tool = GetTokenInfoQueryTool(context)
    params = GetTokenInfoParameters(token_id=str(token_id))

    result: ToolResponse = await tool.execute(executor_client, context, params)

    # 4. Validation
    assert result.error is None
    assert result.extra is not None
    assert "tokenInfo" in result.extra

    token_info = result.extra["tokenInfo"]
    assert token_info["token_id"] == str(token_id)
    assert token_info["name"] == ft_params.token_name
    assert token_info["symbol"] == ft_params.token_symbol
    assert str(token_info["decimals"]) == str(ft_params.decimals)

    # Verify human readable message contains key info
    assert ft_params.token_name in result.human_message
    assert ft_params.token_symbol in result.human_message
    assert "Current Supply" in result.human_message


@pytest.mark.asyncio
async def test_get_token_info_invalid_id(setup_accounts):
    executor_client: Client = setup_accounts["executor_client"]
    context: Context = setup_accounts["context"]

    # 1. Execute Tool with non-existent ID
    tool = GetTokenInfoQueryTool(context)
    params = GetTokenInfoParameters(token_id="0.0.999999999")

    result: ToolResponse = await tool.execute(executor_client, context, params)

    # 2. Validation
    assert result.error is not None
    assert "Failed to get token info" in result.human_message
    # Mirror node usually returns Not Found or 404-like error in the exception message
    assert "Not Found" in result.human_message or "404" in str(result.error)
