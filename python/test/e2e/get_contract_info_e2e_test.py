"""End-to-end tests for GetContractInfoQueryTool via the full LLM → tool flow.

This module validates querying contract information through the agent executor
and verifies error handling for invalid identifiers.
"""

from typing import Any, AsyncGenerator

import pytest
from hiero_sdk_python import Hbar, PrivateKey, TopicId

from test.utils.usd_to_hbar_service import UsdToHbarService
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import (
    ResponseParserService,
)
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateERC20Parameters,
    CreateTopicParametersNormalised,
)
from test import HederaOperationsWrapper, wait
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


@pytest.fixture
async def executor_account(operator_wrapper, operator_client):
    """Create a funded executor account and yield its client + wrapper."""
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    yield executor_account_id, executor_key, executor_client, executor_wrapper

    # Cleanup: return balance and delete executor account
    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )


@pytest.fixture(scope="module")
def langchain_setup(setup_environment):
    """Provide LangChain setup from module resources."""
    return setup_environment["langchain_setup"]


@pytest.fixture(scope="module")
def agent_executor(setup_environment):
    """Provide LangChain agent executor."""
    return setup_environment["agent_executor"]


@pytest.fixture(scope="module")
def executor_wrapper(setup_environment):
    """Provide executor wrapper."""
    return setup_environment["executor_wrapper"]


@pytest.fixture(scope="module")
async def setup_environment(operator_client, operator_wrapper):
    """Module-scoped environment setup using session-scoped operator fixtures."""
    # Executor account (Agent performing transfers)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(),
            initial_balance=Hbar(UsdToHbarService.usd_to_hbar(1.75)),
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    params = CreateERC20Parameters(
        token_name="E2EInfoToken",
        token_symbol="EIT",
        decimals=18,
        initial_supply=1000,
    )

    create_result = await executor_wrapper.create_erc20(params)

    erc20_address = create_result.get("erc20_address")
    if not erc20_address:
        raise Exception("Failed to create ERC20 for get_contract_info_e2e tests")

    # Wait for mirror node to index the new contract
    await wait(MIRROR_NODE_WAITING_TIME)

    # Setup LangChain
    from test import create_langchain_test_setup

    setup = await create_langchain_test_setup(custom_client=executor_client)

    yield {
        "erc20_address": erc20_address,
        "executor_account_id": executor_account_id,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    setup.cleanup()

    await return_hbars_and_delete_account(
        executor_wrapper,
        executor_account_id,
        operator_client.operator_account_id,
    )
    executor_client.close()


@pytest.fixture
def langchain_config():
    """Provide standard RunnableConfig."""
    return RunnableConfig(configurable={"thread_id": "contract_info_e2e"})


@pytest.fixture
async def response_parser(langchain_setup):
    """Provide the LangChain response parser."""
    return langchain_setup.response_parser


async def execute_get_contract_info_query(
    agent_executor,
    input_text: str,
    config: RunnableConfig,
    response_parser: ResponseParserService,
) -> dict[str, Any]:
    """Execute contract info query through the agent and return parsed tool data."""
    query_result = await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config=config,
    )

    parsed_tool_calls = response_parser.parse_new_tool_messages(query_result)

    if not parsed_tool_calls:
        raise ValueError("The get_contract_info_query_tool was not called.")
    if len(parsed_tool_calls) > 1:
        raise ValueError("Multiple tool calls were found.")

    tool_call = parsed_tool_calls[0]
    if tool_call.toolName != "get_contract_info_query_tool":
        raise ValueError(
            f"Incorrect tool name. Called {tool_call.toolName} instead of get_contract_info_query_tool"
        )

    return tool_call.parsedData


async def create_test_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> TopicId:
    """Helper function to create a topic for message submission tests.

    Creates a topic with no submit key, so the executor (as creator) can
    submit messages freely.
    """
    resp = await executor_wrapper.create_topic(
        CreateTopicParametersNormalised(submit_key=None)
    )
    assert resp.topic_id is not None
    # Wait for topic creation to propagate to mirror node
    await wait(MIRROR_NODE_WAITING_TIME)
    return resp.topic_id


@pytest.fixture
async def pre_created_topic(
    executor_wrapper: HederaOperationsWrapper,
) -> AsyncGenerator[TopicId, None]:
    """Provides a pre-created topic ID for tests."""
    topic_id = await create_test_topic(executor_wrapper)
    yield topic_id


@pytest.mark.asyncio
async def test_get_contract_info_via_agent_success(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
    setup_environment: str,
):
    """Fetch info for a newly deployed ERC20 contract and verify success content."""
    # Use freshly deployed ERC20 EVM address
    contract_identifier = setup_environment["erc20_address"]

    input_text = f"Get contract info for {contract_identifier}"
    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    assert parsed_data.get("error") in (None, "", False)
    assert "Contract Info Query Result:" in human_message
    # We passed an EVM address; ensure it is reflected in the output
    assert f"- EVM Address: {contract_identifier.lower()}" in human_message


@pytest.mark.asyncio
async def test_get_contract_info_with_topic_id_should_error(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
    pre_created_topic: TopicId,
):
    """Using a Topic ID instead of Contract ID should yield an error from the tool."""
    topic_id = str(pre_created_topic)  # Provided Topic ID; not a contract ID
    input_text = f"Get contract info for {topic_id}"

    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error = parsed_data.get("raw").get("error")
    assert error is not None
    assert "Failed to get contract info" in human_message


@pytest.mark.asyncio
async def test_get_contract_info_with_invalid_id_should_error(
    agent_executor,
    langchain_config,
    response_parser: ResponseParserService,
):
    """Malformed or incorrect contract ID should trigger error handling."""
    invalid_id = "1.2.3.4"  # Deliberately invalid format
    input_text = f"Get contract info for {invalid_id}"

    parsed_data = await execute_get_contract_info_query(
        agent_executor, input_text, langchain_config, response_parser
    )

    human_message = parsed_data.get("humanMessage", "")
    error = parsed_data.get("raw").get("error")
    assert error is not None
    assert "Failed to get contract info" in human_message
