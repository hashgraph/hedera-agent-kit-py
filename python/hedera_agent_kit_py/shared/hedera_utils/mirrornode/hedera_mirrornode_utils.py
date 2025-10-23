from typing import Optional
from .hedera_mirrornode_service_default_impl import HederaMirrornodeServiceDefaultImpl
from .hedera_mirrornode_service_interface import IHederaMirrornodeService
from .types import LedgerId


def get_mirrornode_service(
    mirrornode_service: Optional[IHederaMirrornodeService], ledger_id: LedgerId
) -> IHederaMirrornodeService:
    if mirrornode_service is not None:
        return mirrornode_service
    return HederaMirrornodeServiceDefaultImpl(ledger_id)
