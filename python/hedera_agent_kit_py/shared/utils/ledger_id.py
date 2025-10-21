from enum import Enum

from hiero_sdk_python import Network


class LedgerId(Enum):
    """
    Represents the ledger types for different network environments.

    This class is an enumeration that provides values representing distinct
    network environments typically used in Blockchain or distributed ledger
    systems. The enumerator members correspond to predefined environments such
    as a testing network, a production network, and a preview network.
    """
    TESTNET = 'testnet'
    MAINNET = 'mainnet'
    PREVIEWNET = 'previewnet'


def network_from_ledger_id(ledger_id: LedgerId) -> Network:
    return Network(network=ledger_id.value)

def ledger_id_from_network(network: Network) -> LedgerId:
    return LedgerId(network.network)