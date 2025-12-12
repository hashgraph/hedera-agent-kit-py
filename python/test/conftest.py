import os
import time
from pathlib import Path

from dotenv import load_dotenv
import pytest

from test.utils.usd_to_hbar_service import UsdToHbarService


@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """
    Automatically load environment variables for all tests.

    Priority:
        1. .env.test.local  (for test-specific config)
        2. .env             (fallback)

    This fixture runs automatically before any test session.
    """
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

    # Optionally verify key vars for visibility
    print(f"ACCOUNT_ID={os.getenv('ACCOUNT_ID')}")
    print(f"PRIVATE_KEY={'***' if os.getenv('PRIVATE_KEY') else None}")
    print(f"OPENAI_API_KEY={'***' if os.getenv('OPENAI_API_KEY') else None}")


@pytest.fixture(scope="session", autouse=True)
async def init_hbar_service():
    """
    Initialize the UsdToHbarService once per test session. Fetches the live price via the service logic.
    """
    print("\nInitializing HBAR Price Service...")
    await UsdToHbarService.initialize()
    print(f"HBAR Rate set to: ${UsdToHbarService._exchange_rate}")


@pytest.fixture(autouse=True)
def slow_down_tests():
    """Add a delay between tests to avoid rate limiting."""
    yield
    delay_ms = float(os.getenv("TEST_DELAY_MS", "0"))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)
