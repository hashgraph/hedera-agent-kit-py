from typing import Optional

from hiero_sdk_python import (
    AccountAllowanceApproveTransaction,
    AccountCreateTransaction,
    AccountDeleteTransaction,
    AccountUpdateTransaction,
    ContractExecuteTransaction,
    ScheduleCreateTransaction,
    ScheduleDeleteTransaction,
    ScheduleSignTransaction,
    TokenAirdropTransaction,
    TokenAssociateTransaction,
    TokenCreateTransaction,
    TokenDeleteTransaction,
    TokenDissociateTransaction,
    TokenMintTransaction,
    TokenUpdateTransaction,
    TopicCreateTransaction,
    TopicDeleteTransaction,
    TopicMessageSubmitTransaction,
    TopicUpdateTransaction,
    TransferTransaction,
    NftId,
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit_py.shared.parameter_schemas import (
    ApproveHbarAllowanceParametersNormalised,
    ApproveNftAllowanceParametersNormalised,
    ApproveTokenAllowanceParametersNormalised,
    AssociateTokenParametersNormalised,
    AirdropFungibleTokenParametersNormalised,
    CreateFungibleTokenParametersNormalised,
    CreateNonFungibleTokenParametersNormalised,
    DeleteAccountParametersNormalised,
    DeleteTopicParametersNormalised,
    DeleteTokenParametersNormalised,
    DissociateTokenParametersNormalised,
    MintFungibleTokenParametersNormalised,
    MintNonFungibleTokenParametersNormalised,
    TransferFungibleTokenWithAllowanceParametersNormalised,
    TransferHbarParametersNormalised,
    TransferHbarWithAllowanceParametersNormalised,
    TransferNonFungibleTokenWithAllowanceParametersNormalised,
    UpdateAccountParametersNormalised,
    UpdateTokenParametersNormalised,
    CreateAccountParametersNormalised,
    CreateTopicParametersNormalised,
    SubmitTopicMessageParametersNormalised,
    UpdateTopicParametersNormalised,
    ContractExecuteTransactionParametersNormalised,
    SignScheduleTransactionParameters,
    ScheduleDeleteTransactionParameters,
)
from hedera_agent_kit_py.shared.parameter_schemas.token_schema import (
    TransferFungibleTokenParametersNormalised,
)


class HederaBuilder:
    """Helper class to build Hedera SDK transactions with optional scheduling support.

    This class provides static methods to construct transactions for accounts, tokens,
    NFTs, topics, HBAR transfers, and contract executions. Methods automatically wrap
    transactions in a ScheduleCreateTransaction if scheduling parameters are provided.
    """

    @staticmethod
    def maybe_wrap_in_schedule(
        tx, scheduling_params: Optional[ScheduleCreateParams] = None
    ) -> ScheduleCreateTransaction:
        """Wrap a transaction in a schedule if scheduling parameters are provided.

        Args:
            tx: The transaction to wrap.
            scheduling_params (Optional[ScheduleCreateParams]): Optional schedule creation parameters.

        Returns:
            Transaction: Either the original transaction or a ScheduleCreateTransaction.
        """
        if scheduling_params is not None:
            return ScheduleCreateTransaction(
                scheduling_params
            ).set_scheduled_transaction(tx)
        return tx

    @staticmethod
    def create_fungible_token(
        params: CreateFungibleTokenParametersNormalised,
    ) -> Transaction:
        """Build a TokenCreateTransaction for a fungible token.

        Args:
            params: Normalised parameters for creating a fungible token.

        Returns:
            Transaction: TokenCreateTransaction, optionally wrapped in a schedule.
        """
        tx: TokenCreateTransaction = TokenCreateTransaction(
            token_params=params.token_params,
            keys=params.keys,
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_non_fungible_token(
        params: CreateNonFungibleTokenParametersNormalised,
    ) -> Transaction:
        """Build a TokenCreateTransaction for a non-fungible token.

        Args:
            params: Normalised parameters for creating a non-fungible token.

        Returns:
            Transaction: TokenCreateTransaction, optionally wrapped in a schedule.
        """
        tx: TokenCreateTransaction = TokenCreateTransaction(
            token_params=params.token_params,
            keys=params.keys,
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar(params: TransferHbarParametersNormalised) -> Transaction:
        """Build a TransferTransaction for transferring HBAR.

        Args:
            params: Normalised HBAR transfer parameters.

        Returns:
            Transaction: TransferTransaction, optionally wrapped in a schedule.
        """

        tx: TransferTransaction = TransferTransaction(
            hbar_transfers=params.hbar_transfers
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar_with_allowance(
        params: TransferHbarWithAllowanceParametersNormalised,
    ) -> TransferTransaction:
        """Build a TransferTransaction using approved HBAR allowances.

        Args:
            params: Normalised HBAR transfer-with-allowance parameters.

        Returns:
            TransferTransaction: Transaction including all approved HBAR transfers.
        """
        tx: TransferTransaction = TransferTransaction()
        for owner_account_id, amount in params.hbar_approved_transfers.items():
            tx.add_approved_hbar_transfer(owner_account_id, amount)

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def transfer_non_fungible_token_with_allowance(
        params: TransferNonFungibleTokenWithAllowanceParametersNormalised,
    ) -> Transaction:
        """Build a TransferTransaction for NFTs using approved allowances.

        Args:
            params: Normalised NFT transfer-with-allowance parameters.

        Returns:
            Transaction: TransferTransaction including all approved NFT transfers,
            optionally wrapped in a schedule.
        """
        tx: TransferTransaction = TransferTransaction()

        for token_id, transfers in params.nft_approved_transfer.items():
            for sender_id, receiver_id, serial_number, _is_approved in transfers:
                nft_id: NftId = NftId(token_id, serial_number)
                tx.add_approved_nft_transfer(nft_id, sender_id, receiver_id)

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)

        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_fungible_token_with_allowance(
        params: TransferFungibleTokenWithAllowanceParametersNormalised,
    ) -> Transaction:
        """Build a TransferTransaction for fungible tokens using approved allowances.

        Args:
            params: Normalised fungible token transfer-with-allowance parameters.

        Returns:
            Transaction: TransferTransaction including all approved token transfers,
            optionally wrapped in a schedule.
        """
        tx: TransferTransaction = TransferTransaction()

        for token_id, transfers in params.ft_approved_transfer.items():
            for account_id, amount in transfers.items():
                tx.add_approved_token_transfer(token_id, account_id, amount)

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)

        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_fungible_token(
        params: TransferFungibleTokenParametersNormalised,
    ):
        tx = TransferTransaction()

        for token_id, transfers in params.ft_transfers.items():
            for account_id, amount in transfers.items():
                tx.add_token_transfer(token_id, account_id, amount)

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)

        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def airdrop_fungible_token(
        params: AirdropFungibleTokenParametersNormalised,
    ) -> TokenAirdropTransaction:
        """Build a TokenAirdropTransaction for fungible tokens.

        Args:
            params: Normalised airdrop parameters.

        Returns:
            TokenAirdropTransaction: Transaction ready for submission.
        """
        return TokenAirdropTransaction(**vars(params))

    @staticmethod
    def update_token(params: UpdateTokenParametersNormalised) -> TokenUpdateTransaction:
        """Build a TokenUpdateTransaction.

        Args:
            params: Normalised token update parameters.

        Returns:
            TokenUpdateTransaction: Transaction ready for submission.
        """
        return TokenUpdateTransaction(**vars(params))

    @staticmethod
    def mint_fungible_token(
        params: MintFungibleTokenParametersNormalised,
    ) -> Transaction:
        """Build a TokenMintTransaction for fungible tokens.

        Args:
            params: Normalised mint parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: TokenMintTransaction = TokenMintTransaction(
            token_id=params.token_id, amount=params.amount
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def mint_non_fungible_token(
        params: MintNonFungibleTokenParametersNormalised,
    ) -> Transaction:
        """Build a TokenMintTransaction for non-fungible tokens.

        Args:
            params: Normalised mint parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: TokenMintTransaction = TokenMintTransaction(
            token_id=params.token_id, metadata=params.metadata
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def dissociate_token(
        params: DissociateTokenParametersNormalised,
    ):
        """Build a TokenDissociateTransaction.

        Args:
            params: Normalised dissociate token parameters.

        Returns:
            TokenDissociateTransaction: Transaction ready for submission.
        """
        tx = TokenDissociateTransaction(
            account_id=params.account_id, token_ids=params.token_ids
        )

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)

        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_account(params: CreateAccountParametersNormalised) -> Transaction:
        """Build an AccountCreateTransaction.

        Args:
            params: Normalised account creation parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: AccountCreateTransaction = AccountCreateTransaction(
            key=params.key,
            initial_balance=params.initial_balance,
            memo=params.memo,
            # max_automatic_token_associations=params.max_automatic_token_associations, FIXME: add this back when SDK supports it
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_account(
        params: DeleteAccountParametersNormalised,
    ) -> AccountDeleteTransaction:
        """Build an AccountDeleteTransaction.

        Args:
            params: Normalised account deletion parameters.

        Returns:
            AccountDeleteTransaction: Transaction ready for submission.
        """
        return AccountDeleteTransaction(**vars(params))

    @staticmethod
    def update_account(params: UpdateAccountParametersNormalised) -> Transaction:
        """Build an AccountUpdateTransaction.

        Args:
            params: Normalised account update parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: AccountUpdateTransaction = AccountUpdateTransaction(params.account_params)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_token(params: DeleteTokenParametersNormalised) -> TokenDeleteTransaction:
        """Build a TokenDeleteTransaction.

        Args:
            params: Normalised token deletion parameters.

        Returns:
            TokenDeleteTransaction: Transaction ready for submission.
        """
        return TokenDeleteTransaction(**vars(params))

    @staticmethod
    def delete_topic(params: DeleteTopicParametersNormalised) -> TopicDeleteTransaction:
        """Build a TopicDeleteTransaction.

        Args:
            params: Normalised topic deletion parameters.

        Returns:
            TopicDeleteTransaction: Transaction ready for submission.
        """
        return TopicDeleteTransaction(**vars(params))

    @staticmethod
    def sign_schedule_transaction(
        params: SignScheduleTransactionParameters,
    ) -> ScheduleSignTransaction:
        """Build a ScheduleSignTransaction.

        Args:
            params: Normalised schedule signing parameters.

        Returns:
            ScheduleSignTransaction: Transaction ready for submission.
        """
        return ScheduleSignTransaction(**vars(params))

    @staticmethod
    def delete_schedule_transaction(
        params: ScheduleDeleteTransactionParameters,
    ) -> ScheduleDeleteTransaction:
        """Build a ScheduleDeleteTransaction.

        Args:
            params: Normalised schedule deletion parameters.

        Returns:
            ScheduleDeleteTransaction: Transaction ready for submission.
        """
        return ScheduleDeleteTransaction(**vars(params))

    @staticmethod
    def associate_token(
        params: AssociateTokenParametersNormalised,
    ) -> TokenAssociateTransaction:
        """Build a TokenAssociateTransaction.

        Args:
            params: Normalised token association parameters.

        Returns:
            TokenAssociateTransaction: Transaction ready for submission.
        """
        return TokenAssociateTransaction(**vars(params))

    @staticmethod
    def _build_account_allowance_approve_tx(
        params,
    ) -> AccountAllowanceApproveTransaction:
        """Helper to build an AccountAllowanceApproveTransaction with optional memo."""

        tx = AccountAllowanceApproveTransaction(
            hbar_allowances=getattr(params, "hbar_allowances", None),
            token_allowances=getattr(params, "token_allowances", None),
            nft_allowances=getattr(params, "nft_allowances", None),
        )

        # Check for memo (getattr handles the missing check here too)
        memo = getattr(params, "transaction_memo", None)
        if memo:
            tx.set_transaction_memo(memo)

        return tx

    @staticmethod
    def approve_hbar_allowance(
        params: ApproveHbarAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        """Build an HBAR allowance approval transaction."""
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_nft_allowance(
        params: ApproveNftAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        """Build an NFT allowance approval transaction."""
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_token_allowance(
        params: ApproveTokenAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        """Build a fungible token allowance approval transaction."""
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def execute_transaction(
        params: ContractExecuteTransactionParametersNormalised,
    ) -> Transaction:
        """Build a ContractExecuteTransaction.

        Args:
            params: Normalised contract execution parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: ContractExecuteTransaction = ContractExecuteTransaction(
            contract_id=params.contract_id,
            gas=params.gas,
            function_parameters=params.function_parameters,
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_topic(params: CreateTopicParametersNormalised) -> TopicCreateTransaction:
        """Build a TopicCreateTransaction with optional memo.

        Args:
            params: Normalised topic creation parameters.

        Returns:
            TopicCreateTransaction: Transaction ready for submission.
        """
        tx: TopicCreateTransaction = TopicCreateTransaction(
            memo=params.memo,
            submit_key=params.submit_key,
            admin_key=params.admin_key,
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def submit_topic_message(
        params: SubmitTopicMessageParametersNormalised,
    ) -> Transaction:
        """Build a TopicMessageSubmitTransaction.

        Args:
            params: Normalised message submission parameters.

        Returns:
            Transaction: Transaction optionally wrapped in a schedule.
        """
        tx: TopicMessageSubmitTransaction = TopicMessageSubmitTransaction(
            topic_id=params.topic_id,
            message=params.message,
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def update_topic(params: UpdateTopicParametersNormalised) -> TopicUpdateTransaction:
        """Build a TopicUpdateTransaction.

        Args:
            params: Normalised topic update parameters.

        Returns:
            TopicUpdateTransaction: Transaction ready for submission.
        """
        return TopicUpdateTransaction(**vars(params))
