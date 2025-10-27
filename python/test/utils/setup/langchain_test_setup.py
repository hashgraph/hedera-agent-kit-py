import os
from typing import Optional, Dict, Any, Callable

from dotenv import load_dotenv
from hiero_sdk_python import Client
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit_py.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit_py.shared.configuration import AgentMode, Context, Configuration
from . import (
    TOOLKIT_OPTIONS,
    get_operator_client_for_tests,
    DEFAULT_LLM_OPTIONS,
    LLMFactory,
)
from . import PROVIDER_API_KEY_MAP

load_dotenv(".env.test.local")


class LangchainTestSetup:
    """Container for LangChain test setup components."""

    def __init__(
        self,
        client: Client,
        agent: Any,
        toolkit: HederaLangchainToolkit,
        cleanup: Callable[[], None],
    ):
        self.client = client
        self.agent = agent
        self.toolkit = toolkit
        self.cleanup = cleanup


def get_provider_api_key_map():
    pass


async def create_langchain_test_setup(
    toolkit_options: Optional[Dict[str, Any]] = None,
    llm_options: Optional[Dict[str, Any]] = None,
    custom_client: Optional[Client] = None,
) -> LangchainTestSetup:
    """
    Creates a full LangChain test setup for Hedera integration testing.

    Args:
        toolkit_options (dict): Tool and plugin configuration.
        llm_options (dict): Optional overrides for LLM (provider, model, temperature, apiKey, etc.).
        custom_client (Client): Optionally provide a pre-configured Hedera client.

    Returns:
        LangchainTestSetup: Fully initialized testing environment (client, agent, toolkit, cleanup).
    """

    toolkit_options = toolkit_options or TOOLKIT_OPTIONS
    llm_options = llm_options or {}

    # Use a provided client or create one for tests
    client = custom_client or get_operator_client_for_tests()
    operator_account_id = getattr(client, "operator_account_id", None)

    # Resolve provider, model, and API key
    provider = (
        llm_options.get("provider")
        or os.getenv("E2E_LLM_PROVIDER")
        or DEFAULT_LLM_OPTIONS["provider"]
    )
    model = (
        llm_options.get("model")
        or os.getenv("E2E_LLM_MODEL")
        or DEFAULT_LLM_OPTIONS.get("model")
    )

    api_key = llm_options.get("api_key") or PROVIDER_API_KEY_MAP.get(provider)

    if not api_key:
        raise ValueError(f"Missing API key for provider: {provider}")

    # Resolve final LLM options
    resolved_llm_options = {
        **DEFAULT_LLM_OPTIONS,
        **llm_options,
        "provider": provider,
        "model": model,
        "api_key": api_key,
    }

    # Create the LLM instance
    llm = LLMFactory.create_llm(resolved_llm_options)

    # Initialize toolkit
    toolkit = HederaLangchainToolkit(
        client=client,
        configuration=Configuration(
            tools=toolkit_options.get("tools"),
            plugins=toolkit_options.get("plugins"),
            context=Context(
                mode=toolkit_options.get("agentMode", AgentMode.AUTONOMOUS),
                account_id=str(operator_account_id),
            ),
        ),
    )

    # Prepare tools and create agent
    tools = toolkit.get_tools()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=DEFAULT_LLM_OPTIONS.system_prompt,
        checkpointer=InMemorySaver(),
    )

    # Cleanup function
    def cleanup():
        try:
            client.close()
        except Exception:
            pass

    return LangchainTestSetup(
        client=client, agent=agent, toolkit=toolkit, cleanup=cleanup
    )
