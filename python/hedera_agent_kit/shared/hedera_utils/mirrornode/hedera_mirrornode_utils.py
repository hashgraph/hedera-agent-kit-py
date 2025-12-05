from typing import Optional
from .hedera_mirrornode_service_default_impl import HederaMirrornodeServiceDefaultImpl
from .hedera_mirrornode_service_interface import IHederaMirrornodeService
from .types import LedgerId


def get_mirrornode_service(
    mirrornode_service: Optional[IHederaMirrornodeService], ledger_id: LedgerId
) -> IHederaMirrornodeService:
    """Return a Hedera Mirrornode service instance.

    If a service instance is provided, it is returned as-is. Otherwise, a
    default implementation (`HederaMirrornodeServiceDefaultImpl`) is created
    for the given ledger ID.

    Args:
        mirrornode_service (Optional[IHederaMirrornodeService]): Optional existing service instance.
        ledger_id (LedgerId): Ledger ID used to create a default service if needed.

    Returns:
        IHederaMirrornodeService: The Mirrornode service instance.
    """
    if mirrornode_service is not None:
        return mirrornode_service
    return HederaMirrornodeServiceDefaultImpl(ledger_id)
