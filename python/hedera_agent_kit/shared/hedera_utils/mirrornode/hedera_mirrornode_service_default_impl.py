import asyncio
import base64
from decimal import Decimal
from typing import Optional, Any, Dict, List, Coroutine

import aiohttp

from hedera_agent_kit.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode.types import (
    LedgerIdToBaseUrl,
    TopicMessage,
)
from hedera_agent_kit.shared.utils.ledger_id import LedgerId
from .hedera_mirrornode_decoders import decode_messages
from .types import (
    AccountResponse,
    TokenBalancesResponse,
    TopicMessagesQueryParams,
    TopicMessagesResponse,
    TopicInfo,
    TokenInfo,
    TransactionDetailsResponse,
    ContractInfo,
    TokenAirdropsResponse,
    TokenAllowanceResponse,
    NftBalanceResponse,
    ScheduledTransactionDetailsResponse,
    ExchangeRateResponse,
)


class HederaMirrornodeServiceDefaultImpl(IHederaMirrornodeService):
    def __init__(self, ledger_id: LedgerId):
        if str(ledger_id.value) not in LedgerIdToBaseUrl:
            raise ValueError(f"Network type {ledger_id} not supported")
        self.base_url = LedgerIdToBaseUrl[ledger_id.value]

    async def _fetch_json(self, url: str, context: Optional[str] = None) -> Any:
        """Fetch JSON with context-aware error messages."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(
                        f"Failed to fetch {context or 'data'}: HTTP {resp.status} - {text}"
                    )
                try:
                    return await resp.json()
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to parse JSON for {context or 'data'}: {str(e)}. Raw response: {text}"
                    )

    # ------------------------- ACCOUNT ------------------------- #

    async def get_account(self, account_id: str) -> AccountResponse:
        url = f"{self.base_url}/accounts/{account_id}"
        raw_data: Dict[str, Any] = await self._fetch_json(
            url, context=f"account {account_id}"
        )

        if not raw_data.get("account") or "balance" not in raw_data:
            raise ValueError(f"Account {account_id} not found")

        key_info = raw_data.get("key")
        if not key_info or "key" not in key_info:
            raise ValueError(f"Key not found for account {account_id}")

        account_public_key: str = key_info.get("key")
        if not account_public_key:
            raise ValueError(f"Account public key not found for account {account_id}")

        # Get the EVM address from the raw data (returned by Mirror Node API)
        evm_address = raw_data.get("evm_address")
        if not evm_address:
            raise ValueError(f"EVM address not found for account {account_id}")

        return {
            "account_id": raw_data["account"],
            "account_public_key": key_info["key"],
            "balance": raw_data["balance"],
            "evm_address": evm_address,
        }

    async def get_account_hbar_balance(self, account_id: str) -> Decimal:
        account: AccountResponse = await self.get_account(account_id)
        return Decimal(account["balance"]["balance"])

    async def get_account_token_balances(
        self, account_id: str, token_id: Optional[str] = None
    ) -> TokenBalancesResponse:
        token_param: str = f"&token.id={token_id}" if token_id else ""
        url: str = f"{self.base_url}/accounts/{account_id}/tokens?{token_param}"
        res: TokenBalancesResponse = await self._fetch_json(
            url, context=f"token balances for account {account_id}"
        )

        # Fetch token symbols in parallel
        tasks: list[Coroutine[Any, Any, TokenInfo]] = []
        for token in res.get("tokens", []):
            tid = token.get("token_id")
            if tid:
                tasks.append(self.get_token_info(tid))
        token_infos: list[TokenInfo] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        for idx, info in enumerate(token_infos):
            if isinstance(info, dict):
                res["tokens"][idx]["symbol"] = info.get("symbol", "UNKNOWN")
            else:
                res["tokens"][idx]["symbol"] = "UNKNOWN"

        return res

    async def get_account_nfts(self, account_id: str) -> NftBalanceResponse:
        url: str = f"{self.base_url}/accounts/{account_id}/nfts"
        return await self._fetch_json(url, context=f"NFTs for account {account_id}")

    # ------------------------- TOPIC / CONSENSUS ------------------------- #

    async def get_topic_messages(
        self, query_params: TopicMessagesQueryParams
    ) -> TopicMessagesResponse:
        lower: str = (
            f"&timestamp=gte:{query_params.get('lowerTimestamp')}"
            if query_params.get("lowerTimestamp")
            else ""
        )
        upper: str = (
            f"&timestamp=lte:{query_params.get('upperTimestamp')}"
            if query_params.get("upperTimestamp")
            else ""
        )
        
        limit = query_params.get("limit", 100)
        encoding = query_params.get("encoding", "base64")
        # Request at most 100 messages per page (Mirror Node max)
        page_limit = min(limit, 100)
        
        url: str = (
            f"{self.base_url}/topics/{query_params['topic_id']}/messages?{lower}{upper}&order=desc&limit={page_limit}"
        )

        messages: List[TopicMessage] = []
        fetched_pages: int = 0

        while url:
            data: Dict[str, Any] = await self._fetch_json(
                url, context=f"topic messages for {query_params['topic_id']}"
            )
            batch = data.get("messages", [])
            if not batch:
                break
                
            messages.extend(batch)
            
            # effective_limit cancellation
            if len(messages) >= limit:
                break

            fetched_pages += 1
            if fetched_pages >= 100:
                break
            url: str = (
                f"{self.base_url}{data['links']['next']}"
                if data.get("links", {}).get("next")
                else None
            )

        # Decode messages based on encoding parameter
        decoded_messages = decode_messages(messages[:limit])

        return {
            "topic_id": query_params["topic_id"],
            "messages": decoded_messages,
        }

    async def get_topic_info(self, topic_id: str) -> TopicInfo:
        url: str = f"{self.base_url}/topics/{topic_id}"
        return await self._fetch_json(url, context=f"topic info {topic_id}")

    # ------------------------- TOKEN ------------------------- #

    async def get_token_info(self, token_id: str) -> TokenInfo:
        url: str = f"{self.base_url}/tokens/{token_id}"
        return await self._fetch_json(url, context=f"token info {token_id}")

    async def get_pending_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        url: str = f"{self.base_url}/accounts/{account_id}/airdrops/pending"
        return await self._fetch_json(
            url, context=f"pending airdrops for account {account_id}"
        )

    async def get_outstanding_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        url: str = f"{self.base_url}/accounts/{account_id}/airdrops/outstanding"
        return await self._fetch_json(
            url, context=f"outstanding airdrops for account {account_id}"
        )

    async def get_token_allowances(
        self, owner_account_id: str, spender_account_id: str
    ) -> TokenAllowanceResponse:
        url: str = (
            f"{self.base_url}/accounts/{owner_account_id}/allowances/tokens?spender.id={spender_account_id}"
        )
        return await self._fetch_json(
            url,
            context=f"token allowances from {owner_account_id} to {spender_account_id}",
        )

    # ------------------------- TRANSACTION ------------------------- #

    async def get_transaction_record(
        self, transaction_id: str, nonce: Optional[int] = None
    ) -> TransactionDetailsResponse:
        url: str = f"{self.base_url}/transactions/{transaction_id}"
        if nonce is not None:
            url += f"?nonce={nonce}"
        return await self._fetch_json(
            url, context=f"transaction record {transaction_id}"
        )

    async def get_scheduled_transaction_details(
        self, schedule_id: str
    ) -> ScheduledTransactionDetailsResponse:
        url: str = f"{self.base_url}/schedules/{schedule_id}"
        return await self._fetch_json(
            url, context=f"scheduled transaction {schedule_id}"
        )

    async def get_contract_info(self, contract_id: str) -> ContractInfo:
        url: str = f"{self.base_url}/contracts/{contract_id}"
        return await self._fetch_json(url, context=f"contract info {contract_id}")

    # ------------------------- NETWORK / MISC ------------------------- #

    async def get_exchange_rate(
        self, timestamp: Optional[str] = None
    ) -> ExchangeRateResponse:
        ts_param: str = f"?timestamp={timestamp}" if timestamp else ""
        url: str = f"{self.base_url}/network/exchangerate{ts_param}"
        return await self._fetch_json(
            url, context=f"exchange rate{f' at {timestamp}' if timestamp else ''}"
        )
