import os
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
import pytest


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
