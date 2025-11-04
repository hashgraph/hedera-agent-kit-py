import os

from hiero_sdk_python import AccountId, PrivateKey, Client, Network
from pydantic import BaseModel, Field, ValidationError


class EnvConfig(BaseModel):
    ACCOUNT_ID: str = Field(..., description="Hedera account ID in format 0.0.x")
    PRIVATE_KEY: str = Field(..., description="Private key in DER or string format")


def get_operator_client_for_tests() -> Client:
    """
    Creates a Hedera client for testing using environment variables.

    Reads operator credentials from `.env.test.local` and constructs a testnet client.

    Environment variables required:
        - ACCOUNT_ID: The operator account ID (format "0.0.12345")
        - PRIVATE_KEY: The operator private key (DER or string)

    Raises:
        ValidationError: If environment variables are missing or invalid.

    Returns:
        hedera.Client: A configured testnet client ready for use.

    Example:
        >>> test_client = get_operator_client_for_tests()
    """
    try:
        env = EnvConfig(
            ACCOUNT_ID=os.getenv("ACCOUNT_ID"),
            PRIVATE_KEY=os.getenv("PRIVATE_KEY"),
        )
    except ValidationError as e:
        raise RuntimeError(f"Invalid environment configuration: {e}") from e

    # Initialize Hedera client
    account_id = AccountId.from_string(env.ACCOUNT_ID)
    private_key = PrivateKey.from_string(env.PRIVATE_KEY)

    return get_custom_client(account_id, private_key)


def get_custom_client(account_id: AccountId, private_key: PrivateKey) -> Client:
    """
    Creates a Hedera testnet client with custom credentials.

    Args:
        account_id (AccountId): The account ID to use as an operator.
        private_key (PrivateKey): The private key associated with the account.

    Returns:
        hedera.Client: A configured testnet client.

    Example:
        >>> tests_account_id = AccountId.from_string("0.0.12345")
        >>> tests_private_key = PrivateKey.from_string("302e020100300506032b657004220420...")
        >>> tests_client = get_custom_client(tests_account_id, tests_private_key)
    """
    client = Client(Network(network="testnet"))
    client.set_operator(account_id, private_key)

    return client
