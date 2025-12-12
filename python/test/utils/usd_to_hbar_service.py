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


# =============================================================================
# TEST ACCOUNT FUNDING CONSTANTS (USD)
# All values include a 50% buffer for safety margin
# See OPERATION_FEES.md for individual operation costs
# =============================================================================

# Integration Tests - Direct tool execution (no LLM overhead)
# Typical operations per test: 1-3 transactions
INTEGRATION_ACCOUNT_BASIC_USD = 0.15          # CryptoCreate ($0.05) + buffer operations
INTEGRATION_TOKEN_CREATE_USD = 1.65           # TokenCreate ($1.00) + CryptoCreate ($0.05) + queries
INTEGRATION_NFT_CREATE_USD = 1.68             # TokenCreate ($1.00) + TokenMint NFT ($0.02) + extras
INTEGRATION_TOPIC_USD = 0.075                 # ConsensusCreateTopic ($0.01) + ConsensusSubmit + extras
INTEGRATION_CONTRACT_USD = 1.65               # ContractCreate ($1.00) + ContractCall + extras
INTEGRATION_ALLOWANCE_USD = 0.15              # CryptoApproveAllowance ($0.05) + transfers
INTEGRATION_AIRDROP_USD = 0.30                # TokenAirdrop ($0.10) + setup

# E2E Tests - Full LLM agent flow (multiple operations per test)
# Typical operations: 3-8 transactions including setup/teardown
E2E_ACCOUNT_USD = 0.30                        # CryptoCreate + CryptoDelete + transfers
E2E_TOKEN_CREATE_USD = 2.25                   # TokenCreate + mints + queries + cleanup
E2E_NFT_CREATE_USD = 2.40                     # TokenCreate + TokenMint NFT ($0.02 each) + extras
E2E_TOPIC_USD = 0.15                          # Topic create + submit + delete + queries
E2E_CONTRACT_USD = 3.00                       # ContractCreate + multiple ContractCalls + queries
E2E_TRANSFER_USD = 0.30                       # Multiple transfers + allowances
E2E_AIRDROP_USD = 0.60                        # TokenCreate + TokenAirdrop + recipient accounts

# Module-level fixtures (shared across multiple tests)
MODULE_FIXTURE_USD = 3.00                     # Covers multiple test executions in a module
SESSION_FIXTURE_USD = 5.00                    # Covers entire test session operations

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
