"""End-to-end tests for transfer NFT tool.

This module provides full testing from user-simulated input, through the LLM,
tools up to on-chain execution and verification.
"""

from typing import Any

import pytest
from hiero_sdk_python import (
    Hbar,
    PrivateKey,
    SupplyType,
    TokenType,
)
from datetime import datetime, timedelta
from hiero_sdk_python.tokens.token_create_transaction import TokenKeys, TokenParams
from langchain_core.runnables import RunnableConfig

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.parameter_schemas import (
    CreateAccountParametersNormalised,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    CreateNonFungibleTokenParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
)
from test import HederaOperationsWrapper, wait
from test.utils import create_langchain_test_setup
from test.utils.setup import (
    get_custom_client,
    MIRROR_NODE_WAITING_TIME,
)
from test.utils.teardown import return_hbars_and_delete_account
from test.utils.usd_to_hbar_service import UsdToHbarService

# Constants
DEFAULT_OWNER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))
DEFAULT_RECEIVER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
TOOL_NAME = "transfer_non_fungible_token_tool"


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
async def setup_module_resources(operator_wrapper, operator_client):
    """Create Owner, Receiver, and NFT for tests (Module Scoped)."""
    # 1. Create Owner (Agent)
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

    # 2. Create Receiver
    receiver_key = PrivateKey.generate_ed25519()
    resp_receiver = await operator_wrapper.create_account(
        CreateAccountParametersNormalised(
            initial_balance=DEFAULT_RECEIVER_BALANCE,
            key=receiver_key.public_key(),
        )
    )
    receiver_id = resp_receiver.account_id
    receiver_client = get_custom_client(receiver_id, receiver_key)
    receiver_wrapper = HederaOperationsWrapper(receiver_client)

    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. Create NFT (Treasury = Owner)
    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="E2E-NFT-Direct",
        token_symbol="ENFTD",
        memo="E2E direct transfer integration",
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

    # Mint second NFT (Mint serial 2)
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=nft_token_id,
            metadata=[
                bytes("ipfs://meta-2.json", "utf-8"),
            ],
        )
    )

    # Associate receiver with the NFT token
    await receiver_wrapper.associate_token(
        {"accountId": str(receiver_id), "tokenId": str(nft_token_id)}
    )

    await wait(MIRROR_NODE_WAITING_TIME)

    # 4. Setup LangChain for Owner (Sender)
    setup = await create_langchain_test_setup(custom_client=owner_client)

    resources = {
        "owner_id": owner_id,
        "owner_key": owner_key,
        "owner_client": owner_client,
        "owner_wrapper": owner_wrapper,
        "receiver_id": receiver_id,
        "receiver_key": receiver_key,
        "receiver_client": receiver_client,
        "receiver_wrapper": receiver_wrapper,
        "nft_token_id": nft_token_id,
        "langchain_setup": setup,
        "agent_executor": setup.agent,
        "response_parser": setup.response_parser,
    }

    yield resources

    setup.cleanup()

    # Cleanup accounts
    # Receiver first
    await return_hbars_and_delete_account(
        receiver_wrapper, receiver_id, operator_client.operator_account_id
    )
    receiver_client.close()

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
def receiver_account(setup_module_resources):
    res = setup_module_resources
    return (
        res["receiver_id"],
        res["receiver_key"],
        res["receiver_client"],
        res["receiver_wrapper"],
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

    return tool_call


# ============================================================================
# TEST CASES
# ============================================================================


@pytest.mark.asyncio
async def test_should_transfer_nft_to_recipient(
    agent_executor,
    owner_account,
    receiver_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test transferring NFT using natural language."""
    owner_id, _, _, _ = owner_account
    receiver_id, _, _, receiver_wrapper = receiver_account
    nft_token_id = test_nft
    serial_to_transfer = 1

    # Transfer NFT directly using natural language
    # Assuming the agent acts as the owner
    input_text = f"Transfer NFT {nft_token_id} serial {serial_to_transfer} from {owner_id} to {receiver_id}"
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    validate_tool_use(result, response_parser, TOOL_NAME)

    # Wait for Mirror Node propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # Verify NFT was transferred to the receiver
    recipient_nfts = await receiver_wrapper.get_account_nfts(str(receiver_id))

    # Check if the receiver now owns the NFT
    found_nft = False
    for nft in recipient_nfts.get("nfts"):
        if nft.get("token_id") == str(nft_token_id) and nft.get("serial_number") == 1:
            found_nft = True
            break

    assert (
        found_nft
    ), f"NFT serial {serial_to_transfer} not found in receiver's account after transfer"


@pytest.mark.asyncio
async def test_should_schedule_nft_transfer(
    agent_executor,
    owner_account,
    receiver_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test scheduling an NFT transfer using natural language."""
    owner_id, _, _, _ = owner_account
    receiver_id, _, _, receiver_wrapper = receiver_account
    nft_token_id = test_nft
    serial_to_transfer = 2

    # Schedule transfer of NFT using natural language with unique memo to avoid duplicates
    import uuid

    random_memo = f"Scheduled transfer {uuid.uuid4()}"

    # Use wait_for_expiry to ensure the transaction doesn't execute immediately
    expiry = (datetime.now() + timedelta(minutes=10)).isoformat()

    input_text = (
        f"Transfer NFT {nft_token_id} serial {serial_to_transfer} "
        f"from {owner_id} to {receiver_id} with memo '{random_memo}'. "
        f"wait for the expiration time to pass and set expiration time to '{expiry}'."
    )
    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    print(result)
    # validate_tool_use consumes the message IDs in the parser, so we must capture the result here
    tool_call = validate_tool_use(result, response_parser, TOOL_NAME)

    # We can check if the transaction status is SUCCESS (Schedule Create was successful).
    assert "SUCCESS" in tool_call.parsedData.get("raw", {}).get("status", "")
    # usage of .get("schedule_id") ensures it's a scheduled transaction
    assert tool_call.parsedData.get("raw", {}).get("schedule_id") is not None

    # Verify NFT was NOT transferred to the receiver (because it should be pending due to wait_for_expiry)
    await wait(MIRROR_NODE_WAITING_TIME)
    recipient_nfts = await receiver_wrapper.get_account_nfts(str(receiver_id))

    found_nft = False
    for nft in recipient_nfts.get("nfts"):
        if (
            nft.get("token_id") == str(nft_token_id)
            and nft.get("serial_number") == serial_to_transfer
        ):
            found_nft = True
            break

    assert (
        not found_nft
    ), f"NFT serial {serial_to_transfer} should NOT be in receiver's account yet (schedule pending)"
