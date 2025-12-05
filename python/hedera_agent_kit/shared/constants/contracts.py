"""
Shared constants for deployed Hedera smart contracts (ERC20, ERC721, etc.)
and their ABIs across supported networks.
"""

from hedera_agent_kit.shared.utils.ledger_id import LedgerId


# =====================================================
#  Contract Addresses (per network)
# =====================================================

TESTNET_ERC20_FACTORY_ADDRESS: str = "0.0.6471814"
"""🧪 ERC20 factory deployed on Hedera Testnet"""

TESTNET_ERC721_FACTORY_ADDRESS: str = "0.0.6510666"
"""🧪 ERC721 factory deployed on Hedera Testnet (TODO: verify final address)"""


# =====================================================
#  Network-to-Contract Mappings
# =====================================================

ERC20_FACTORY_ADDRESSES: dict[str, str] = {
    LedgerId.TESTNET.value: TESTNET_ERC20_FACTORY_ADDRESS,
}

ERC721_FACTORY_ADDRESSES: dict[str, str] = {
    LedgerId.TESTNET.value: TESTNET_ERC721_FACTORY_ADDRESS,
}


# =====================================================
# ️ Factory Contract ABIs (Canonical JSON)
# =====================================================

# Human-readable:
# function deployToken(string memory name_, string memory symbol_, uint8 decimals_, uint256 initialSupply_) external returns (address)
ERC20_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "name_", "type": "string"},
            {"internalType": "string", "name": "symbol_", "type": "string"},
            {"internalType": "uint8", "name": "decimals_", "type": "uint8"},
            {"internalType": "uint256", "name": "initialSupply_", "type": "uint256"},
        ],
        "name": "deployToken",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Human-readable:
# function deployToken(string memory name_, string memory symbol_, string memory baseURI_) external returns (address)
ERC721_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "name_", "type": "string"},
            {"internalType": "string", "name": "symbol_", "type": "string"},
            {"internalType": "string", "name": "baseURI_", "type": "string"},
        ],
        "name": "deployToken",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


# =====================================================
# Token Operation ABIs (Canonical JSON)
# =====================================================

# Human-readable:
# function transfer(address to, uint256 amount) external returns (bool)
ERC20_TRANSFER_FUNCTION_NAME = "transfer"
ERC20_TRANSFER_FUNCTION_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Human-readable:
# function balanceOf(address account) external view returns (uint256)
ERC20_BALANCE_OF_FUNCTION_NAME = "balanceOf"
ERC20_BALANCE_OF_FUNCTION_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Human-readable:
# function transferFrom(address from, address to, uint256 tokenId) external returns (bool)
ERC721_TRANSFER_FUNCTION_NAME = "transferFrom"
ERC721_TRANSFER_FUNCTION_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
        ],
        "name": "transferFrom",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Human-readable:
# function safeMint(address to) external returns (bool)
ERC721_MINT_FUNCTION_NAME = "safeMint"
ERC721_MINT_FUNCTION_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "to", "type": "address"}],
        "name": "safeMint",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


# =====================================================
#  Helper Functions
# =====================================================


def get_erc20_factory_address(ledger_id: LedgerId) -> str:
    """Return the ERC20 factory contract address for the given ledger/network."""
    address = ERC20_FACTORY_ADDRESSES.get(ledger_id.value)
    if not address:
        raise ValueError(f"Network type {ledger_id} not supported for ERC20 factory")
    return address


def get_erc721_factory_address(ledger_id: LedgerId) -> str:
    """Return the ERC721 factory contract address for the given ledger/network."""
    address = ERC721_FACTORY_ADDRESSES.get(ledger_id.value)
    if not address:
        raise ValueError(f"Network type {ledger_id} not supported for ERC721 factory")
    return address
