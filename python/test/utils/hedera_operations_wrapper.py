from __future__ import annotations

from typing import Any, Dict, List, Optional

from hiero_sdk_python import (
    AccountId,
    AccountInfoQuery,
    Client,
    ContractInfoQuery,
    NftId,
    TokenAssociateTransaction,
    TokenId,
    TokenInfoQuery,
    TokenNftInfoQuery,
    TopicId,
    TopicInfoQuery,
    CryptoGetAccountBalanceQuery,
    AccountInfo,
    TokenInfo,
    TokenNftInfo,
    TransactionReceipt,
)
from hiero_sdk_python.account.account_balance import AccountBalance
from hiero_sdk_python.consensus.topic_info import TopicInfo
from hiero_sdk_python.contract.contract_create_transaction import (
    ContractCreateTransaction,
)

from hedera_agent_kit_py.shared.configuration import Context
from hedera_agent_kit_py.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_utils import (
    get_mirrornode_service,
)
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.types import (
    TokenAirdropsResponse,
    TokenAllowanceResponse,
    TokenBalance,
    TopicMessagesResponse,
    TokenBalancesResponse,
)
from hedera_agent_kit_py.shared.models import ExecutedTransactionToolResponse
from hedera_agent_kit_py.shared.parameter_schemas import (
    AirdropFungibleTokenParametersNormalised,
    TransferHbarParametersNormalised,
    SubmitTopicMessageParametersNormalised,
    DeleteTopicParametersNormalised,
    CreateTopicParametersNormalised,
    DeleteAccountParametersNormalised,
    CreateAccountParametersNormalised,
    ApproveHbarAllowanceParametersNormalised,
    ApproveTokenAllowanceParametersNormalised,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenParametersNormalised,
    DeleteTokenParametersNormalised,
    CreateNonFungibleTokenParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
)
from hedera_agent_kit_py.shared.strategies.tx_mode_strategy import (
    ExecuteStrategy,
    RawTransactionResponse,
)
from hedera_agent_kit_py.shared.utils import LedgerId
from . import from_evm_address


