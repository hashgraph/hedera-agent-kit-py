import asyncio
from hedera_agent_kit_py.shared.hedera_utils.mirrornode import HederaMirrornodeServiceDefaultImpl
from hedera_agent_kit_py.shared.hedera_utils.mirrornode.hedera_mirrornode_service_interface import \
    IHederaMirrornodeService
from hedera_agent_kit_py.shared.utils.ledger_id import LedgerId


async def main():
    print("Hello World")
    mirrornode: IHederaMirrornodeService = HederaMirrornodeServiceDefaultImpl(LedgerId.TESTNET)

    # Await the async call
    res = await mirrornode.get_account('0.0.5993149')
    print(res)


# Run the async main
asyncio.run(main())
