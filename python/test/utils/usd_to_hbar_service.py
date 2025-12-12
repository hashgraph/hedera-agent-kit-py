"""
This service provides USD to HBAR conversion. This is used for testing to ensure that the fluctuations in the exchange rate
do not affect the test results. The accounts created for tests are funded with HBARs to pay for the transactions.
The transaction costs on Hedera are FIXED in USD, which means that when the price of HBAR changes, the amount of HBARs required to pay for the transaction also changes.
The implication of that is that the tests happen to fail if the price of HBAR changes significantly.
By passing fixed USD amounts and converting them to HBARs, we can ensure that the tests won't be affected by price fluctuations.
"""
from hedera_agent_kit.shared.hedera_utils.mirrornode import HederaMirrornodeServiceDefaultImpl
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import ExchangeRateResponse
from hedera_agent_kit.shared.utils import LedgerId

class UsdToHbarService:
    _exchange_rate = None
    _is_initialized = False

    @classmethod
    async def initialize(cls, fixed_rate: float = None):
        """
        Initializes the service. Fetches the live price.
        """
        cls._exchange_rate = await cls._fetch_live_hbar_price()

        cls._is_initialized = True

    @classmethod
    def usd_to_hbar(cls, usd_amount: float) -> float:
        """Convert USD to HBAR using the stored rate."""
        if not cls._is_initialized or cls._exchange_rate is None:
            raise RuntimeError("UsdToHbarService is not initialized! Ensure the fixture runs before this call.")

        hbar_amount = usd_amount / cls._exchange_rate
        return round(hbar_amount, 8)

    @staticmethod
    async def _fetch_live_hbar_price() -> float:
        """Fetches the current HBAR price in USD from the Hedera mirrornode."""
        try:
            mirrornode = HederaMirrornodeServiceDefaultImpl(LedgerId.TESTNET)
            resp: ExchangeRateResponse = await mirrornode.get_exchange_rate()
            current_rate = resp["current_rate"]
            return current_rate["cent_equivalent"] / current_rate["hbar_equivalent"] / 100
        except Exception as e:
            raise RuntimeError(f"Couldn't fetch current HBAR price from mirrornode: {e}") from e
