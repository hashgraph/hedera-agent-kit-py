from unittest.mock import MagicMock
import pytest
from hiero_sdk_python import Client

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas.token_schema import (
    TransferNonFungibleTokenParameters,
    NftTransfer,
)


class TestTransferNonFungibleTokenParameterNormalization:
    @pytest.fixture
    def mock_context(self):
        return MagicMock(spec=Context)

    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def mock_source_account_id(self):
        return "0.0.1001"

    def make_params(
        self,
        recipients: list[NftTransfer],
        token_id: str = "0.0.2001",
        source_account_id: str = "0.0.1001",
        memo: str = None,
    ):
        """Helper to construct the input parameters."""
        return TransferNonFungibleTokenParameters(
            source_account_id=source_account_id,
            token_id=token_id,
            recipients=recipients,
            transaction_memo=memo,
        )

    @pytest.mark.asyncio
    async def test_normalises_single_nft_transfer_correctly(
        self, mock_context, mock_client, mock_source_account_id
    ):
        params = self.make_params(
            recipients=[NftTransfer(recipient="0.0.3001", serial_number=1)],
            token_id="0.0.2001",
            source_account_id=mock_source_account_id,
            memo="NFT xfer",
        )

        result = await HederaParameterNormaliser.normalise_transfer_non_fungible_token(
            params, mock_context, mock_client
        )

        # Check that we have transfers grouped by token_id
        assert len(result.nft_transfers) == 1

        # Get the list of transfers for this token
        token_id_key = list(result.nft_transfers.keys())[0]
        transfers = result.nft_transfers[token_id_key]

        assert len(transfers) == 1
        # The result uses NftTransferNormalised objects
        assert str(transfers[0].receiver_id) == "0.0.3001"
        assert transfers[0].serial_number == 1
        assert str(transfers[0].sender_id) == mock_source_account_id
        assert result.transaction_memo == "NFT xfer"

    @pytest.mark.asyncio
    async def test_handles_multiple_nft_recipients(self, mock_context, mock_client):
        params = self.make_params(
            recipients=[
                NftTransfer(recipient="0.0.3001", serial_number=1),
                NftTransfer(recipient="0.0.3002", serial_number=2),
            ],
        )

        result = await HederaParameterNormaliser.normalise_transfer_non_fungible_token(
            params, mock_context, mock_client
        )

        # Get the transfers for the token
        token_id_key = list(result.nft_transfers.keys())[0]
        transfers = result.nft_transfers[token_id_key]

        assert len(transfers) == 2
        assert transfers[0].serial_number == 1
        assert transfers[1].serial_number == 2
        assert str(transfers[0].receiver_id) == "0.0.3001"
        assert str(transfers[1].receiver_id) == "0.0.3002"

    @pytest.mark.asyncio
    async def test_throws_if_no_recipients_provided(self, mock_context, mock_client):
        with pytest.raises(ValueError, match=r"recipient"):
            # This validation happens at Pydantic level during make_params
            self.make_params(recipients=[])

    @pytest.mark.asyncio
    async def test_throws_if_serial_number_is_zero(self, mock_context, mock_client):
        with pytest.raises(ValueError, match=r"greater than 0|positive"):
            self.make_params(
                recipients=[NftTransfer(recipient="0.0.1002", serial_number=0)],
            )

    @pytest.mark.asyncio
    async def test_throws_if_serial_number_is_negative(self, mock_context, mock_client):
        with pytest.raises(ValueError, match=r"greater than 0|positive"):
            self.make_params(
                recipients=[NftTransfer(recipient="0.0.1002", serial_number=-3)],
            )

    @pytest.mark.asyncio
    async def test_normalises_without_memo(self, mock_context, mock_client):
        params = self.make_params(
            recipients=[NftTransfer(recipient="0.0.3001", serial_number=5)],
        )

        result = await HederaParameterNormaliser.normalise_transfer_non_fungible_token(
            params, mock_context, mock_client
        )

        assert result.transaction_memo is None

    @pytest.mark.asyncio
    async def test_preserves_source_account_id_in_transfers(
        self, mock_context, mock_client
    ):
        source_account = "0.0.9999"
        params = self.make_params(
            recipients=[
                NftTransfer(recipient="0.0.3001", serial_number=10),
                NftTransfer(recipient="0.0.3002", serial_number=11),
            ],
            source_account_id=source_account,
        )

        result = await HederaParameterNormaliser.normalise_transfer_non_fungible_token(
            params, mock_context, mock_client
        )

        token_id_key = list(result.nft_transfers.keys())[0]
        transfers = result.nft_transfers[token_id_key]

        # All transfers should have the same sender (source account)
        for transfer in transfers:
            assert str(transfer.sender_id) == source_account
