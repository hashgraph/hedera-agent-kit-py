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
    TransactionReceipt, TransactionRecordQuery, TransactionId,
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
    NftBalanceResponse, AccountResponse,
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
    CreateERC20Parameters,
    CreateERC721Parameters,
    MintERC721Parameters,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenParametersNormalised,
    DeleteTokenParametersNormalised,
    CreateNonFungibleTokenParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
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

    async def get_account_info_mirrornode(self, account_id: str) -> AccountResponse:
        account_info: AccountResponse = await self.mirrornode.get_account(account_id)
        return account_info


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
        """Deploy an ERC20 contract from bytecode (legacy method).
        
        Args:
            bytecode: The contract bytecode
            
        Returns:
            Dict containing contractId and transactionId
        """
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

    async def create_erc20(
        self, params: CreateERC20Parameters
    ) -> Dict[str, Optional[str]]:
        """Create an ERC20 token using the factory contract.
        
        Args:
            params: ERC20 creation parameters
            
        Returns:
            Dict containing erc20_address, transaction_id, and human_message
        """
        from hedera_agent_kit_py.shared.constants.contracts import (
            get_erc20_factory_address,
            ERC20_FACTORY_ABI,
        )
        from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
            HederaParameterNormaliser,
        )
        from hedera_agent_kit_py.shared.utils import ledger_id_from_network
        
        try:
            factory_address = get_erc20_factory_address(
                ledger_id_from_network(self.client.network)
            )
            
            normalised_params = (
                await HederaParameterNormaliser.normalise_create_erc20_params(
                    params,
                    factory_address,
                    ERC20_FACTORY_ABI,
                    "deployToken",
                    Context(),
                    self.client,
                )
            )
            
            tx = HederaBuilder.execute_transaction(normalised_params)
            result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
                tx, self.client, Context()
            )
            
            # Get ERC20 address from the transaction
            erc20_address = await self._get_erc_address(result.raw.transaction_id)
            
            return {
                "erc20_address": erc20_address,
                "transaction_id": str(result.raw.transaction_id),
                "human_message": f"ERC20 token created successfully at address {erc20_address}",
            }
        except Exception as exc:
            print("[HederaOperationsWrapper] Error creating ERC20:", exc)
            raise

    async def create_erc721(
        self, params: CreateERC721Parameters
    ) -> Dict[str, Optional[str]]:
        """Create an ERC721 token using the factory contract.
        
        Args:
            params: ERC721 creation parameters
            
        Returns:
            Dict containing erc721_address, transaction_id, and human_message
        """
        from hedera_agent_kit_py.shared.constants.contracts import (
            get_erc721_factory_address,
            ERC721_FACTORY_ABI,
        )
        from hedera_agent_kit_py.shared.hedera_utils.hedera_parameter_normalizer import (
            HederaParameterNormaliser,
        )
        from hedera_agent_kit_py.shared.utils import ledger_id_from_network
        
        try:
            factory_address = get_erc721_factory_address(
                ledger_id_from_network(self.client.network)
            )
            
            normalised_params = (
                await HederaParameterNormaliser.normalise_create_erc721_params(
                    params,
                    factory_address,
                    ERC721_FACTORY_ABI,
                    "deployToken",
                    Context(),
                    self.client,
                )
            )
            
            tx = HederaBuilder.execute_transaction(normalised_params)
            result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
                tx, self.client, Context()
            )
            
            # Get ERC721 address from the transaction
            erc721_address = await self._get_erc_address(result.raw.transaction_id)
            
            return {
                "erc721_address": erc721_address,
                "transaction_id": str(result.raw.transaction_id),
                "human_message": f"ERC721 token created successfully at address {erc721_address}",
            }
        except Exception as exc:
            print("[HederaOperationsWrapper] Error creating ERC721:", exc)
            raise

    async def mint_erc721(
        self, params: MintERC721Parameters
    ) -> Dict[str, Optional[str]]:
        """Mint an ERC721 token.
        
        Args:
            params: ERC721 minting parameters
            
        Returns:
            Dict containing transaction_id and human_message
        """
        from hedera_agent_kit_py.shared.constants.contracts import (
            ERC721_MINT_FUNCTION_ABI,
            ERC721_MINT_FUNCTION_NAME,
        )
        from hedera_agent_kit_py.shared.utils import ledger_id_from_network
        from hedera_agent_kit_py.shared.utils.account_resolver import AccountResolver
        from hiero_sdk_python import ContractExecuteTransaction
        from hiero_sdk_python.contract.contract_id import ContractId
        from web3 import Web3
        
        try:
            mirrornode_service = get_mirrornode_service(
                None, ledger_id_from_network(self.client.network)
            )
            
            # Resolve to_address (defaults to operator if not provided)
            to_address_input = params.to_address or str(self.client.operator_account_id)
            to_address = await AccountResolver.get_hedera_evm_address(
                to_address_input, mirrornode_service
            )
            
            # Resolve contract ID
            contract_id_str = await AccountResolver.get_hedera_account_id(
                params.contract_id, mirrornode_service
            )
            contract_id = ContractId.from_string(contract_id_str)
            
            # Encode the mint function call
            w3 = Web3()
            checksummed_to = w3.to_checksum_address(to_address)
            contract = w3.eth.contract(abi=ERC721_MINT_FUNCTION_ABI)
            encoded_data = contract.encode_abi(
                abi_element_identifier=ERC721_MINT_FUNCTION_NAME,
                args=[checksummed_to],
            )
            function_parameters = bytes.fromhex(encoded_data[2:])
            
            # Execute the contract call
            tx = (
                ContractExecuteTransaction()
                .set_contract_id(contract_id)
                .set_gas(100_000)
                .set_function_parameters(function_parameters)
            )
            
            result: ExecutedTransactionToolResponse = await self.execute_strategy.handle(
                tx, self.client, Context()
            )
            
            return {
                "transaction_id": str(result.raw.transaction_id),
                "human_message": "ERC721 token minted successfully",
            }
        except Exception as exc:
            print("[HederaOperationsWrapper] Error minting ERC721:", exc)
            raise

    async def get_erc20_balance(
        self, erc20_contract_address: str, account_address: str
    ) -> int:
        """Get ERC20 token balance for an account by calling balanceOf on the contract.
        
        Args:
            erc20_contract_address: The ERC20 contract address (EVM format like 0x...)
            account_address: The account address to check balance for (Hedera ID like 0.0.123)
            
        Returns:
            int: The token balance (in base units, not adjusted for decimals)
        """
        from hedera_agent_kit_py.shared.constants.contracts import (
            ERC20_BALANCE_OF_FUNCTION_ABI,
            ERC20_BALANCE_OF_FUNCTION_NAME,
        )
        from hiero_sdk_python import ContractCallQuery
        from hiero_sdk_python.contract.contract_id import ContractId
        from web3 import Web3
        
        try:
            # Get EVM address for the account
            account_info = await self.get_account_info_mirrornode(account_address)
            account_evm_address = account_info.get("evm_address")
            
            if not account_evm_address:
                raise ValueError(f"Could not get EVM address for account {account_address}")
            
            # Encode the balanceOf function call
            w3 = Web3()
            checksummed_account = w3.to_checksum_address(account_evm_address)
            contract = w3.eth.contract(abi=ERC20_BALANCE_OF_FUNCTION_ABI)
            encoded_data = contract.encode_abi(
                abi_element_identifier=ERC20_BALANCE_OF_FUNCTION_NAME,
                args=[checksummed_account],
            )
            function_parameters = bytes.fromhex(encoded_data[2:])
            
            # Create ContractId from EVM address
            # Strip 0x prefix and convert to bytes
            addr_hex = erc20_contract_address.lower().replace("0x", "")
            evm_bytes = bytes.fromhex(addr_hex)
            
            if len(evm_bytes) != 20:
                raise ValueError(
                    f"Invalid EVM address length: expected 20 bytes, got {len(evm_bytes)}"
                )
            
            # Create ContractId with only EVM address (shard=0, realm=0, contract=0)
            contract_id = ContractId(
                shard=0, realm=0, contract=0, evm_address=evm_bytes
            )
            
            # Execute a contract call query
            query = (
                ContractCallQuery()
                .set_contract_id(contract_id)
                .set_gas(100_000)
                .set_function_parameters(function_parameters)
            )
            
            result = query.execute(self.client)
            
            # Decode the result - balanceOf returns uint256
            result_bytes = getattr(result, "contract_call_result", None)
            if not result_bytes or len(result_bytes) < 32:
                return 0
            
            # uint256 is encoded as 32 bytes
            balance = int.from_bytes(result_bytes[:32], "big")
            return balance
            
        except Exception as exc:
            print(f"[HederaOperationsWrapper] Error getting ERC20 balance: {exc}")
            raise

    async def _get_erc_address( self, transaction_id: TransactionId
    ) -> str | None:
        """Minimal helper to resolve the deployed ERC721 EVM address via SDK."""

        record = (
            TransactionRecordQuery().set_transaction_id(transaction_id).execute(self.client)
        )

        contract_call_result = getattr(record, "call_result", None)

        if contract_call_result is None:
            return None

        # Access the raw ABI-encoded return bytes from the function result
        result_bytes = getattr(contract_call_result, "contract_call_result", None)

        if not result_bytes or not isinstance(result_bytes, (bytes, bytearray)):
            return None

        # The factory returns an EVM address as the first return value.
        # In Solidity ABI, an address is encoded as a 32-byte word left-padded with zeros.
        # We need to take the last 20 bytes of the first 32-byte word.
        if len(result_bytes) < 32:
            return None

        first_word = bytes(result_bytes[:32])
        addr_last_20 = first_word[-20:]
        evm_addr = "0x" + addr_last_20.hex()
        return evm_addr

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

    async def transfer_non_fungible_token_with_allowance(
        self, params: TransferNonFungibleTokenWithAllowanceParametersNormalised
    ) -> RawTransactionResponse:
        tx = HederaBuilder.transfer_non_fungible_token_with_allowance(params)
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

    async def get_account_nfts(self, account_id: str) -> NftBalanceResponse:
        return await self.mirrornode.get_account_nfts(account_id)

    async def get_scheduled_transaction_details(self, scheduled_tx_id: str) -> Any:
        return await self.mirrornode.get_scheduled_transaction_details(scheduled_tx_id)
