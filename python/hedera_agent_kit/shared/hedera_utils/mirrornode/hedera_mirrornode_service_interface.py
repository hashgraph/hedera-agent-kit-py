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
    """Interface for interacting with Hedera Mirror Node services."""

    @abstractmethod
    async def get_account(self, account_id: str) -> AccountResponse:
        """
        Retrieve account details by account ID.

        Args:
            account_id (str): The Hedera account ID.

        Returns:
            AccountResponse: Dictionary containing account ID, public key, balance, and EVM address.

        Raises:
            ValueError: If the account or its key cannot be found.
        """
        pass

    @abstractmethod
    async def get_account_hbar_balance(self, account_id: str) -> Decimal:
        """
        Retrieve the HBAR balance for a given account.

        Args:
            account_id (str): The Hedera account ID.

        Returns:
            Decimal: The HBAR balance of the account.
        """
        pass

    @abstractmethod
    async def get_account_token_balances(
        self, account_id: str, token_id: Optional[str] = None
    ) -> TokenBalancesResponse:
        """
        Retrieve token balances for a given account. If token ID is not provided, retrieves all token balances.

        Args:
            account_id (str): The Hedera account ID.
            token_id: (Optional[str]): The token ID. If provided, retrieves the balance for that specific token.

        Returns:
            TokenBalancesResponse: Dictionary containing the token balances for the account.
        """
        pass

    @abstractmethod
    async def get_topic_messages(
        self, query_params: TopicMessagesQueryParams
    ) -> TopicMessagesResponse:
        """
        Retrieve messages from a given topic, optionally filtered by timestamp and limit.

        Args:
            query_params (TopicMessagesQueryParams): Query parameters including topic ID, lower and upper timestamps, and limit.

        Returns:
            TopicMessagesResponse: Dictionary containing topic ID and list of messages.
        """
        pass

    @abstractmethod
    async def get_topic_info(self, topic_id: str) -> TopicInfo:
        """
        Retrieve information about a specific topic.

        Args:
            topic_id (str): The topic ID.

        Returns:
            TopicInfo: Dictionary containing topic information.
        """
        pass

    @abstractmethod
    async def get_token_info(self, token_id: str) -> TokenInfo:
        """
        Retrieve detailed information about a token.

        Args:
            token_id (str): The token ID.

        Returns:
            TokenInfo: Dictionary containing token details.
        """
        pass

    @abstractmethod
    async def get_contract_info(self, contract_id: str) -> ContractInfo:
        """
        Retrieve information about a smart contract.

        Args:
            contract_id (str): The contract ID.

        Returns:
            ContractInfo: Dictionary containing contract details.
        """
        pass

    @abstractmethod
    async def get_transaction_record(
        self, transaction_id: str, nonce: Optional[int] = None
    ) -> TransactionDetailsResponse:
        """
        Retrieve the details of a specific transaction.

        Args:
            transaction_id (str): The transaction ID.
            nonce (Optional[int]): Optional nonce to disambiguate multiple transactions with the same ID.

        Returns:
            TransactionDetailsResponse: Dictionary containing transaction details.
        """
        pass

    @abstractmethod
    async def get_exchange_rate(
        self, timestamp: Optional[str] = None
    ) -> ExchangeRateResponse:
        """
        Retrieve the network exchange rate at a specific time.

        Args:
            timestamp (Optional[str]): Optional timestamp to query the exchange rate for.

        Returns:
            ExchangeRateResponse: Dictionary containing current or historical exchange rate data.
        """
        pass

    @abstractmethod
    async def get_pending_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        """
        Retrieve pending token airdrops for a given account.

        Args:
            account_id (str): The Hedera account ID.

        Returns:
            TokenAirdropsResponse: Dictionary containing pending airdrops.
        """
        pass

    @abstractmethod
    async def get_outstanding_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        """
        Retrieve outstanding token airdrops for a given account.

        Args:
            account_id (str): The Hedera account ID.

        Returns:
            TokenAirdropsResponse: Dictionary containing outstanding airdrops.
        """
        pass

    @abstractmethod
    async def get_token_allowances(
        self, owner_account_id: str, spender_account_id: str
    ) -> TokenAllowanceResponse:
        """
        Retrieve token allowances given by an owner to a spender.

        Args:
            owner_account_id (str): The account ID of the token owner.
            spender_account_id (str): The account ID of the spender.

        Returns:
            TokenAllowanceResponse: Dictionary containing token allowances.
        """
        pass

    @abstractmethod
    async def get_account_nfts(self, account_id: str) -> NftBalanceResponse:
        """
        Retrieve NFTs owned by a given account.

        Args:
            account_id (str): The Hedera account ID.

        Returns:
            NftBalanceResponse: Dictionary containing NFT balances.
        """
        pass

    @abstractmethod
    async def get_scheduled_transaction_details(
        self, schedule_id: str
    ) -> ScheduledTransactionDetailsResponse:
        """
        Retrieve details of a scheduled transaction.

        Args:
            schedule_id (str): The schedule ID.

        Returns:
            ScheduledTransactionDetailsResponse: Dictionary containing scheduled transaction details.
        """
        pass
