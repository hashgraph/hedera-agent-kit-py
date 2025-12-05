import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from hiero_sdk_python import Client, AccountId, PrivateKey, PublicKey, TokenId
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit.shared.parameter_schemas import SchedulingParams
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenWithAllowanceParameters,
    TokenTransferEntry,
)
from hedera_agent_kit.shared.utils.account_resolver import AccountResolver


@pytest.fixture
def mock_context():
    return Context(account_id="0.0.1001")


@pytest.fixture
def mock_client():
    client = MagicMock(spec=Client)
    keypair = PrivateKey.generate_ed25519()
    client.operator_private_key = keypair
    client.operator_public_key = keypair.public_key()
    return client


@pytest.fixture
def mock_mirrornode():
    mirrornode = MagicMock(spec=IHederaMirrornodeService)
    mirrornode.get_token_info = AsyncMock(return_value={"decimals": 2})
    return mirrornode


@pytest.mark.asyncio
class TestTransferFungibleTokenWithAllowanceNormalization:
    async def test_normalise_single_transfer(
        self, mock_context, mock_client, mock_mirrornode
    ):
        params = TransferFungibleTokenWithAllowanceParameters(
            token_id="0.0.9999",
            source_account_id="0.0.1001",
            # CHANGE: Using TokenTransferEntry model
            transfers=[TokenTransferEntry(account_id="0.0.2002", amount=100)],
            transaction_memo="Test memo",
        )

        result = await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        mock_mirrornode.get_token_info.assert_called_with("0.0.9999")

        token_id = TokenId.from_string("0.0.9999")
        assert token_id in result.ft_approved_transfer

        transfers = result.ft_approved_transfer[token_id]

        # Recipient credit
        recipient_id = AccountId.from_string("0.0.2002")
        assert transfers[recipient_id] == 100 * 10**2

        # Owner debit
        owner_id = AccountId.from_string("0.0.1001")
        assert transfers[owner_id] == -(100 * 10**2)

        assert result.transaction_memo == "Test memo"
        assert result.scheduling_params is None

    async def test_normalise_multiple_transfers(
        self, mock_context, mock_client, mock_mirrornode
    ):
        params = TransferFungibleTokenWithAllowanceParameters(
            token_id="0.0.9999",
            source_account_id="0.0.1001",
            transfers=[
                TokenTransferEntry(account_id="0.0.2002", amount=50),
                TokenTransferEntry(account_id="0.0.3003", amount=75),
            ],
        )

        result = await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        token_id = TokenId.from_string("0.0.9999")
        transfers = result.ft_approved_transfer[token_id]

        assert transfers[AccountId.from_string("0.0.2002")] == 50 * 10**2
        assert transfers[AccountId.from_string("0.0.3003")] == 75 * 10**2
        assert transfers[AccountId.from_string("0.0.1001")] == -(125 * 10**2)

    @patch.object(AccountResolver, "get_default_public_key")
    async def test_scheduling_params(
        self, mock_resolver, mock_context, mock_client, mock_mirrornode
    ):
        # Mocking the account resolver call that happens inside normalise_scheduled_transaction_params
        mock_resolver.return_value = mock_client.operator_public_key

        params = TransferFungibleTokenWithAllowanceParameters(
            token_id="0.0.9999",
            source_account_id="0.0.1001",
            transfers=[TokenTransferEntry(account_id="0.0.2002", amount=50)],
            scheduling_params=SchedulingParams(
                is_scheduled=True, wait_for_expiry=False
            ),
        )

        result = await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
            params, mock_context, mock_client, mock_mirrornode
        )

        assert result.scheduling_params is not None
        assert result.scheduling_params.wait_for_expiry is False

    async def test_invalid_amount(self, mock_context, mock_client, mock_mirrornode):

        params = TransferFungibleTokenWithAllowanceParameters.model_construct(
            token_id="0.0.9999",
            source_account_id="0.0.1001",
            transfers=[
                TokenTransferEntry.model_construct(account_id="0.0.2002", amount=-50)
            ],
        )

        with pytest.raises(ValueError, match="Invalid transfer amount"):
            await HederaParameterNormaliser.normalise_transfer_fungible_token_with_allowance(
                params, mock_context, mock_client, mock_mirrornode
            )
