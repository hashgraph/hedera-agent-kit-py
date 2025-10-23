from hedera_agent_kit_py.shared.utils.ledger_id import LedgerId

TESTNET_ERC20_FACTORY_ADDRESS = "0.0.6471814"
TESTNET_ERC721_FACTORY_ADDRESS = (
    "0.0.6510666"  ## TODO: Update with actual deployed address
)

# ERC20 Factory contract addresses for different networks
ERC20_FACTORY_ADDRESSES = {
    LedgerId.TESTNET.value: TESTNET_ERC20_FACTORY_ADDRESS,
}

# ERC721 Factory contract addresses for different networks
ERC721_FACTORY_ADDRESSES = {
    LedgerId.TESTNET.value: TESTNET_ERC721_FACTORY_ADDRESS,
}

# ERC20 Factory contract ABI
ERC20_FACTORY_ABI = [
    "function deployToken(string memory name_, string memory symbol_, uint8 decimals_, uint256 initialSupply_) external returns (address)",
]

# ERC721 Factory contract ABI
ERC721_FACTORY_ABI = [
    "function deployToken(string memory name_, string memory symbol_, string memory baseURI_) external returns (address)",
]

ERC20_TRANSFER_FUNCTION_NAME = "transfer"
ERC20_TRANSFER_FUNCTION_ABI = [
    "function transfer(address to, uint256 amount) external returns (bool)",
]

ERC721_TRANSFER_FUNCTION_NAME = "transferFrom"
ERC721_TRANSFER_FUNCTION_ABI = [
    "function transferFrom(address from, address to, uint256 tokenId) external returns (bool)",
]

ERC721_MINT_FUNCTION_NAME = "safeMint"
ERC721_MINT_FUNCTION_ABI = ["function safeMint(address to) external returns (bool)"]


def get_erc20_factory_address(ledger_id: LedgerId) -> str:
    address = ERC20_FACTORY_ADDRESSES.get(ledger_id.value)
    if not address:
        raise ValueError(f"Network type {ledger_id} not supported for ERC20 factory")
    return address


def get_erc721_factory_address(ledger_id: LedgerId) -> str:
    address = ERC721_FACTORY_ADDRESSES.get(ledger_id.value)
    if not address:
        raise ValueError(f"Network type {ledger_id} not supported for ERC721 factory")
    return address
