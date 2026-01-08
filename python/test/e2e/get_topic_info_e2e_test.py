"""End-to-end tests for GetTopicInfoQueryTool using pre-created topics.

This module validates querying topic information through the full LLM → tool → mirror node flow.
"""

from typing import Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParametersNormalised,
)
from test import HederaOperationsWrapper, create_langchain_test_setup, wait
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)

from test.utils.teardown import return_hbars_and_delete_account


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a funded executor account and yield resources (Module Scoped)."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(
                UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"])
            ),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Setup LangChain
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

    # Cleanup
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
def executor_wrapper(setup_module_resources):
    return setup_module_resources["executor_wrapper"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide standard RunnableConfig (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "get_topic_info_e2e"})


async def execute_get_topic_info_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute topic info query through the agent and return parsed tool data."""
    query_result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    # Use the new parsing logic
    parsed_tool_calls = response_parser.parse_new_tool_messages(query_result)

    if not parsed_tool_calls:
        raise ValueError("The get_topic_info_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_topic_info_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_topic_info_query_tool"
        )

    return tool_call.parsedData


@pytest.mark.asyncio
async def test_get_topic_info_via_agent(
    operator_client,
    executor_account,
    agent_executor,
    executor_wrapper,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Test fetching topic info through the agent executor."""
    executor_account_id, _, executor_client, _ = executor_account

    # Create topic with admin key set
    admin_key = executor_client.operator_private_key.public_key()
    create_topic_resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(
            submit_key=admin_key,
        )
    )
    topic_id = create_topic_resp.topic_id

    # Submit one message to ensure a topic shows up on the mirror node
    await executor_wrapper.submit_message(
        SubmitTopicMessageParametersNormalised(
            topic_id=topic_id, message="E2E Topic Info Warmup"
        )
    )

    # Wait for mirrornode indexing
    await wait(MIRROR_NODE_WAITING_TIME)

    # Query topic info via agent
    input_text = f"Get topic info for {topic_id}"
    parsed_data = await execute_get_topic_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data["humanMessage"]
    raw_data = parsed_data["raw"]

    assert parsed_data.get("error") is None
    topic_info = raw_data.get("topic_info")
    assert topic_info is not None
    assert topic_info["topic_id"] == str(topic_id)
    assert "Here are the details for topic" in human_message
