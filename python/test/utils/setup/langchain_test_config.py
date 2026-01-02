import os
from dataclasses import dataclass
from typing import List

from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_consensus_query_plugin,
    core_account_query_plugin,
    core_consensus_plugin,
    core_evm_plugin,
    core_misc_query_plugin,
    core_token_query_plugin,
    core_token_plugin,
    core_transaction_query_plugin,
    core_evm_query_plugin,
)
from hedera_agent_kit.shared import AgentMode
from hedera_agent_kit.shared.plugin import Plugin
from .llm_factory import LLMProvider, LLMOptions

# Maps provider to base environment variable name
BASE_API_KEY_ENV_MAP = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GROQ: "GROQ_API_KEY",
}


@dataclass
class LangchainTestOptions:
    tools: List[str]
    plugins: List[Plugin]
    agent_mode: AgentMode


def get_all_provider_api_keys(provider: LLMProvider) -> List[str]:
    """
    Get all available API keys for a provider.

    Looks for keys in this order:
    - PROVIDER_API_KEY (base key, no suffix)
    - PROVIDER_API_KEY_2, PROVIDER_API_KEY_3, ... up to _9

    Returns a list of all found keys (might be empty).
    """
    base_env_name = BASE_API_KEY_ENV_MAP.get(provider)
    if not base_env_name:
        return []

    keys = []

    # Check base key (e.g., OPENAI_API_KEY)
    if base_key := os.getenv(base_env_name):
        keys.append(base_key)

    # Check numbered keys (e.g., OPENAI_API_KEY_2, OPENAI_API_KEY_3, ...)
    for i in range(2, 10):  # Support up to 9 keys per provider
        if numbered_key := os.getenv(f"{base_env_name}_{i}"):
            keys.append(numbered_key)

    return keys


def get_api_key_for_worker(provider: LLMProvider) -> str | None:
    """
    Get an API key for the current pytest-xdist worker.

    Uses the PYTEST_XDIST_WORKER env var (e.g., "gw0", "gw1") to determine
    which key to use. Workers are assigned keys in a round-robin fashion:
    - Worker gw0 → key index 0
    - Worker gw1 → key index 1
    - etc. (wraps around if more workers than keys)

    If not running under xdist (no worker ID), returns the first available key.
    If only one key exists (the base key without a suffix), all workers use it.

    Returns None if no keys are available for the provider.
    """
    keys = get_all_provider_api_keys(provider)
    if not keys:
        return None

    # Get xdist worker ID (e.g., "gw0", "gw1", "master" for a main process)
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "")

    # Parse worker number from "gwN" format
    if worker_id.startswith("gw"):
        try:
            worker_num = int(worker_id[2:])
        except ValueError:
            worker_num = 0
    else:
        # Not running under xdist, or main process - use the first key
        worker_num = 0

    # Round-robin: select key based on worker number
    return keys[worker_num % len(keys)]


DEFAULT_LLM_OPTIONS: LLMOptions = LLMOptions(
    provider=LLMProvider.OPENAI,
    model="gpt-4o-mini",
    temperature=0.4,
    max_iterations=1,
    system_prompt="""You are a Hedera blockchain assistant. You have access to tools for blockchain operations.
        When a user asks to transfer HBAR, use the transfer_hbar_tool with the correct parameters.
        Extract the amount and recipient account ID from the user's request.
        Always use the exact tool name and parameter structure expected.
        When error occurs, respond with a detailed error message.""",
    api_key=None,
    base_url=None,
)

TOOLKIT_OPTIONS: LangchainTestOptions = LangchainTestOptions(
    tools=[],
    plugins=[
        core_account_plugin,
        core_consensus_plugin,
        core_account_query_plugin,
        core_consensus_query_plugin,
        core_misc_query_plugin,
        core_evm_plugin,
        core_transaction_query_plugin,
        core_token_plugin,
        core_token_query_plugin,
        core_evm_query_plugin,
    ],
    agent_mode=AgentMode.AUTONOMOUS,
)

MIRROR_NODE_WAITING_TIME = 4000


# Balance tiers for test account funding.
# These are defined in USD and should be converted to HBAR at runtime
# using UsdToHbarService.usd_to_hbar().
#
# Tiers:
# - MINIMAL:  $0.50 - Basic operations (single transfer, simple query)
# - STANDARD: $5.00 - Most common test scenarios (token operations, multiple transfers)
# - ELEVATED: $10.00 - Complex operations (NFT minting, multiple token operations)
# - MAXIMUM:  $20.00 - Heavy operations (contract deployments, extensive token operations)

BALANCE_TIERS = {
    "MINIMAL": 0.5,
    "STANDARD": 5.0,
    "ELEVATED": 10.0,
    "MAXIMUM": 20.0,
}
