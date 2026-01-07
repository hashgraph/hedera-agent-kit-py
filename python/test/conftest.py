import os
import time
from pathlib import Path
import asyncio

from dotenv import load_dotenv
import pytest

from test.utils.usd_to_hbar_service import UsdToHbarService


def pytest_configure(config):
    """
    Called before PyTest collects tests.

    1. Load environment variables from `.env.test.local` (preferred) or fall back to `.env`.
    2. Synchronously initialize `UsdToHbarService` using `asyncio.run` so module-level
       constants that rely on the HBAR/USD exchange rate are available before imports.
    """
    # 1. Load Env Vars
    project_root = Path(__file__).resolve().parent.parent
    env_test_local = project_root / ".env.test.local"
    env_default = project_root / ".env"

    if env_test_local.exists():
        load_dotenv(env_test_local)
        print(f"✅ Loaded environment from {env_test_local}")
    elif env_default.exists():
        load_dotenv(env_default)
        print(f"✅ Loaded environment from {env_default}")
    else:
        print("⚠️  No .env.test.local or .env found at project root.")

    # 2. Initialize HBAR Service
    print("\nInitializing HBAR Price Service (Pre-Collection)...")
    try:
        # We use asyncio.run because this hook is synchronous, but the service is async.
        # This ensures the service is ready before any test modules are imported.
        asyncio.run(UsdToHbarService.initialize())
        print(f"HBAR Rate set to: ${UsdToHbarService._exchange_rate}")
    except Exception as e:
        print(f"❌ Failed to initialize HBAR Service: {e}")


@pytest.fixture(autouse=True)
def slow_down_tests():
    """Add a delay between tests to avoid rate limiting."""
    yield
    delay_ms = float(os.getenv("TEST_DELAY_MS", "0"))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)


# =============================================================================
# SESSION-SCOPED FIXTURES (Run once for entire test session)
# =============================================================================


@pytest.fixture(scope="session")
def operator_client():
    """
    Session-level operator client - created once for entire test run.

    This fixture follows the TypeScript pattern of `beforeAll` at the global level.
    The operator account (from env variables) is used to fund executor accounts
    which perform the actual test operations.

    Yields:
        Client: A configured Hedera testnet client using operator credentials.
    """
    from test.utils.setup import get_operator_client_for_tests

    client = get_operator_client_for_tests()
    yield client
    client.close()


@pytest.fixture(scope="session")
def operator_wrapper(operator_client):
    """
    Session-level operator wrapper - created once for entire test run.

    Provides convenience methods for Hedera operations using the operator account.

    Args:
        operator_client: The session-scoped operator client fixture.

    Returns:
        HederaOperationsWrapper: A wrapper for common Hedera operations.
    """
    from test import HederaOperationsWrapper

    return HederaOperationsWrapper(operator_client)
