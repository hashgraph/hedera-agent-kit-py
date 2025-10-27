import logging
from decimal import Decimal

from hiero_sdk_python import AccountId

from hedera_agent_kit_py.shared.hedera_utils import to_base_unit
from hedera_agent_kit_py.shared.parameter_schemas import (
    DeleteAccountParametersNormalised,
    TransferHbarParametersNormalised,
)
from .. import HederaOperationsWrapper


async def return_hbars_and_delete_account(
    account_wrapper: HederaOperationsWrapper,
    account_to_delete: AccountId,
    account_to_return: AccountId,
) -> None:
    """
    Attempts to delete a test account and return its HBAR balance to a specified account.
    Best-effort cleanup: tries to delete the account. If the account holds tokens,
    deletion fails, and the HBAR balance is transferred back to the operator account,
    leaving 0.1 HBAR for transaction fees.
    """
    try:
        await account_wrapper.delete_account(
            DeleteAccountParametersNormalised(
                account_id=account_to_delete, transfer_account_id=account_to_return
            )
        )
    except Exception as e:
        logging.error(
            "Error deleting account. Attempting to recover HBARs. Account will not be deleted. Error: %s",
            e,
        )

        # Get current HBAR balance in tinybars
        balance_tinybars: int = account_wrapper.get_account_hbar_balance(
            str(account_to_delete)
        )

        # Compute transfer amount, leaving 0.1 HBAR for fees
        transfer_amount_tinybars = int(
            balance_tinybars - to_base_unit(Decimal("0.1"), 8)
        )
        if transfer_amount_tinybars <= 0:
            raise ValueError("Not enough HBAR to return")

        # Use HederaOperationsWrapper transfer_hbar method
        await account_wrapper.transfer_hbar(
            TransferHbarParametersNormalised(
                hbar_transfers=[
                    {account_to_return, transfer_amount_tinybars},
                    {account_to_delete, -transfer_amount_tinybars},
                ]
            )
        )
