from decimal import Decimal


def to_hbar(tinybars: Decimal) -> Decimal:
    """
    Converts a tinybar amount to an hbar amount.
    """
    return tinybars / Decimal("100000000")


def to_tinybars(hbar: Decimal) -> int:
    return int(hbar * Decimal("100000000"))
