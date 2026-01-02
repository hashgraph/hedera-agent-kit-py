import pytest
from hiero_sdk_python import Hbar, PrivateKey, AccountId, Client

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account


DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
    executor_key = PrivateKey.generate_ed25519()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key.public_key(),
        )
    )
    executor_account_id: AccountId = resp.account_id
    executor_client: Client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=executor_client)

    resources = {
        "executor_account_id": executor_account_id,
        "executor_key": executor_key,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture(scope="module")
def executor_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["executor_account_id"],
        res["executor_key"],
        res["executor_client"],
        res["executor_wrapper"],
    )


@pytest.fixture(scope="module")
def executor_wrapper(setup_module_resources):
    return setup_module_resources["executor_wrapper"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "delete_account_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_test_account(
    executor_wrapper, executor_client, initial_balance_in_hbar=Hbar(0)
):
    return await executor_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_client.operator_private_key.public_key(),
            initial_balance=initial_balance_in_hbar,
        )
    )


def extract_tool_human_message(
    agent_result, response_parser: ResponseParserService, tool_name: str
) -> str:
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found")
    if parsed_tool_calls[0].toolName != tool_name:
        raise ValueError(
            f"Incorrect tool name. Called {parsed_tool_calls[0].toolName} instead of {tool_name}"
        )

    return parsed_tool_calls[0].parsedData["humanMessage"]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_delete_pre_created_account_default_transfer(
    agent_executor,
    executor_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(executor_wrapper, executor_client)
    target_account_id = str(resp.account_id)

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {"role": "user", "content": f"Delete the account {target_account_id}"}
            ]
        },
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "delete_account_tool"
    )
    assert "deleted" in human_message.lower()


@pytest.mark.asyncio
async def test_delete_pre_created_account_with_explicit_transfer(
    agent_executor,
    executor_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(executor_wrapper, executor_client)
    target_account_id = str(resp.account_id)
    transfer_account_id = str(executor_client.operator_account_id)

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Delete the account {target_account_id} and transfer remaining balance to {transfer_account_id}",
                }
            ]
        },
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "delete_account_tool"
    )
    assert "deleted" in human_message.lower()


@pytest.mark.asyncio
async def test_delete_non_existent_account(
    agent_executor, executor_wrapper, langchain_config, response_parser
):
    fake_account_id = "0.0.999999999"

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {"role": "user", "content": f"Delete the account {fake_account_id}"}
            ]
        },
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "delete_account_tool"
    )
    assert any(
        err in human_message.upper()
        for err in [
            "INVALID_ACCOUNT_ID",
            "ACCOUNT_DELETED",
            "NOT_FOUND",
            "INVALID_SIGNATURE",
        ]
    )


@pytest.mark.asyncio
async def test_delete_account_with_natural_language_variations(
    agent_executor,
    executor_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    _, _, executor_client, _ = executor_account
    resp = await create_test_account(
        executor_wrapper,
        executor_client,
        initial_balance_in_hbar=Hbar(
            UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])
        ),
    )
    target_account_id = str(resp.account_id)

    operator_balance_before = executor_wrapper.get_account_hbar_balance(
        str(executor_client.operator_account_id)
    )

    result = await agent_executor.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Remove account id {target_account_id} and send balance to {executor_client.operator_account_id}",
                }
            ]
        },
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "delete_account_tool"
    )
    assert "deleted" in human_message.lower()

    await wait(MIRROR_NODE_WAITING_TIME)

    operator_balance_after = executor_wrapper.get_account_hbar_balance(
        str(executor_client.operator_account_id)
    )

    assert operator_balance_after > operator_balance_before
