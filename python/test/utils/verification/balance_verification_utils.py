from decimal import Decimal, getcontext, ROUND_DOWN

from hedera_agent_kit_py.shared.hedera_utils import to_display_unit
from .. import HederaOperationsWrapper

# Set precision for HBAR operations
getcontext().prec = 20


async def verify_hbar_balance_change(
    account_id: str,
    balance_before_raw: Decimal,
    expected_change: Decimal,
    hedera_operations_wrapper: HederaOperationsWrapper,
):
    """
    Helper to verify HBAR balance changes after transactions.
    HBAR has 8 decimal places.
    """
    balance_before = to_display_unit(balance_before_raw, 8)
    balance_after_raw = hedera_operations_wrapper.get_account_hbar_balance(account_id)
    balance_after = to_display_unit(balance_after_raw, 8)

    expected_balance = balance_before + expected_change

    print(
        f"Verifying balance change for account {account_id}. "
        f"Before: {balance_before:.8f} HBAR, "
        f"Expected: {expected_balance:.8f} HBAR, "
        f"Actual: {balance_after:.8f} HBAR."
    )

    # Compare with proper decimal rounding
    assert balance_after.quantize(
        Decimal("1.00000000"), rounding=ROUND_DOWN
    ) >= balance_before.quantize(Decimal("1.00000000"), rounding=ROUND_DOWN)
