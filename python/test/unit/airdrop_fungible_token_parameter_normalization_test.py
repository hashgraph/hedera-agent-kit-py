import pytest
from unittest.mock import AsyncMock, MagicMock
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.parameter_schemas import (
    AirdropFungibleTokenParameters,
    AirdropRecipient,
)


@pytest.mark.asyncio
class TestAirdropFungibleTokenNormalisation:
    async def test_normalise_recipients_correctly(self):
        mock_context = MagicMock()
        mock_client = MagicMock()
        mock_mirror_node = AsyncMock()
        mock_mirror_node.get_token_info.return_value = {"decimals": "2"}

        params: AirdropFungibleTokenParameters = AirdropFungibleTokenParameters(
            token_id="0.0.2001",
            source_account_id="0.0.1001",
            recipients=[
                AirdropRecipient(account_id="0.0.3001", amount=5),
                AirdropRecipient(account_id="0.0.3002", amount=10),
            ],
        )

        result = (
            await HederaParameterNormaliser.normalise_airdrop_fungible_token_params(
                params,
                mock_context,
                mock_client,
                mock_mirror_node,
            )
        )

        assert len(result.token_transfers) == 3
        # Check amounts (converted to base units)
        # 5 * 10^2 = 500
        assert result.token_transfers[0].amount == 500
        # 10 * 10^2 = 1000
        assert result.token_transfers[1].amount == 1000
        # Total negated: -(500 + 1000) = -1500
        assert result.token_transfers[2].amount == -1500

    async def test_throw_error_if_recipient_amount_is_invalid(self):
        mock_context = MagicMock()
        mock_client = MagicMock()
        mock_mirror_node = AsyncMock()
        mock_mirror_node.get_token_info.return_value = {"decimals": "2"}

        params: AirdropFungibleTokenParameters = AirdropFungibleTokenParameters(
            token_id="0.0.2001",
            source_account_id="0.0.1001",
            recipients=[AirdropRecipient(account_id="0.0.3001", amount=0)],
        )

        with pytest.raises(ValueError, match="Invalid recipient amount: 0"):
            await HederaParameterNormaliser.normalise_airdrop_fungible_token_params(
                params,
                mock_context,
                mock_client,
                mock_mirror_node,
            )
