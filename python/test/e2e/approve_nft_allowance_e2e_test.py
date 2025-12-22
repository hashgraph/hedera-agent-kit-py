"""End-to-end tests for approve NFT allowance tool.

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
    TokenId,
    TokenType,
    TokenNftInfo,
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
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
    NftApprovedTransferNormalised,
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
DEFAULT_RECIPIENT_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["MINIMAL"]))
TOOL_NAME = "approve_nft_allowance_tool"


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================
# Note: operator_client and operator_wrapper fixtures are provided by conftest.py
#       at session scope for the entire test run.


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create a temporary owner/treasury account (Module Scoped)."""
    owner_key = PrivateKey.generate_ed25519()
    owner_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_OWNER_BALANCE,
            key=owner_key.public_key(),
        )
    )

    owner_account_id: AccountId = owner_resp.account_id
    owner_client: Client = get_custom_client(owner_account_id, owner_key)
    owner_wrapper = HederaOperationsWrapper(owner_client)

    # Setup LangChain once
    setup = await create_langchain_test_setup(custom_client=owner_client)

    resources = {
        "owner_account_id": owner_account_id,
        "owner_key": owner_key,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    await return_hbars_and_delete_account(
        owner_wrapper,
        owner_account_id,
        operator_client.operator_account_id,
    )
    owner_client.close()


@pytest.fixture(scope="module")
def owner_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["owner_account_id"],
        res["owner_key"],
        res["owner_client"],
        res["owner_wrapper"],
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
    return RunnableConfig(configurable={"thread_id": "approve_nft_allowance_e2e"})


@pytest.fixture
async def spender_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary spender account (Function Scoped)."""
    spender_key_pair = PrivateKey.generate_ed25519()
    spender_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_SPENDER_BALANCE,
            key=spender_key_pair.public_key(),
        )
    )

    spender_account_id: AccountId = spender_resp.account_id
    spender_client: Client = get_custom_client(spender_account_id, spender_key_pair)
    spender_wrapper_instance = HederaOperationsWrapper(spender_client)

    yield spender_account_id, spender_key_pair, spender_client, spender_wrapper_instance

    await return_hbars_and_delete_account(
        spender_wrapper_instance,
        spender_account_id,
        operator_client.operator_account_id,
    )
    spender_client.close()


# Recipient account remains function scoped
@pytest.fixture
async def recipient_account(
    operator_wrapper, operator_client
) -> AsyncGenerator[tuple, None]:
    """Create a temporary recipient account (Function Scoped)."""
    recipient_key_pair: PrivateKey = PrivateKey.generate_ed25519()
    recipient_resp = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_RECIPIENT_BALANCE,
            key=recipient_key_pair.public_key(),
        )
    )

    recipient_account_id: AccountId = recipient_resp.account_id
    recipient_client: Client = get_custom_client(
        recipient_account_id, recipient_key_pair
    )

    recipient_wrapper_instance = HederaOperationsWrapper(recipient_client)

    yield (
        recipient_account_id,
        recipient_key_pair,
        recipient_client,
        recipient_wrapper_instance,
    )

    await return_hbars_and_delete_account(
        recipient_wrapper_instance,
        recipient_account_id,
        operator_client.operator_account_id,
    )
    recipient_client.close()


@pytest.fixture
async def test_nft(owner_account, spender_account, recipient_account):
    """Create a test NFT token owned by owner and mint one serial."""
    owner_id, owner_key, owner_client, owner_wrapper = owner_account
    spender_id, _, _, spender_wrapper = spender_account
    recipient_id, _, _, recipient_wrapper = recipient_account

    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="AK-NFT-E2E",
        token_symbol="AKNE",
        memo="Approve NFT allowance E2E",
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

    # Mint at least one NFT serial
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=nft_token_id,
            metadata=[
                bytes("ipfs://meta-1.json", "utf-8"),
            ],
        )
    )

    # Associate spender and recipient with the NFT token
    await spender_wrapper.associate_token(
        {"accountId": str(spender_id), "tokenId": str(nft_token_id)}
    )
    await recipient_wrapper.associate_token(
        {"accountId": str(recipient_id), "tokenId": str(nft_token_id)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    return nft_token_id


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


async def spend_nft_via_allowance(
    owner_id: AccountId,
    recipient_id: AccountId,
    nft_token_id: TokenId,
    serial_number: int,
    spender_wrapper: HederaOperationsWrapper,
):
    """
    Helper to execute a TransferTransaction using the approved NFT allowance.
    This simulates the Spender taking action to transfer the NFT.
    """
    transfer_details = NftApprovedTransferNormalised(
        sender_id=owner_id,
        receiver_id=recipient_id,
        serial_number=serial_number,
        is_approval=True,
    )

    params = TransferNonFungibleTokenWithAllowanceParametersNormalised(
        nft_approved_transfer={nft_token_id: [transfer_details]}
    )

    await spender_wrapper.transfer_non_fungible_token_with_allowance(params)


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_approve_nft_allowance_and_allow_spender_to_transfer_via_approved_transfer(
    agent_executor,
    owner_account,
    spender_account,
    recipient_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test approving NFT allowance and using it to transfer NFT."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, spender_client, spender_wrapper = spender_account
    recipient_id, _, _, recipient_wrapper = recipient_account
    nft_token_id = test_nft
    serial_to_use = 1

    memo = "E2E approve NFT allowance"

    # 1. Agent approves NFT allowance
    input_text = f'Approve NFT allowance for token {nft_token_id} serial {serial_to_use} to spender {spender_id} with memo "{memo}"'
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    validate_tool_use(result, response_parser, TOOL_NAME)

    # Wait for Mirror Node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. Spender uses the allowance to transfer NFT to the recipient
    await spend_nft_via_allowance(
        owner_id, recipient_id, nft_token_id, serial_to_use, spender_wrapper
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Verify NFT ownership moved to recipient
    nft_info: TokenNftInfo = recipient_wrapper.get_nft_info(
        str(nft_token_id), serial_to_use
    )

    # Verify the NFT is now owned by the recipient
    assert nft_info is not None
