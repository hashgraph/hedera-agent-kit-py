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


class HederaBuilder:
    @staticmethod
    def maybe_wrap_in_schedule(
        tx, scheduling_params: Optional[ScheduleCreateParams] = None
    ) -> ScheduleCreateTransaction:
        if scheduling_params is not None:
            return ScheduleCreateTransaction(
                scheduling_params
            ).set_scheduled_transaction(tx)
        return tx

    @staticmethod
    def create_fungible_token(
        params: CreateFungibleTokenParametersNormalised,
    ) -> Transaction:
        tx: TokenCreateTransaction = TokenCreateTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_non_fungible_token(
        params: CreateNonFungibleTokenParametersNormalised,
    ) -> Transaction:
        tx: TokenCreateTransaction = TokenCreateTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar(params: TransferHbarParametersNormalised) -> Transaction:
        tx: TransferTransaction = TransferTransaction(
            hbar_transfers=params.hbar_transfers
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar_with_allowance(
        params: TransferHbarWithAllowanceParametersNormalised,
    ) -> TransferTransaction:
        tx: TransferTransaction = TransferTransaction()
        for approved_transfer in params.hbar_approved_transfers:
            tx.add_approved_hbar_transfer(
                approved_transfer.owner_account_id,
                approved_transfer.amount,
            )

        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def transfer_non_fungible_token_with_allowance(
        params: TransferNonFungibleTokenWithAllowanceParametersNormalised,
    ) -> Transaction:
        tx: TransferTransaction = TransferTransaction()

        for token_id, transfers in params.nft_approved_transfer.items():
            for sender_id, receiver_id, serial_number, is_approved in transfers:
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
    def airdrop_fungible_token(
        params: AirdropFungibleTokenParametersNormalised,
    ) -> TokenAirdropTransaction:
        return TokenAirdropTransaction(**vars(params))

    @staticmethod
    def update_token(params: UpdateTokenParametersNormalised) -> TokenUpdateTransaction:
        return TokenUpdateTransaction(**vars(params))

    @staticmethod
    def mint_fungible_token(
        params: MintFungibleTokenParametersNormalised,
    ) -> Transaction:
        tx: TokenMintTransaction = TokenMintTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def mint_non_fungible_token(
        params: MintNonFungibleTokenParametersNormalised,
    ) -> Transaction:
        tx: TokenMintTransaction = TokenMintTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def dissociate_token(
        params: DissociateTokenParametersNormalised,
    ) -> TokenDissociateTransaction:
        return TokenDissociateTransaction(**vars(params))

    @staticmethod
    def create_account(params: CreateAccountParametersNormalised) -> Transaction:
        tx: AccountCreateTransaction = AccountCreateTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_account(
        params: DeleteAccountParametersNormalised,
    ) -> AccountDeleteTransaction:
        return AccountDeleteTransaction(**vars(params))

    @staticmethod
    def update_account(params: UpdateAccountParametersNormalised) -> Transaction:
        tx: AccountUpdateTransaction = AccountUpdateTransaction(params.account_params)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_token(params: DeleteTokenParametersNormalised) -> TokenDeleteTransaction:
        return TokenDeleteTransaction(**vars(params))

    @staticmethod
    def delete_topic(params: DeleteTopicParametersNormalised) -> TopicDeleteTransaction:
        return TopicDeleteTransaction(**vars(params))

    @staticmethod
    def sign_schedule_transaction(
        params: SignScheduleTransactionParameters,
    ) -> ScheduleSignTransaction:
        return ScheduleSignTransaction(**vars(params))

    @staticmethod
    def delete_schedule_transaction(
        params: ScheduleDeleteTransactionParameters,
    ) -> ScheduleDeleteTransaction:
        return ScheduleDeleteTransaction(**vars(params))

    @staticmethod
    def associate_token(
        params: AssociateTokenParametersNormalised,
    ) -> TokenAssociateTransaction:
        return TokenAssociateTransaction(**vars(params))

    @staticmethod
    def _build_account_allowance_approve_tx(
        params,
    ) -> AccountAllowanceApproveTransaction:
        tx: AccountAllowanceApproveTransaction = AccountAllowanceApproveTransaction(
            **vars(params)
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def approve_hbar_allowance(
        params: ApproveHbarAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_nft_allowance(
        params: ApproveNftAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_token_allowance(
        params: ApproveTokenAllowanceParametersNormalised,
    ) -> AccountAllowanceApproveTransaction:
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def execute_transaction(
        params: ContractExecuteTransactionParametersNormalised,
    ) -> Transaction:
        tx: ContractExecuteTransaction = ContractExecuteTransaction(**vars(params))
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_topic(params: CreateTopicParametersNormalised) -> TopicCreateTransaction:
        tx: TopicCreateTransaction = TopicCreateTransaction(**vars(params))
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def submit_topic_message(
        params: SubmitTopicMessageParametersNormalised,
    ) -> Transaction:
        tx: TopicMessageSubmitTransaction = TopicMessageSubmitTransaction(
            **vars(params)
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def update_topic(params: UpdateTopicParametersNormalised) -> TopicUpdateTransaction:
        return TopicUpdateTransaction(**vars(params))
