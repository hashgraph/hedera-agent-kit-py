import pytest
from hiero_sdk_python import PrivateKey, Hbar

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import (
    BALANCE_TIERS,
    LangchainTestOptions,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.general_utils import wait
from test.utils.setup import get_custom_client
from test.utils.setup.langchain_test_setup import create_langchain_test_setup
from test.utils.setup.client_setup import get_operator_client_for_tests

from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
    DeleteAccountParametersNormalised,
)
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_consensus_plugin,
    core_evm_plugin,
)
from hedera_agent_kit.plugins.core_account_plugin import (
    TRANSFER_HBAR_TOOL,
    CREATE_ACCOUNT_TOOL,
    UPDATE_ACCOUNT_TOOL,
    DELETE_ACCOUNT_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin import CREATE_ERC20_TOOL
from test.utils.hedera_operations_wrapper import HederaOperationsWrapper


@pytest.fixture(scope="module")
async def setup_agent_environment():
    """Setup Hedera environment and agent for hook integration tests."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Create an executor account
    executor_key_pair = PrivateKey.generate_ecdsa()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"])
            ),
            key=executor_key_pair.public_key(),
        )
    )
    executor_account_id = executor_resp.account_id

    executor_client = get_custom_client(executor_account_id, executor_key_pair)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Create a topic to use for auditing
    topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(memo="Audit Trail Topic")
    )
    audit_topic_id = topic_resp.topic_id

    # Initialize the hook
    relevant_tools = [
        TRANSFER_HBAR_TOOL,
        CREATE_ACCOUNT_TOOL,
        UPDATE_ACCOUNT_TOOL,
        DELETE_ACCOUNT_TOOL,
        CREATE_ERC20_TOOL,
    ]
    audit_hook = HcsAuditTrailHook(
        relevant_tools=relevant_tools,
        hcs_topic_id=str(audit_topic_id),
        logging_client=executor_client,
    )

    # Initialize agent setup
    toolkit_options = LangchainTestOptions(
        tools=relevant_tools,
        plugins=[core_account_plugin, core_consensus_plugin, core_evm_plugin],
        agent_mode=AgentMode.AUTONOMOUS,
        hooks=[audit_hook],
    )

    # LangchainTestSetup takes care of creating toolkit and agent
    test_setup = await create_langchain_test_setup(
        toolkit_options=toolkit_options, custom_client=executor_client
    )

    yield {
        "test_setup": test_setup,
        "executor_wrapper": executor_wrapper,
        "audit_topic_id": audit_topic_id,
        "executor_account_id": executor_account_id,
        "operator_id": operator_client.operator_account_id,
    }

    # Cleanup: Delete the account
    try:
        await executor_wrapper.delete_account(
            DeleteAccountParametersNormalised(
                account_id=executor_account_id,
                transfer_account_id=operator_client.operator_account_id,
            )
        )
    finally:
        operator_client.close()


@pytest.mark.asyncio
async def test_hcs_audit_trail_hook_integration_agent(setup_agent_environment):
    """Test that HcsAuditTrailHook successfully logs tool execution to HCS via LangChain agent."""
    test_setup = setup_agent_environment["test_setup"]
    wrapper: HederaOperationsWrapper = setup_agent_environment["executor_wrapper"]
    audit_topic_id = setup_agent_environment["audit_topic_id"]
    recipient_id = str(setup_agent_environment["operator_id"])

    print(f"Audit topic ID: {audit_topic_id}")

    agent = test_setup.agent
    amount = 0.0001
    prompt = f"Transfer {amount} HBAR to {recipient_id}"

    # 1. Invoke the agent
    await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        },
        config={"configurable": {"thread_id": "1"}},
    )

    # 2. Wait for mirror node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify audit log
    messages_resp = await wrapper.get_topic_messages(str(audit_topic_id))
    messages = messages_resp.get("messages", [])

    assert len(messages) > 0, "No audit messages found in topic"

    found_audit_log = False
    for msg in messages:
        # Message is base64 encoded by Mirror Node API, but the mirrornode service decodes it for us
        decoded_msg = msg["message"]
        print(f"Audit log: {decoded_msg}")
        if (
            f"Agent executed tool {TRANSFER_HBAR_TOOL}" in decoded_msg
            and str(setup_agent_environment["operator_id"].num) in decoded_msg
        ):
            found_audit_log = True
            break

    assert (
        found_audit_log
    ), f"Expected audit log message not found in HCS topic {audit_topic_id}"


@pytest.mark.asyncio
async def test_hcs_audit_trail_hook_create_account(setup_agent_environment):
    """Test that HcsAuditTrailHook logs CreateAccountTool execution."""
    test_setup = setup_agent_environment["test_setup"]
    wrapper: HederaOperationsWrapper = setup_agent_environment["executor_wrapper"]
    audit_topic_id = setup_agent_environment["audit_topic_id"]

    agent = test_setup.agent
    prompt = (
        "Create a new Hedera account with 0.1 HBAR initial balance and memo 'AuditTest'"
    )

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": "2"}},
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    messages_resp = await wrapper.get_topic_messages(str(audit_topic_id))
    messages = messages_resp.get("messages", [])

    found_audit_log = False
    for msg in messages:
        decoded_msg = msg["message"]
        if (
            f"Agent executed tool {CREATE_ACCOUNT_TOOL}" in decoded_msg
            and "AuditTest" in decoded_msg
            and "0.1" in decoded_msg
        ):
            found_audit_log = True
            break

    assert found_audit_log, f"Audit log for {CREATE_ACCOUNT_TOOL} not found"


@pytest.mark.asyncio
async def test_hcs_audit_trail_hook_update_account(setup_agent_environment):
    """Test that HcsAuditTrailHook logs UpdateAccountTool execution."""
    test_setup = setup_agent_environment["test_setup"]
    wrapper: HederaOperationsWrapper = setup_agent_environment["executor_wrapper"]
    audit_topic_id = setup_agent_environment["audit_topic_id"]
    executor_account_id = str(setup_agent_environment["executor_account_id"])

    agent = test_setup.agent
    prompt = f"Update account {executor_account_id} with memo 'UpdatedAuditMemo'"

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": "3"}},
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    messages_resp = await wrapper.get_topic_messages(str(audit_topic_id))
    messages = messages_resp.get("messages", [])

    found_audit_log = False
    for msg in messages:
        decoded_msg = msg["message"]
        if (
            f"Agent executed tool {UPDATE_ACCOUNT_TOOL}" in decoded_msg
            and "UpdatedAuditMemo" in decoded_msg
        ):
            found_audit_log = True
            break

    assert found_audit_log, f"Audit log for {UPDATE_ACCOUNT_TOOL} not found"


@pytest.mark.asyncio
async def test_hcs_audit_trail_hook_create_erc20(setup_agent_environment):
    """Test that HcsAuditTrailHook logs CreateERC20Tool execution."""
    test_setup = setup_agent_environment["test_setup"]
    wrapper: HederaOperationsWrapper = setup_agent_environment["executor_wrapper"]
    audit_topic_id = setup_agent_environment["audit_topic_id"]

    agent = test_setup.agent
    token_name = "AuditToken"
    token_symbol = "AUD"
    prompt = f"Create a new ERC20 token named '{token_name}' with symbol '{token_symbol}' and 1000 initial supply"

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": "4"}},
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    messages_resp = await wrapper.get_topic_messages(str(audit_topic_id))
    messages = messages_resp.get("messages", [])

    found_audit_log = False
    for msg in messages:
        decoded_msg = msg["message"]
        if (
            f"Agent executed tool {CREATE_ERC20_TOOL}" in decoded_msg
            and "function_parameters" in decoded_msg
            and "0x"
            in decoded_msg  # validating if parameters bytes were decoded correctly
        ):
            found_audit_log = True
            break

    assert found_audit_log, f"Audit log for {CREATE_ERC20_TOOL} not found"


@pytest.mark.asyncio
async def test_hcs_audit_trail_hook_delete_account(setup_agent_environment):
    """Test that HcsAuditTrailHook logs DeleteAccountTool execution."""
    test_setup = setup_agent_environment["test_setup"]
    wrapper: HederaOperationsWrapper = setup_agent_environment["executor_wrapper"]
    audit_topic_id = setup_agent_environment["audit_topic_id"]
    executor_client = setup_agent_environment["test_setup"].client

    # Create a temporary account to delete
    temp_resp = await wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=Hbar(0.1),
            key=executor_client.operator_private_key.public_key(),
        )
    )
    temp_account_id = str(temp_resp.account_id)

    agent = test_setup.agent
    prompt = f"Delete account {temp_account_id} and transfer balance to {setup_agent_environment['executor_account_id']}"

    await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": "5"}},
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    messages_resp = await wrapper.get_topic_messages(str(audit_topic_id))
    messages = messages_resp.get("messages", [])

    found_audit_log = False
    for msg in messages:
        decoded_msg = msg["message"]
        if (
            f"Agent executed tool {DELETE_ACCOUNT_TOOL}" in decoded_msg
            and temp_account_id in decoded_msg
        ):
            found_audit_log = True
            break

    assert found_audit_log, f"Audit log for {DELETE_ACCOUNT_TOOL} not found"
