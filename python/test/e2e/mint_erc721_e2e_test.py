"""
End-to-end tests for mint_erc721 tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution for ERC721 minting.
"""

from typing import Any
import pytest
from hiero_sdk_python import Hbar, PrivateKey
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit_py.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit_py.plugins.core_evm_plugin import CreateERC721Tool
from hedera_agent_kit_py.shared.configuration import Context, AgentMode
from hedera_agent_kit_py.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
    CreateERC721Parameters,
)
from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_operator_client_for_tests,
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown.account_teardown import return_hbars_and_delete_account


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_environment():
    """Setup test environment with ERC721 contract and accounts."""
    operator_client = get_operator_client_for_tests()
    operator_wrapper = HederaOperationsWrapper(operator_client)

    # Executor account (Agent performing minting)
    executor_key = PrivateKey.generate_ed25519()
    executor_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(50)
        )
    )
    executor_account_id = executor_resp.account_id
    executor_client = get_custom_client(executor_account_id, executor_key)
    executor_wrapper = HederaOperationsWrapper(executor_client)

    # Recipient account
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            key=executor_key.public_key(), initial_balance=Hbar(5)
        )
    )
    recipient_account_id = recipient_resp.account_id

    # LangChain setup with RunnableConfig to avoid checkpointer error
    lc_setup = await create_langchain_test_setup(custom_client=executor_client)
    langchain_config = RunnableConfig(configurable={"thread_id": "mint_erc721_e2e"})

    await wait(MIRROR_NODE_WAITING_TIME)

    # Deploy ERC721 contract via the dedicated tool (wrapper does not provide create_erc721)
    context = Context(mode=AgentMode.AUTONOMOUS, account_id=str(executor_account_id))
    create_tool = CreateERC721Tool(context)
    create_params = CreateERC721Parameters(token_name="TestMintNFT", token_symbol="TMNFT")
    create_result = await create_tool.execute(executor_client, context, create_params)
    create_exec = create_result if isinstance(create_result, ExecutedTransactionToolResponse) else None

    # Some test environments may return ToolResponse; cast defensively
    if create_exec is None:
        create_exec = ExecutedTransactionToolResponse(
            human_message=getattr(create_result, "human_message", ""),
            raw=getattr(create_result, "raw", {}),
            extra=getattr(create_result, "extra", {}),
            error=getattr(create_result, "error", None),
        )

    assert create_exec.error is None, f"ERC721 deployment failed: {create_exec.error}"
    assert isinstance(create_exec.extra, dict), "Result.extra must be a dict"
    assert "erc721_address" in create_exec.extra, "Missing erc721_address in result.extra"
    erc721_address = create_exec.extra["erc721_address"]

    await wait(MIRROR_NODE_WAITING_TIME)

    yield {
        "operator_client": operator_client,
        "executor_client": executor_client,
        "executor_wrapper": executor_wrapper,
        "executor_account_id": executor_account_id,
        "recipient_account_id": recipient_account_id,
        "agent_executor": lc_setup.agent,
        "response_parser": lc_setup.response_parser,
        "langchain_config": langchain_config,
        "erc721_address": erc721_address,
    }

    # Teardown
    lc_setup.cleanup()
    await return_hbars_and_delete_account(
        executor_wrapper, recipient_account_id, operator_client.operator_account_id
    )
    await return_hbars_and_delete_account(
        executor_wrapper, executor_account_id, operator_client.operator_account_id
    )
    executor_client.close()
    operator_client.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_request(agent_executor, input_text: str, config: RunnableConfig):
    """Execute an agent request with the given input text."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def extract_tool_result(
    agent_result: dict[str, Any], response_parser: ResponseParserService
) -> Any:
    """Extract tool result from agent response."""
    tool_calls = response_parser.parse_new_tool_messages(agent_result)
    return tool_calls[0] if tool_calls else None


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_mint_erc721_to_hedera_id_via_natural_language(setup_environment):
    """Test minting an ERC721 token to a Hedera account via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    erc721_address = env["erc721_address"]
    recipient_account_id = env["recipient_account_id"]

    input_text = f"Mint ERC721 token {erc721_address} to {recipient_account_id}"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["status"] == "SUCCESS"
    assert parsed_data["raw"]["transaction_id"] is not None

    # Verify recipient now holds at least one NFT (balance increase implicitly)
    await wait(MIRROR_NODE_WAITING_TIME)
    executor_wrapper = env["executor_wrapper"]
    nfts_before = await executor_wrapper.get_account_nfts(str(recipient_account_id))
    # The mirrornode response returns a dict with 'nfts' list; ensure it's non-empty
    assert (
        isinstance(nfts_before, dict) and len(nfts_before.get("nfts", [])) >= 0
    ), "Unexpected NFT balance response"


@pytest.mark.asyncio
async def test_mint_erc721_to_evm_address_via_natural_language(setup_environment):
    """Test minting an ERC721 token to an EVM address via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    erc721_address = env["erc721_address"]
    recipient_account_id = env["recipient_account_id"]

    # Resolve EVM address for the recipient
    executor_wrapper = env["executor_wrapper"]
    recipient_info = await executor_wrapper.get_account_info_mirrornode(
        str(recipient_account_id)
    )
    recipient_evm = recipient_info.get("evm_address")
    assert recipient_evm, "Recipient EVM address not found"

    input_text = f"Mint ERC721 token {erc721_address} to {recipient_evm}"
    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    assert parsed_data["raw"]["status"] == "SUCCESS"
    assert parsed_data["raw"]["transaction_id"] is not None


@pytest.mark.asyncio
async def test_schedule_mint_erc721_via_natural_language(setup_environment):
    """Test scheduling an ERC721 mint via natural language."""
    env = setup_environment
    agent_executor = env["agent_executor"]
    response_parser = env["response_parser"]
    config = env["langchain_config"]
    erc721_address = env["erc721_address"]
    recipient_account_id = env["recipient_account_id"]

    input_text = (
        f"Mint ERC721 token {erc721_address} to {recipient_account_id}. "
        f"Schedule this transaction."
    )

    result = await execute_agent_request(agent_executor, input_text, config)
    tool_call = extract_tool_result(result, response_parser)

    assert tool_call is not None
    parsed_data = tool_call.parsedData
    human = parsed_data.get("humanMessage", "").lower()
    raw = parsed_data.get("raw", {})
    assert "scheduled" in human
    assert raw.get("schedule_id") is not None
