"""End-to-end tests for transfer HBAR with allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    HbarAllowance,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    ApproveHbarAllowanceParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_OWNER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))
DEFAULT_SPENDER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create Owner, Spender, and Receiver accounts (Module Scoped)."""
    # 1. Create Owner
    owner_key = PrivateKey.generate_ed25519()
    resp_owner = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_OWNER_BALANCE,
            key=owner_key.public_key(),
        )
    )
    owner_id = resp_owner.account_id
    owner_client = get_custom_client(owner_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # 2. Create Spender (Agent)
    spender_key = PrivateKey.generate_ed25519()
    resp_spender = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_SPENDER_BALANCE,
            key=spender_key.public_key(),
        )
    )
    spender_id = resp_spender.account_id
    spender_client = get_custom_client(spender_id, spender_key)
    spender_wrapper = HederaOperationsWrapper(spender_client)

    # 3. Create Receiver
    receiver_key = PrivateKey.generate_ed25519()
    resp_receiver = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(2),
            key=receiver_key.public_key(),
        )
    )
    receiver_id = resp_receiver.account_id
    receiver_client = get_custom_client(receiver_id, receiver_key)
    receiver_wrapper = HederaOperationsWrapper(receiver_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Setup LangChain for Spender
    setup = await create_langchain_test_setup(custom_client=spender_client)

    resources = {
        "owner_id": owner_id,
        "owner_key": owner_key,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "spender_id": spender_id,
        "spender_key": spender_key,
        "spender_client": spender_client,
        "spender_wrapper": spender_wrapper,
        "receiver_id": receiver_id,
        "receiver_key": receiver_key,
        "receiver_client": receiver_client,
        "receiver_wrapper": receiver_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    # Cleanup accounts
    # Spender first (Agent)
    await return_hbars_and_delete_account(
        spender_wrapper, spender_id, operator_client.operator_account_id
    )
    spender_client.close()

    # Owner next
    await return_hbars_and_delete_account(
        owner_wrapper, owner_id, operator_client.operator_account_id
    )
    owner_client.close()

    # Receiver last
    await return_hbars_and_delete_account(
        receiver_wrapper, receiver_id, operator_client.operator_account_id
    )
    receiver_client.close()


@pytest.fixture(scope="module")
def owner_account(setup_module_resources):
    res = setup_module_resources
    return res["owner_id"], res["owner_key"], res["owner_client"], res["owner_wrapper"]


@pytest.fixture(scope="module")
def spender_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["spender_id"],
        res["spender_key"],
        res["spender_client"],
        res["spender_wrapper"],
    )


@pytest.fixture(scope="module")
def receiver_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["receiver_id"],
        res["receiver_key"],
        res["receiver_client"],
        res["receiver_wrapper"],
    )


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "transfer_allowance_e2e"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def approve_allowance(
    owner_wrapper: HederaOperationsWrapper,
    spender_id: AccountId,
    amount_hbar: float,
):
    """Helper to approve HBAR allowance from Owner to Spender."""
    amount_tinybar = int(Hbar(amount_hbar).to_tinybars())
    allowance_params = ApproveHbarAllowanceParametersNormalised(
        hbar_allowances=[
            HbarAllowance(
                spender_account_id=spender_id,
                amount=amount_tinybar,
            )
        ]
    )
    await owner_wrapper.approve_hbar_allowance(allowance_params)
    await wait(MIRROR_NODE_WAITING_TIME)


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
):
    """Execute a request via the agent and return the response."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    """Helper to extract tool data from response."""
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    if not tool_calls:
        return None
    return tool_calls[0]


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_transfer_hbar_using_allowance(
    agent_executor,
    owner_account,
    spender_account,
    receiver_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test transferring HBAR using allowance via natural language."""
    # 1. Setup
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, _ = spender_account
    receiver_id, _, _, receiver_wrapper = receiver_account

    transfer_amount = 1.0

    # 2. Approve Allowance (Owner -> Spender)
    await approve_allowance(owner_wrapper, spender_id, 5.0)

    # 3. Capture balance before
    balance_before = owner_wrapper.get_account_hbar_balance(str(receiver_id))

    # 4. Agent Execution (Spender executes)
    input_text = f"Transfer {transfer_amount} HBAR from {owner_id} to {receiver_id} using allowance"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    # 5. Verification - Tool Response
    assert tool_call is not None
    assert "successfully transferred" in tool_call.parsedData["humanMessage"]
    assert tool_call.parsedData["raw"]["status"] == "SUCCESS"

    # 6. Verification - On-Chain Balance
    balance_after = owner_wrapper.get_account_hbar_balance(str(receiver_id))
    expected_increase = int(Hbar(transfer_amount).to_tinybars())

    assert balance_after == balance_before + expected_increase


