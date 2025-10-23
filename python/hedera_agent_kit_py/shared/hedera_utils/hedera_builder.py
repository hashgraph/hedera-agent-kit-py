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
)
from hiero_sdk_python.schedule.schedule_create_transaction import ScheduleCreateParams

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
)


# FIXME: Most of these methods are not implemented and typed correctly yet.
#  The python implementation has more types build into the SDK than the TS one and we need to align our approach to reuse them


class HederaBuilder:
    @staticmethod
    def maybe_wrap_in_schedule(
        tx, scheduling_params: Optional[ScheduleCreateParams] = None
    ):
        if scheduling_params is not None:
            return ScheduleCreateTransaction(
                scheduling_params
            ).set_scheduled_transaction(tx)
        return tx

    @staticmethod
    def create_fungible_token(params: CreateFungibleTokenParametersNormalised):
        tx = TokenCreateTransaction(
            token_params=params.token_params,
            keys=params.keys,
        )
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_non_fungible_token(params: CreateNonFungibleTokenParametersNormalised):
        tx = TokenCreateTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar(params: TransferHbarParametersNormalised):
        tx = TransferTransaction(hbar_transfers=params.hbar_transfers)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def transfer_hbar_with_allowance(
        params: TransferHbarWithAllowanceParametersNormalised,
    ):
        tx = TransferTransaction(**params.dict())  # FIXME
        tx.add_approved_hbar_transfer(
            params.hbar_approved_transfer.owner_account_id,
            params.hbar_approved_transfer.amount,
        )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def transfer_non_fungible_token_with_allowance(
        params: TransferNonFungibleTokenWithAllowanceParametersNormalised,
    ):
        tx = TransferTransaction()
        for transfer in params.transfers:
            tx.add_approved_nft_transfer(
                transfer.nft_id, params.source_account_id, transfer.receiver
            )
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def transfer_fungible_token_with_allowance(
        params: TransferFungibleTokenWithAllowanceParametersNormalised,
    ):
        tx = TransferTransaction()
        tx.add_approved_token_transfer(
            params.token_id,
            params.approved_transfer.owner_account_id,
            params.approved_transfer.amount,
        )
        for t in params.token_transfers:
            tx.add_token_transfer(t.token_id, t.account_id, t.amount)
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def airdrop_fungible_token(params: AirdropFungibleTokenParametersNormalised):
        return TokenAirdropTransaction(**params.dict())  # FIXME

    @staticmethod
    def update_token(params: UpdateTokenParametersNormalised):
        return TokenUpdateTransaction(**params.dict())  # FIXME

    @staticmethod
    def mint_fungible_token(params: MintFungibleTokenParametersNormalised):
        tx = TokenMintTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def mint_non_fungible_token(params: MintNonFungibleTokenParametersNormalised):
        tx = TokenMintTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def dissociate_token(params: DissociateTokenParametersNormalised):
        return TokenDissociateTransaction(**params.dict())  # FIXME

    @staticmethod
    def create_account(params: CreateAccountParametersNormalised):
        tx = AccountCreateTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_account(params: DeleteAccountParametersNormalised):
        return AccountDeleteTransaction(**params.dict())  # FIXME

    @staticmethod
    def update_account(params: UpdateAccountParametersNormalised):
        tx = AccountUpdateTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def delete_token(params: DeleteTokenParametersNormalised):
        return TokenDeleteTransaction(**params.dict())  # FIXME

    @staticmethod
    def delete_topic(params: DeleteTopicParametersNormalised):
        return TopicDeleteTransaction(**params.dict())  # FIXME

    @staticmethod
    def sign_schedule_transaction(params: ScheduleSignTransaction):
        return ScheduleSignTransaction(**params.dict())  # FIXME

    @staticmethod
    def delete_schedule_transaction(params: ScheduleDeleteTransaction):
        return ScheduleDeleteTransaction(**params.dict())  # FIXME

    @staticmethod
    def associate_token(params: AssociateTokenParametersNormalised):
        return TokenAssociateTransaction(
            account_id=params.account_id,
            token_ids=[t for t in params.token_ids],
        )

    @staticmethod
    def _build_account_allowance_approve_tx(params):
        tx = AccountAllowanceApproveTransaction(**params.dict())
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def approve_hbar_allowance(params: ApproveHbarAllowanceParametersNormalised):
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_nft_allowance(params: ApproveNftAllowanceParametersNormalised):
        return HederaBuilder._build_account_allowance_approve_tx(params)

    @staticmethod
    def approve_token_allowance(params: ApproveTokenAllowanceParametersNormalised):
        tx = AccountAllowanceApproveTransaction(**params.dict())  # FIXME
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def execute_transaction(params: ContractExecuteTransactionParametersNormalised):
        tx = ContractExecuteTransaction(**params.dict())  # FIXME
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def create_topic(params: CreateTopicParametersNormalised):
        tx_params = params.dict(exclude={"transaction_memo"})  # FIXME
        tx = TopicCreateTransaction(**tx_params)
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return tx

    @staticmethod
    def submit_topic_message(params: SubmitTopicMessageParametersNormalised):
        tx_params = params.dict(exclude={"transaction_memo"})  # FIXME
        tx = TopicMessageSubmitTransaction(**tx_params)
        if getattr(params, "transaction_memo", None):
            tx.set_transaction_memo(params.transaction_memo)
        return HederaBuilder.maybe_wrap_in_schedule(
            tx, getattr(params, "scheduling_params", None)
        )

    @staticmethod
    def update_topic(params: UpdateTopicParametersNormalised):
        return TopicUpdateTransaction(**params.dict())  # FIXME
