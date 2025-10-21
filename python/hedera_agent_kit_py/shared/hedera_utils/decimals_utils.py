from decimal import Decimal, getcontext, ROUND_FLOOR

# Set high precision for large token calculations
getcontext().prec = 100

## TODO: this must match SDK transaction responses - might require adjustment later

def to_base_unit(amount: float | Decimal, decimals: int) -> Decimal:
    """
    Converts a token amount to base units (the smallest denomination).
    Example: `to_base_unit(1.5, 8) => Decimal('150000000')`
    """
    amount_dec = Decimal(amount)
    multiplier = Decimal(10) ** decimals
    return (amount_dec * multiplier).to_integral_value(rounding=ROUND_FLOOR)


def to_display_unit(base_amount: float | Decimal, decimals: int) -> Decimal:
    """
    Converts a base unit amount to a human-readable value.
    Example: `to_display_unit(150000000, 8) => Decimal('1.5')`
    """
    base_amount_dec = Decimal(base_amount)
    divisor = Decimal(10) ** decimals
    return base_amount_dec / divisor
