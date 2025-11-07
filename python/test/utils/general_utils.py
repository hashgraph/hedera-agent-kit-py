from hiero_sdk_python.contract.contract_id import ContractId


def from_evm_address(evm_address: str) -> ContractId:
    """
    Creates a ContractId instance from a 20-byte EVM address.
    The EVM address layout:
        [4 bytes shard][8 bytes realm][8 bytes contract], all big-endian.

    Args:
        evm_address (str): Hex string, e.g., "0x0123456789abcdef..."

    Returns:
        ContractId: Parsed ContractId with shard, realm, contract extracted.
    """
    # Strip 0x prefix and convert to bytes
    addr_hex = evm_address.lower().replace("0x", "")
    evm_bytes = bytes.fromhex(addr_hex)

    if len(evm_bytes) != 20:
        raise ValueError(
            f"Invalid EVM address length: expected 20 bytes, got {len(evm_bytes)}"
        )

    # Parse bytes back to integers
    shard = int.from_bytes(evm_bytes[0:4], "big")
    realm = int.from_bytes(evm_bytes[4:12], "big")
    contract = int.from_bytes(evm_bytes[12:20], "big")

    return ContractId(
        shard=shard, realm=realm, contract=contract, evm_address=evm_bytes
    )


async def wait(time_in_millis: int):
    """
    Waits for a specified amount of time.

    This function pauses the execution of the program for a given duration
    specified in milliseconds. It uses Python's built-in time module to achieve
    this delay.

    :param time_in_millis: The amount of time to wait, specified in milliseconds.
    :type time_in_millis: int
    """
    import time

    time.sleep(time_in_millis / 1000)
