"""Utilities for resolving deployed contract addresses from transaction records.

This module provides helpers to extract the EVM address of contracts deployed
via factory pattern transactions on Hedera.
"""

from __future__ import annotations

from hiero_sdk_python import Client
from hiero_sdk_python.query.transaction_record_query import TransactionRecordQuery

from hedera_agent_kit.shared.models import RawTransactionResponse


async def get_deployed_contract_address(
    client: Client, raw: RawTransactionResponse
) -> str | None:
    """Resolve the deployed contract EVM address from a transaction record.

    When a factory contract deploys a new contract (e.g., ERC20 or ERC721),
    the new contract's address is returned as part of the function result.
    This helper queries the transaction record and decodes that address from
    the ABI-encoded return bytes.

    Args:
        client: The Hedera client used to query the transaction record.
        raw: The raw transaction response containing the transaction ID.

    Returns:
        The deployed contract's EVM address as a hex string (e.g., "0x..."),
        or None if the address could not be resolved.
    """
    record = (
        TransactionRecordQuery().set_transaction_id(raw.transaction_id).execute(client)
    )

    contract_call_result = getattr(record, "call_result", None)

    if contract_call_result is None:
        return None

    # Access the raw ABI-encoded return bytes from the function result
    result_bytes = getattr(contract_call_result, "contract_call_result", None)

    if not result_bytes or not isinstance(result_bytes, (bytes, bytearray)):
        return None

    # The factory returns an EVM address as the first return value.
    # In Solidity ABI, an address is encoded as a 32-byte word left-padded with zeros.
    # We need to take the last 20 bytes of the first 32-byte word.
    if len(result_bytes) < 32:
        return None

    first_word = bytes(result_bytes[:32])
    addr_last_20 = first_word[-20:]
    evm_addr = "0x" + addr_last_20.hex()
    return evm_addr
