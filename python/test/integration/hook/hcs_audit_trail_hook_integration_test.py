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
from hedera_agent_kit.shared.hooks.hcs_audit_trail_hook import HcsAuditTrailHook
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
    DeleteAccountParametersNormalised,
)
from hedera_agent_kit.plugins import core_account_plugin, core_consensus_plugin
from hedera_agent_kit.plugins.core_account_plugin.transfer_hbar import (
    TRANSFER_HBAR_TOOL,
)
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
    audit_hook = HcsAuditTrailHook(
        relevant_tools=[TRANSFER_HBAR_TOOL],
        hcs_topic_id=str(audit_topic_id),
        logging_client=executor_client,
    )

    # Initialize agent setup
    toolkit_options = LangchainTestOptions(
        tools=[TRANSFER_HBAR_TOOL],
        plugins=[core_account_plugin, core_consensus_plugin],
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
