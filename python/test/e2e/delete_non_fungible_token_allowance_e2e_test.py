"""End-to-end tests for delete NFT allowance tool."""

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
    TokenNftAllowance,
)

from test.utils.usd_to_hbar_service import UsdToHbarService
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
DEFAULT_OWNER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(10))
DEFAULT_SPENDER_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
DEFAULT_RECIPIENT_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(0.25))
TOOL_NAME_DELETE = "delete_non_fungible_token_allowance_tool"


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
    return RunnableConfig(configurable={"thread_id": "delete_nft_allowance_e2e"})


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
    """Create a test NFT token owned by owner and mint two serials."""
    owner_id, owner_key, owner_client, owner_wrapper = owner_account
    spender_id, _, _, spender_wrapper = spender_account
    recipient_id, _, _, recipient_wrapper = recipient_account

    treasury_public_key = owner_key.public_key()
    keys = TokenKeys(
        supply_key=treasury_public_key,
        admin_key=treasury_public_key,
    )
    nft_params = TokenParams(
        token_name="AK-NFT-Delete-E2E",
        token_symbol="AKNDE",
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

    # Mint 2 serials
    await owner_wrapper.mint_nft(
        MintNonFungibleTokenParametersNormalised(
            token_id=nft_token_id,
            metadata=[
                bytes("ipfs://meta-1.json", "utf-8"),
                bytes("ipfs://meta-2.json", "utf-8"),
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


async def execute_agent_request(
    agent_executor, input_text: str, config: RunnableConfig
) -> dict[str, Any]:
    return await agent_executor.ainvoke(
        {"messages": [{"role": "user", "content": input_text}]}, config=config
    )


def validate_tool_use(
    agent_result: dict[str, Any], response_parser: ResponseParserService, tool_name: str
):
    parsed_tool_calls = response_parser.parse_new_tool_messages(agent_result)

    if not parsed_tool_calls:
        raise ValueError("The tool was not called")

    target_tool_calls = [
        call for call in parsed_tool_calls if call.toolName == tool_name
    ]

    if not target_tool_calls:
        raise ValueError(f"Tool {tool_name} was not among the called tools.")

    tool_call = target_tool_calls[0]

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


async def spend_nft_via_allowance(
    owner_id: AccountId,
    recipient_id: AccountId,
    nft_token_id: TokenId,
    serial_number: int,
    spender_wrapper: HederaOperationsWrapper,
):
    """Attempt to transfer NFT using allowance."""
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


@pytest.mark.asyncio
async def test_should_delete_specific_nft_allowance(
    agent_executor,
    owner_account,
    spender_account,
    recipient_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test deleting allowance for a specific serial number."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, spender_wrapper = spender_account
    recipient_id, _, _, recipient_wrapper = recipient_account
    nft_token_id = test_nft
    serial_to_use = 1

    # 1. SETUP: Manually approve allowance for serial 1
    allowance = TokenNftAllowance(
        token_id=nft_token_id,
        spender_account_id=spender_id,
        serial_numbers=[serial_to_use],
        approved_for_all=False,
    )
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(nft_allowances=[allowance])
    )
    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. ACTION: Agent deletes allowance for serial 1
    input_text = (
        f"Delete NFT allowance for a token {nft_token_id} serial {serial_to_use}."
    )
    result = await execute_agent_request(agent_executor, input_text, langchain_config)
    validate_tool_use(result, response_parser, TOOL_NAME_DELETE)
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. VERIFY: Spender fails to transfer serial 1
    with pytest.raises(Exception) as excinfo:
        await spend_nft_via_allowance(
            owner_id, recipient_id, nft_token_id, serial_to_use, spender_wrapper
        )
    assert "SPENDER_DOES_NOT_HAVE_ALLOWANCE" in str(
        excinfo.value
    ) or "INVALID_ALLOWANCE_OWNER_ID" in str(excinfo.value)


@pytest.mark.asyncio
async def test_should_delete_multiple_serial_nft_allowances(
    agent_executor,
    owner_account,
    spender_account,
    recipient_account,
    test_nft,
    langchain_config,
    response_parser,
):
    """Test deleting allowances for multiple specific serial numbers."""
    owner_id, _, _, owner_wrapper = owner_account
    spender_id, _, _, spender_wrapper = spender_account
    recipient_id, _, _, recipient_wrapper = recipient_account
    nft_token_id = test_nft
    serials_to_use = [1, 2]

    # 1. SETUP: Manually approve allowances for serials 1 and 2
    allowance = TokenNftAllowance(
        token_id=nft_token_id,
        spender_account_id=spender_id,
        serial_numbers=serials_to_use,
        approved_for_all=False,
    )
    await owner_wrapper.approve_nft_allowance(
        ApproveNftAllowanceParametersNormalised(nft_allowances=[allowance])
    )
    await wait(MIRROR_NODE_WAITING_TIME)

    # 2. ACTION: Agent deletes allowance for serials 1 and 2
    input_text = (
        f"Delete NFT allowance for token {nft_token_id} serials {serials_to_use}."
    )
    result = await execute_agent_request(agent_executor, input_text, langchain_config)

    validate_tool_use(result, response_parser, TOOL_NAME_DELETE)

    # Wait for propagation
    await wait(MIRROR_NODE_WAITING_TIME)

    # 3. VERIFICATION: Spender fails to transfer serial 1 (or 2)
    with pytest.raises(Exception) as excinfo:
        await spend_nft_via_allowance(
            owner_id, recipient_id, nft_token_id, 1, spender_wrapper
        )
    assert "SPENDER_DOES_NOT_HAVE_ALLOWANCE" in str(excinfo.value)