class HederaOperationsWrapper:
    """Wrapper around Hedera SDK operations with transaction execution strategies."""

    def __init__(self, client: Client):
        self.client = client
        self.execute_strategy = ExecuteStrategy()
        self.mirrornode = get_mirrornode_service(None, LedgerId.TESTNET)

    # ---------------------------
    # ACCOUNT OPERATIONS
    # ---------------------------
    async def create_account(
        self, params: CreateAccountParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.create_account(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def delete_account(
        self, params: DeleteAccountParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.delete_account(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    # ---------------------------
    # TOKEN OPERATIONS
    # ---------------------------
    async def create_fungible_token(
        self, params: CreateFungibleTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.create_fungible_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def create_non_fungible_token(
        self, params: CreateNonFungibleTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.create_non_fungible_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def delete_token(
        self, params: DeleteTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.delete_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    # ---------------------------
    # TOPIC (CONSENSUS) OPERATIONS
    # ---------------------------
    async def create_topic(
        self, params: CreateTopicParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.create_topic(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def delete_topic(
        self, params: DeleteTopicParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.delete_topic(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def submit_message(
        self, params: SubmitTopicMessageParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.submit_topic_message(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def get_topic_messages(self, topic_id: str) -> TopicMessagesResponse:
        return await self.mirrornode.get_topic_messages(
            {
                "topic_id": topic_id,
                "lowerTimestamp": "",
                "upperTimestamp": "",
                "limit": 100,
            }
        )

    # ---------------------------
    # TRANSFERS & AIRDROPS
    # ---------------------------
    async def transfer_hbar(
        self, params: TransferHbarParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.transfer_hbar(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def airdrop_token(
        self, params: AirdropFungibleTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.airdrop_fungible_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def transfer_fungible(
        self, params: TransferFungibleTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.transfer_fungible_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def associate_token(self, params: Dict[str, str]) -> RawTransactionResponse:
        tx = TokenAssociateTransaction(
            account_id=AccountId.from_string(params["accountId"]),
            token_ids=[TokenId.from_string(params["tokenId"])],
        )
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    # ---------------------------
    # READ-ONLY QUERIES
    # ---------------------------
    def get_account_balances(self, account_id: str) -> AccountBalance:
        query = CryptoGetAccountBalanceQuery().set_account_id(
            AccountId.from_string(account_id)
        )
        return query.execute(self.client)

    def get_account_info(self, account_id: str) -> AccountInfo:
        query = AccountInfoQuery().set_account_id(AccountId.from_string(account_id))
        return query.execute(self.client)

    def get_topic_info(self, topic_id: str) -> TopicInfo:
        query = TopicInfoQuery().set_topic_id(TopicId.from_string(topic_id))
        return query.execute(self.client)

    def get_token_info(self, token_id: str) -> TokenInfo:
        query = TokenInfoQuery().set_token_id(TokenId.from_string(token_id))
        return query.execute(self.client)

    def get_nft_info(self, token_id: str, serial: int) -> TokenNftInfo:
        query = TokenNftInfoQuery(nft_id=NftId(TokenId.from_string(token_id), serial))
        return query.execute(self.client)

    def get_account_token_balances(self, account_id: str) -> List[Dict[str, Any]]:
        balances = self.get_account_balances(account_id)
        tokens_map = getattr(balances, "tokens", {}) or {}
        decimals_map = getattr(balances, "token_decimals", {}) or {}

        return [
            {
                "tokenId": str(tid),
                "balance": int(balance),
                "decimals": int(decimals_map.get(tid, 0)),
            }
            for tid, balance in tokens_map.items()
        ]

    def get_account_token_balance(
        self, account_id: str, token_id: str
    ) -> Dict[str, Any]:
        balances = self.get_account_balances(account_id)
        token_id_obj = TokenId.from_string(token_id)
        balance = (getattr(balances, "tokens", {}) or {}).get(token_id_obj, 0)
        decimals = (getattr(balances, "token_decimals", {}) or {}).get(token_id_obj, 0)
        return {
            "tokenId": str(token_id_obj),
            "balance": int(balance),
            "decimals": int(decimals),
        }

    async def get_account_token_balance_from_mirrornode(
        self, account_id: str, token_id: str
    ) -> TokenBalance:
        token_balances: TokenBalancesResponse = (
            await self.mirrornode.get_account_token_balances(account_id)
        )
        found = next(
            (t for t in token_balances.get("tokens") if t.get("token_id") == token_id),
            None,
        )
        if not found:
            raise ValueError(f"Token balance for tokenId {token_id} not found")
        return found

    def get_account_hbar_balance(self, account_id: str) -> int:
        info = self.get_account_info(account_id)
        balance = getattr(info, "balance", None)
        if hasattr(balance, "to_tinybars"):
            return int(balance.to_tinybars())
        return int(balance or 0)

    # ---------------------------
    # CONTRACTS / EVM
    # ---------------------------
    async def deploy_erc20(self, bytecode: bytes) -> Dict[str, Optional[str]]:
        try:
            tx = ContractCreateTransaction().set_gas(3_000_000).set_bytecode(bytecode)
            receipt: TransactionReceipt = tx.execute(self.client)
            return {
                "contractId": str(getattr(receipt, "contract_id", None)),
                "transactionId": str(getattr(receipt, "transaction_id", None)),
            }
        except Exception as exc:
            print("[HederaOperationsWrapper] Error deploying ERC20:", exc)
            raise

    async def get_contract_info(self, evm_contract_address: str) -> Any:
        # ContractId lack method for creation from EVM address, so we need to create it manually
        # TODO: add issue to SDK repo to add method for creation from EVM address
        query = ContractInfoQuery().set_contract_id(
            from_evm_address(evm_contract_address)
        )
        return query.execute(self.client)

    # ---------------------------
    # AIRDROPS, ALLOWANCES, APPROVALS
    # ---------------------------
    async def get_pending_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        return await self.mirrornode.get_pending_airdrops(account_id)

    async def get_outstanding_airdrops(self, account_id: str) -> TokenAirdropsResponse:
        return await self.mirrornode.get_outstanding_airdrops(account_id)

    async def get_token_allowances(
        self, owner_account_id: str, spender_account_id: str
    ) -> TokenAllowanceResponse:
        return await self.mirrornode.get_token_allowances(
            owner_account_id, spender_account_id
        )

    async def approve_hbar_allowance(
        self, params: ApproveHbarAllowanceParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.approve_hbar_allowance(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def approve_token_allowance(
        self, params: ApproveTokenAllowanceParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.approve_token_allowance(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def approve_nft_allowance(
        self, params: ApproveNftAllowanceParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.approve_nft_allowance(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def mint_nft(
        self, params: MintNonFungibleTokenParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.mint_non_fungible_token(params)
        result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
            tx, self.client, Context()
        )
        return result.raw

    async def get_account_nfts(self, account_id: str) -> Any:
        return await self.mirrornode.get_account_nfts(account_id)

    async def get_scheduled_transaction_details(self, scheduled_tx_id: str) -> Any:
        return await self.mirrornode.get_scheduled_transaction_details(scheduled_tx_id)
