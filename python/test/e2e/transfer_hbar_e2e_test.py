from decimal import Decimal
import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.plugins.core_account_plugin import core_account_plugin_tool_names
from hedera_agent_kit_py.shared.parameter_schemas import CreateAccountParametersNormalised
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import get_operator_client_for_tests, get_custom_client
from hedera_agent_kit_py.shared.hedera_utils import to_tinybars
from test.utils.teardown import return_hbars_and_delete_account

(TRANSFER_HBAR_TOOL,) = core_account_plugin_tool_names


@pytest.fixture(scope="module")
async def test_setup():
    """Setup LangChain agent and toolkit with a real Hedera executor account."""
    setup = await create_langchain_test_setup()
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(test_setup):
    return test_setup.agent


@pytest.fixture
async def toolkit(test_setup):
    return test_setup.toolkit



@pytest.fixture
async def executor_wrapper():
    """Return the HederaOperationsWrapper to the executor account."""

    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    executor_key_pair = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(5, in_tinybars=False),
            key=executor_key_pair.public_key(),
        )
    )

    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    return HederaOperationsWrapper(executor_client)



@pytest.fixture
async def recipient_account(executor_wrapper):
    """Create a new recipient account for each test."""
    operator_client = get_operator_client_for_tests()
    recipient_resp = await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=0, key=operator_client.operator_private_key.public_key()
        )
    )
    account_id = recipient_resp.account_id
    yield account_id
    # Cleanup: return funds and delete an account
    await return_hbars_and_delete_account(
        executor_wrapper, account_id, operator_client.operator_account_id
    )


@pytest.mark.asyncio
async def test_simple_transfer(agent_executor, recipient_account, executor_wrapper):
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    amount = 0.1

    input_text = f"Transfer {amount} HBAR to {recipient_account}"
    config = RunnableConfig(configurable={"thread_id": "1"})
    await agent_executor.ainvoke({"messages": [{"role": "user", "content": input_text}]}, config=config)

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert balance_after - balance_before == to_tinybars(Decimal(amount))


@pytest.mark.asyncio
async def test_transfer_with_memo(agent_executor, recipient_account, executor_wrapper):
    balance_before = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    amount = 0.05
    memo = "Payment for services"

    input_text = f'Transfer {amount} HBAR to {recipient_account} with memo "{memo}"'
    config = RunnableConfig(configurable={"thread_id": "1"})
    await agent_executor.ainvoke({"messages": [{"role": "user", "content": input_text}]}, config=config)

    balance_after = executor_wrapper.get_account_hbar_balance(str(recipient_account))
    assert balance_after - balance_before == to_tinybars(Decimal(amount))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, account_id, amount",
    [
        ("Please send 5 HBAR to account 0.0.7777", "0.0.7777", 5),
        ("I want to transfer 3.14 HBAR to 0.0.8888", "0.0.8888", 3.14),
        ("Can you move 10 HBAR to 0.0.9999?", "0.0.9999", 10),
    ],
)
async def test_natural_language_variations(agent_executor, executor_wrapper, input_text, account_id, amount):
    """Test multiple ways of specifying HBAR transfers in natural language."""
    balance_before = executor_wrapper.get_account_hbar_balance(account_id)

    config = RunnableConfig(configurable={"thread_id": "1"})
    await agent_executor.ainvoke({"messages": [{"role": "user", "content": input_text}]}, config=config)

    balance_after = executor_wrapper.get_account_hbar_balance(account_id)
    assert balance_after - balance_before == to_tinybars(Decimal(amount))
