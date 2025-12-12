import time
import pytest

from hiero_sdk_python import (
    PrivateKey,
    Hbar,
    Client,
    AccountId,
    Timestamp,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferHbarParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
)
from test.utils.teardown import return_hbars_and_delete_account

DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def operator_client():
    return get_operator_client_for_tests()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    return HederaOperationsWrapper(operator_client)


# ============================================================================
# FUNCTION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture
async def executor_account(operator_wrapper, operator_client):
    """
    Creates a temporary executor account.
    Yields: (account_id, private_key, client, wrapper)
    Teardown: Returns remaining HBARs to operator and deletes account.
    """
    executor_key: PrivateKey = PrivateKey.generate_ed25519()
    resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE, key=executor_key.public_key()
        )
    )
    executor_account_id = resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()


@pytest.fixture
async def langchain_test_setup(executor_account):
    """
    Sets up the LangChain agent using the EXECUTOR Client.
    The Executor will be the Schedule Admin and the Payer.
    """
    _, _, executor_client, _ = executor_account

    # We pass the executor_client as the custom_client
    setup = await create_langchain_test_setup(custom_client=executor_client)
    yield setup
    setup.cleanup()


@pytest.fixture
async def agent_executor(langchain_test_setup):
    return langchain_test_setup.agent


@pytest.fixture
async def response_parser(langchain_test_setup):
    return langchain_test_setup.response_parser


@pytest.fixture
def langchain_config():
    return RunnableConfig(configurable={"thread_id": "schedule_delete_e2e"})


@pytest.fixture
def context(executor_account):
    """Context is now based on the Executor."""
    executor_id, _, _, _ = (
        executor_account  # ============================================================================
    )


# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_deletes_a_scheduled_transaction_by_admin(
    agent_executor,
    operator_client,
    executor_account,
    context,
    langchain_config,
    response_parser,
):
    """
    E2E Test:
    1. Setup: Executor creates a schedule (Executor -> Operator) with Executor as Admin.
    2. Act: Agent (running as Executor) deletes the schedule.
    3. Assert: Verify the tool output confirms deletion.
    """
    # Unpack executor fixture
    _, _, executor_client, executor_wrapper = executor_account

    # 1. Create the schedule
    # Executor sends funds to the Operator
    schedule_id = await create_deletable_scheduled_transaction(
        wrapper=executor_wrapper,
        client=executor_client,
        recipient_id=operator_client.operator_account_id,
    )

    # 2. Act: Ask agent (Executor) to delete it
    input_text = f"Delete scheduled transaction {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    # 3. Assert
    human_message = extract_tool_human_message(
        result, response_parser, "schedule_delete_tool"
    )

    assert "successfully deleted" in human_message.lower()
    return Context(
        mode=AgentMode.AUTONOMOUS,
        account_id=str(executor_client.operator_account_id),
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_deletable_scheduled_transaction(
    wrapper: HederaOperationsWrapper,
    client: Client,
    recipient_id: AccountId,
) -> str:
    """
    Creates a scheduled transaction using the Wrapper.

    The 'client' (Executor) creates the schedule, pays for it,
    sets itself as Admin, and is the one being debited in the transfer.
    """

    # Calculate expiration time (1 hour from now)
    future_seconds = int(time.time() + 60 * 60)
    expiration = Timestamp(seconds=future_seconds, nanos=0)

    # Set admin_key to the Executor's key (client.operator_public_key)
    # This allows the Agent (who is acting as Executor) to delete it.
    scheduling_params: ScheduleCreateParams = ScheduleCreateParams(
        admin_key=client.operator_private_key.public_key(),
        expiration_time=expiration,
        wait_for_expiry=True,
    )

    params = TransferHbarParametersNormalised(
        transaction_memo=f"Test Schedule {time.time()}",
        scheduling_params=scheduling_params,
        hbar_transfers={
            client.operator_account_id: -1,
            recipient_id: 1,
        },
    )

    result = await wrapper.transfer_hbar(params)

    if not result.schedule_id:
        raise ValueError(
            "Failed to create scheduled transaction: No Schedule ID returned"
        )

    return str(result.schedule_id)


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
async def test_deletes_a_scheduled_transaction_by_admin(
    agent_executor,
    operator_client,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Standard Case: Direct command to delete.
    """
    _, _, executor_client, executor_wrapper = executor_account

    # 1. Create the schedule
    schedule_id = await create_deletable_scheduled_transaction(
        wrapper=executor_wrapper,
        client=executor_client,
        recipient_id=operator_client.operator_account_id,
    )

    # 2. Act: Direct command
    input_text = f"Delete scheduled transaction {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    # 3. Assert
    human_message = extract_tool_human_message(
        result, response_parser, "schedule_delete_tool"
    )
    assert "successfully deleted" in human_message.lower()


@pytest.mark.asyncio
async def test_deletes_schedule_with_natural_language_cancel_request(
    agent_executor,
    operator_client,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Variation 1: Using "cancel" and polite natural language.
    """
    _, _, executor_client, executor_wrapper = executor_account

    schedule_id = await create_deletable_scheduled_transaction(
        wrapper=executor_wrapper,
        client=executor_client,
        recipient_id=operator_client.operator_account_id,
    )

    # Act: Using "cancel" instead of "delete"
    input_text = f"I made a mistake. Can you please cancel the schedule {schedule_id}?"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "schedule_delete_tool"
    )
    assert "successfully deleted" in human_message.lower()


@pytest.mark.asyncio
async def test_deletes_schedule_with_remove_command(
    agent_executor,
    operator_client,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Variation 2: Using "remove" and implying urgency.
    """
    _, _, executor_client, executor_wrapper = executor_account

    schedule_id = await create_deletable_scheduled_transaction(
        wrapper=executor_wrapper,
        client=executor_client,
        recipient_id=operator_client.operator_account_id,
    )

    # Act: Using "remove"
    input_text = f"Remove schedule {schedule_id} immediately."
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "schedule_delete_tool"
    )
    assert "successfully deleted" in human_message.lower()


@pytest.mark.asyncio
async def test_fails_gracefully_with_non_existent_schedule_id(
    agent_executor,
    langchain_config,
    response_parser,
):
    """
    Negative Case: Attempting to delete a schedule that does not exist.
    """
    # A formatted but non-existent ID
    fake_schedule_id = "0.0.999999999"

    input_text = f"Delete schedule {fake_schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, "schedule_delete_tool"
    )

    # We expect the tool to run but return a failure message containing the Hedera error
    assert "failed" in human_message.lower()
    # Check for specific Hedera error codes or descriptions
    assert any(
        err in human_message.upper()
        for err in ["INVALID_SCHEDULE_ID", "RECORD_NOT_FOUND"]
    )
