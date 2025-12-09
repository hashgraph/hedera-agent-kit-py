import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.verification import extract_tool_response

DEFAULT_EXECUTOR_BALANCE = Hbar(5, in_tinybars=False)


@pytest.fixture(scope="session")
def operator_client():
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    return HederaOperationsWrapper(operator_client)


@pytest.fixture
async def executor_account(operator_wrapper, operator_client):
    executor_key: PrivateKey = PrivateKey.generate_ed25519()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=executor_key.public_key()
        )
    )
    executor_account_id = resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper_instance = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key, executor_client, executor_wrapper_instance

    await return_hbars_and_delete_account(
        executor_wrapper_instance,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture
async def langchain_test_setup(executor_account):
    _, _, executor_client, _ = executor_account
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    return langchain_test_setup.agent


@pytest.fixture
async def executor_wrapper(executor_account):
    _, _, _, wrapper = executor_account
    return wrapper


@pytest.fixture
def langchain_config():
    return RunnableConfig(configurable={"thread_id": "update_account_e2e"})


async def create_test_account(
    executor_wrapper, executor_client, initial_balance_in_hbars=Hbar(0)
):
    return await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_client.operator_private_key.public_key(),
            initial_balance=initial_balance_in_hbars,
        )
    )


@pytest.mark.asyncio
async def test_update_account_memo(
    agent_executor, executor_wrapper, executor_account, langchain_config
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(executor_wrapper, executor_client)
    target_account_id = str(resp.account_id)

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f'Update account {target_account_id} memo to "updated via agent"',
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "update_account_tool")
    assert "updated" in observation.human_message.lower()
    account_info = executor_wrapper.get_account_info(target_account_id)
    assert account_info.account_memo == "updated via agent"


@pytest.mark.asyncio
async def test_update_max_auto_token_associations(
    agent_executor, executor_wrapper, executor_account, langchain_config
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(executor_wrapper, executor_client)
    target_account_id = str(resp.account_id)

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Set max automatic token associations for account {target_account_id} to 10",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "update_account_tool")
    assert "updated" in observation.human_message.lower()
    account_info = executor_wrapper.get_account_info(target_account_id)
    # assert account_info.max_automatic_token_associations.to_number() == 10  # FIXME: not supported by the SDK - implemented for future use


@pytest.mark.asyncio
async def test_update_decline_staking_rewards(
    agent_executor, executor_wrapper, executor_account, langchain_config
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(executor_wrapper, executor_client)
    target_account_id = str(resp.account_id)

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Update account {target_account_id} to decline staking rewards",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "update_account_tool")
    assert "updated" in observation.human_message.lower()
    account_info = executor_wrapper.get_account_info(target_account_id)
    # assert account_info.staking_info.decline_staking_reward is True  # FIXME: not supported by the SDK - implemented for future use


@pytest.mark.asyncio
async def test_fail_update_non_existent_account(
    agent_executor, executor_wrapper, langchain_config
):
    fake_account_id = "0.0.999999999"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Update account {fake_account_id} memo to 'x'",
                }
            ]
        },
        config=langchain_config,
    )

    observation = extract_tool_response(result, "update_account_tool")
    assert any(
        err in observation.human_message.upper()
        for err in [
            "INVALID_ACCOUNT_ID",
            "ACCOUNT_DELETED",
            "NOT_FOUND",
            "INVALID_SIGNATURE",
        ]
    )
