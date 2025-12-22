"""End-to-end tests for transfer NFT with an allowance tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution and verification of the allowance usage.
"""

from typing import AsyncGenerator, Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    AccountId,
    Client,
    SupplyType,
    TokenType,
    TokenNftAllowance,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account

# Constants
DEFAULT_OWNER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))
DEFAULT_SPENDER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))
TOOL_NAME = "transfer_non_fungible_token_with_allowance_tool"


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create Owner, Spender, and NFT for tests (Module Scoped)."""
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

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Create NFT (Treasury = Owner)
    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="E2E-NFT",
        token_symbol="ENFT",
        memo="E2E allowance integration",
        token_type=TokenType.NON_FUNGIBLE_UNIQUE,
        supply_type=SupplyType.FINITE,
        max_supply=10,
        treasury_account_id=owner_id,
    )
    create_params = CreateNonFungibleTokenParametersNormalised(
        token_params=nft_params, keys=keys
    )
    token_resp = await owner_wrapper.create_non_fungible_token(create_params)
    nft_token_id = token_resp.token_id

    # Mint NFTs (Mint serial 1)
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=nft_token_id,
            metadata=[
                bytes("ipfs://meta-1.json", "utf-8"),
            ],
        )
    )

    # Associate spender with the NFT token
    await spender_wrapper.associate_token(
        {"accountId": str(spender_id), "tokenId": str(nft_token_id)}
    )

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
        "nft_token_id": nft_token_id,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    # Cleanup accounts
    # Spender first
    await return_hbars_and_delete_account(
        spender_wrapper, spender_id, operator_client.operator_account_id
    )
    spender_client.close()

    # Owner next
    await return_hbars_and_delete_account(
        owner_wrapper, owner_id, operator_client.operator_account_id
    )
    owner_client.close()


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
def test_nft(setup_module_resources):
    return setup_module_resources["nft_token_id"]


@pytest.fixture(scope="module")
def agent_executor(setup_module_resources):
    return setup_module_resources["agent_executor"]


@pytest.fixture(scope="module")
def response_parser(setup_module_resources):
    return setup_module_resources["response_parser"]


@pytest.fixture
def langchain_config():
    """Provide a standard LangChain runnable config (Function Scoped)."""
    return RunnableConfig(configurable={"thread_id": "1"})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
) -> dict[str, Any]:
    """Execute the agent invocation and return the result."""
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def validate_tool_use(
    agent_result: dict[str, Any], response_parser: ResponseParserService, tool_name: str
):
    """Validates that the specific tool was called successfully."""
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")

    # We filter specifically for our tool in case other chain-of-thought tools were used
    target_tool_calls = [
        call for call in parsed_tool_calls if call.toolName == tool_name
    ]

    if not target_tool_calls:
        raise ValueError(f"Tool {tool_name} was not among the called tools.")

    tool_call = target_tool_calls[0]

    # Check if raw status exists and is SUCCESS
    if tool_call.parsedData.get("error"):
        raise ValueError(
            f"Tool execution failed with error: {tool_call.parsedData['error']}"
        )

    raw_data = tool_call.parsedData.get("raw")
    if not raw_data or raw_data.get("status") != "SUCCESS":
        raise ValueError(
            f"Tool execution failed: {tool_call.parsedData.get('humanMessage', 'Unknown error')}"
        )


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_transfer_nft_via_allowance_to_recipient(
    agent_executor,
    owner_account,
    spender_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test transferring NFT via allowance using natural language."""
    owner_id, _, owner_client, owner_wrapper = owner_account
    spender_id, _, _, spender_wrapper = spender_account
    nft_token_id = test_nft
    serial_to_use = 1

    # Approve NFT allowance using SDK
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(
            nft_allowances=[
                TokenNftAllowance(
                    token_id=nft_token_id,
                    spender_account_id=spender_id,
                    serial_numbers=[serial_to_use],
                )
            ]
        )
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # Transfer NFT via allowance using natural language
    input_text = f"Transfer NFT with allowance from {owner_id} to {spender_id} with serial number {serial_to_use} of {nft_token_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    validate_tool_use(result, response_parser, TOOL_NAME)

    # Wait for Mirror Node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify NFT was transferred to spender
    recipient_nfts = await spender_wrapper.get_account_nfts(str(spender_id))

    # Check if the spender now owns the NFT
    found_nft = False
    for nft in recipient_nfts.get("nfts"):
        if nft.get("token_id") == str(nft_token_id) and nft.get("serial_number") == 1:
            found_nft = True
            break

    assert (
        found_nft
    ), f"NFT serial {serial_to_use} not found in spender's account after transfer"
