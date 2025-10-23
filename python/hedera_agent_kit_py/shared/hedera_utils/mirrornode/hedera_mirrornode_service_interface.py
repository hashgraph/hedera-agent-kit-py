from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from .types import (
    TopicMessagesQueryParams,
    AccountResponse,
    TokenBalancesResponse,
    TopicMessagesResponse,
    TopicInfo,
    TokenInfo,
    TransactionDetailsResponse,
    ContractInfo,
    ExchangeRateResponse,
    TokenAirdropsResponse,
    TokenAllowanceResponse,
    ScheduledTransactionDetailsResponse,
    NftBalanceResponse,
)


class IHederaMirrornodeService(ABC):

    @abstractmethod
    async def get_account(self, account_id: str) -> AccountResponse:
        pass

    @abstractmethod
    async def get_account_hbar_balance(self, account_id: str) -> Decimal:
        pass

    @abstractmethod
    async def get_account_token_balances(
        self, account_id: str
    ) -> TokenBalancesResponse:
        pass

    @abstractmethod
    async def get_topic_messages(
        self, query_params: TopicMessagesQueryParams
    ) -> TopicMessagesResponse:
        pass

    @abstractmethod
    async def get_topic_info(self, topic_id: str) -> TopicInfo:
        pass

    @abstractmethod
    async def get_token_info(self, token_id: str) -> TokenInfo:
        pass

    @abstractmethod
    async def get_contract_info(self, contract_id: str) -> ContractInfo:
        pass

    @abstractmethod
    async def get_transaction_record(
        self, transaction_id: str, nonce: Optional[int] = None
    ) -> TransactionDetailsResponse:
        pass

    @abstractmethod
    async def get_exchange_rate(
        self, timestamp: Optional[str] = None
    ) -> ExchangeRateResponse:
        pass

    @abstractmethod
    async def get_pending_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        pass

    @abstractmethod
    async def get_outstanding_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        pass

    @abstractmethod
    async def get_token_allowances(
        self, owner_account_id: str, spender_account_id: str
    ) -> TokenAllowanceResponse:
        pass

    @abstractmethod
    async def get_account_nfts(self, account_id: str) -> NftBalanceResponse:
        pass

    @abstractmethod
    async def get_scheduled_transaction_details(
        self, schedule_id: str
    ) -> ScheduledTransactionDetailsResponse:
        pass
