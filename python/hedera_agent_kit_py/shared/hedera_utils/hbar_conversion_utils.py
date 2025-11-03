from decimal import Decimal, ROUND_HALF_UP


def to_hbar(tinybars: Decimal) -> Decimal:
    """
    Converts a tinybar amount to an hbar amount.
    """
    return tinybars / Decimal("100000000")


def to_tinybars(hbar: Decimal) -> int:
    tinybars = hbar * Decimal("100000000")
    # Round to the nearest integer using Decimal's rounding
    tinybars_rounded = tinybars.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(tinybars_rounded)