@pytest.mark.asyncio
async def test_transfer_hbar_allowance_with_memo(
    agent_executor,
    owner_account,
    spender_account,
    receiver_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test transferring HBAR with allowance and a specific memo."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, _ = spender_account
    receiver_id, _, _, receiver_wrapper = receiver_account

    transfer_amount = 0.5
    memo = "Allowance-based HBAR transfer test"

    await approve_allowance(owner_wrapper, spender_id, 5.0)

    balance_before = owner_wrapper.get_account_hbar_balance(str(receiver_id))

    input_text = (
        f"Spend allowance from {owner_id} to send {transfer_amount} HBAR "
        f"to {receiver_id} with memo '{memo}'"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    assert "successfully transferred" in tool_call.parsedData["humanMessage"]

    balance_after = owner_wrapper.get_account_hbar_balance(str(receiver_id))
    expected_increase = int(Hbar(transfer_amount).to_tinybars())

    assert balance_after == balance_before + expected_increase


@pytest.mark.asyncio
async def test_transfer_hbar_allowance_tiny_amount(
    agent_executor,
    owner_account,
    spender_account,
    receiver_account,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test transferring a very small amount (1 tinybar) using allowance."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, _ = spender_account
    receiver_id, _, _, receiver_wrapper = receiver_account

    # 0.00000001 HBAR = 1 tinybar
    transfer_amount = 0.00000001

    await approve_allowance(owner_wrapper, spender_id, 1.0)

    balance_before = owner_wrapper.get_account_hbar_balance(str(receiver_id))

    input_text = f"Transfer {transfer_amount:.8f} HBAR from {owner_id} to {receiver_id} using allowance"

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    assert "successfully transferred" in tool_call.parsedData["humanMessage"]

    balance_after = owner_wrapper.get_account_hbar_balance(str(receiver_id))
    # 1 tinybar
    assert balance_after == balance_before + 1


@pytest.mark.asyncio
async def test_transfer_hbar_allowance_multiple_recipients(
    agent_executor,
    owner_account,
    spender_account,
    receiver_account,
    operator_wrapper,
    langchain_config: RunnableConfig,
    response_parser: ResponseParserService,
):
    """Test supporting multiple recipients with allowance in a single request."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, _ = spender_account
    receiver1_id, _, _, receiver1_wrapper = receiver_account

    # Create a second receiver dynamically
    receiver2_key = PrivateKey.generate_ed25519()
    receiver2_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(2), key=receiver2_key.public_key()
        )
    )
    receiver2_id = receiver2_resp.account_id
    receiver2_wrapper = HederaOperationsWrapper(
        get_custom_client(receiver2_id, receiver2_key)
    )

    await approve_allowance(owner_wrapper, spender_id, 5.0)

    amount1 = 0.05
    amount2 = 0.05

    bal1_before = owner_wrapper.get_account_hbar_balance(str(receiver1_id))
    bal2_before = owner_wrapper.get_account_hbar_balance(str(receiver2_id))

    input_text = (
        f"Use allowance from {owner_id} to send {amount1} HBAR to {receiver1_id} "
        f"and {amount2} HBAR to {receiver2_id}"
    )

    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    assert "successfully transferred" in tool_call.parsedData["humanMessage"]

    bal1_after = owner_wrapper.get_account_hbar_balance(str(receiver1_id))
    bal2_after = owner_wrapper.get_account_hbar_balance(str(receiver2_id))

    expected_increase = int(Hbar(amount1).to_tinybars())

    assert bal1_after == bal1_before + expected_increase
    assert bal2_after == bal2_before + expected_increase

    # Cleanup second receiver (the first is handled by fixture)
    await return_hbars_and_delete_account(
        receiver2_wrapper, receiver2_id, operator_wrapper.client.operator_account_id
    )
