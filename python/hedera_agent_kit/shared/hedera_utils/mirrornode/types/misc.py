from typing import TypedDict, Dict

from hedera_agent_kit.shared.utils.ledger_id import LedgerId


class ExchangeRate(TypedDict):
    hbar_equivalent: int
    cent_equivalent: int
    expiration_time: int


class ExchangeRateResponse(TypedDict):
    current_rate: ExchangeRate
    next_rate: ExchangeRate
    timestamp: str


LedgerIdToBaseUrl: Dict[str, str] = {
    LedgerId.MAINNET.value: "https://mainnet-public.mirrornode.hedera.com/api/v1",
    LedgerId.TESTNET.value: "https://testnet.mirrornode.hedera.com/api/v1",
}
