"""End-to-end tests for sign schedule transaction tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution for the sign schedule transaction feature.
"""

import time
import pytest

from hiero_sdk_python import (
    PrivateKey,
    Hbar,
    AccountId,
    Timestamp,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.plugins.core_account_plugin import core_account_plugin_tool_names
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    TransferHbarParametersNormalised,
)
from test import HederaOperationsWrapper
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
)
from test.utils.teardown import return_hbars_and_delete_account


# Constants
SIGN_SCHEDULE_TRANSACTION_TOOL = core_account_plugin_tool_names[
    "SIGN_SCHEDULE_TRANSACTION_TOOL"
]
DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary executor account (Module Scoped)."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_EXECUTOR_BALANCE,
            key=executor_key.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
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
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config."""
    return RunnableConfig(configurable={"thread_id": "sign_schedule_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_signable_scheduled_transaction(
    operator_wrapper: HederaOperationsWrapper,
    executor_account_id: AccountId,
    recipient_id: AccountId,
) -> str:
    """
    Creates a scheduled transaction using the OPERATOR.

    The OPERATOR creates the schedule, but the EXECUTOR is the one whose
    account is being debited. This ensures the executor's signature is
    required and not already present.
    """
    # Calculate expiration time (1 hour from now)
    future_seconds = int(time.time() + 60 * 60)
    expiration = Timestamp(seconds=future_seconds, nanos=0)

    scheduling_params: ScheduleCreateParams = ScheduleCreateParams(
        expiration_time=expiration,
        wait_for_expiry=True,  # Don't execute immediately after signing
    )

    # The scheduled transfer debits the EXECUTOR - so executor's signature is required
    params = TransferHbarParametersNormalised(
        transaction_memo=f"Test Schedule {time.time()}",
        scheduling_params=scheduling_params,
        hbar_transfers={
            executor_account_id: -1,  # Executor is being debited - needs to sign
            recipient_id: 1,
        },
    )

    result = await operator_wrapper.transfer_hbar(params)

    if not result.schedule_id:
        raise ValueError(
            "Failed to create scheduled transaction: No Schedule ID returned"
        )

    return str(result.schedule_id)


def extract_tool_human_message(
    agent_result, response_parser: ResponseParserService, tool_name: str
) -> str:
    """Extract the human message from the tool response."""
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


def extract_tool_parsed_data(
    agent_result, response_parser: ResponseParserService, tool_name: str
) -> dict:
    """Extract the full parsed data from the tool response."""
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found")
    if parsed_tool_calls[0].toolName != tool_name:
        raise ValueError(
            f"Incorrect tool name. Called {parsed_tool_calls[0].toolName} instead of {tool_name}"
        )

    return parsed_tool_calls[0].parsedData


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_signs_scheduled_transaction_via_agent(
    agent_executor,
    operator_client,
    operator_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    E2E Test:
    1. Setup: OPERATOR creates a schedule where EXECUTOR is debited.
    2. Act: Agent (running as Executor) signs the schedule.
    3. Assert: Verify the tool output confirms signing.
    """
    executor_account_id, _, _, _ = executor_account

    # 1. Create the schedule (operator creates, executor needs to sign)
    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper=operator_wrapper,
        executor_account_id=executor_account_id,
        recipient_id=operator_client.operator_account_id,
    )

    # 2. Act: Ask agent (Executor) to sign it
    input_text = f"Sign the scheduled transaction with ID {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    # 3. Assert
    human_message = extract_tool_human_message(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )

    assert "successfully signed" in human_message.lower()
    assert "transaction id" in human_message.lower()


@pytest.mark.asyncio
async def test_signs_schedule_with_natural_language_approve_request(
    agent_executor,
    operator_client,
    operator_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Variation 1: Using "approve" and polite natural language.
    """
    executor_account_id, _, _, _ = executor_account

    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper=operator_wrapper,
        executor_account_id=executor_account_id,
        recipient_id=operator_client.operator_account_id,
    )

    # Act: Using "approve" instead of "sign"
    input_text = f"Please approve and add my signature to the schedule {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )
    assert "successfully signed" in human_message.lower()


@pytest.mark.asyncio
async def test_signs_schedule_with_add_signature_wording(
    agent_executor,
    operator_client,
    operator_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Variation 2: Using "add my signature" wording.
    """
    executor_account_id, _, _, _ = executor_account

    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper=operator_wrapper,
        executor_account_id=executor_account_id,
        recipient_id=operator_client.operator_account_id,
    )

    # Act: Using "add signature" wording
    input_text = (
        f"I want to add my signature to the pending scheduled transaction {schedule_id}"
    )
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )
    assert "successfully signed" in human_message.lower()


@pytest.mark.asyncio
async def test_fails_gracefully_with_non_existent_schedule_id(
    agent_executor,
    langchain_config,
    response_parser,
):
    """
    Negative Case: Attempting to sign a schedule that does not exist.
    """
    # A formatted but non-existent ID
    fake_schedule_id = "0.0.999999999"

    input_text = f"Sign schedule {fake_schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )

    # We expect the tool to run but return a failure message
    assert "failed" in human_message.lower()


@pytest.mark.asyncio
async def test_signs_schedule_with_explicit_schedule_id_wording(
    agent_executor,
    operator_client,
    operator_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Variation 3: Using explicit "schedule ID" in the request.
    """
    executor_account_id, _, _, _ = executor_account

    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper=operator_wrapper,
        executor_account_id=executor_account_id,
        recipient_id=operator_client.operator_account_id,
    )

    input_text = f"Please sign schedule ID {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    human_message = extract_tool_human_message(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )
    assert "successfully signed" in human_message.lower()


@pytest.mark.asyncio
async def test_raw_response_contains_transaction_details(
    agent_executor,
    operator_client,
    operator_wrapper,
    executor_account,
    langchain_config,
    response_parser,
):
    """
    Verify that the raw response contains expected transaction details.
    """
    executor_account_id, _, _, _ = executor_account

    schedule_id = await create_signable_scheduled_transaction(
        operator_wrapper=operator_wrapper,
        executor_account_id=executor_account_id,
        recipient_id=operator_client.operator_account_id,
    )

    input_text = f"Sign the scheduled transaction {schedule_id}"
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=langchain_config,
    )

    parsed_data = extract_tool_parsed_data(
        result, response_parser, SIGN_SCHEDULE_TRANSACTION_TOOL
    )

    # Check human message
    assert "successfully signed" in parsed_data["humanMessage"].lower()

    # Check raw response contains expected fields
    raw_data = parsed_data.get("raw", {})
    assert raw_data.get("transaction_id") is not None
    assert raw_data.get("status") == "SUCCESS"
