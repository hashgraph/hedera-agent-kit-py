from __future__ import annotations
import os
from typing import Optional, Any, Callable

from hiero_sdk_python import Client
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import Context, Configuration
from .client_setup import get_operator_client_for_tests
from .langchain_test_config import (
    TOOLKIT_OPTIONS,
    DEFAULT_LLM_OPTIONS,
    LangchainTestOptions,
    get_provider_api_key_map,
)
from .llm_factory import LLMFactory, LLMOptions


class LangchainTestSetup:
    """Container for LangChain test setup components."""

    def __init__(
        self,
        client: Client,
        agent: Any,
        toolkit: "HederaLangchainToolkit",
        cleanup: Callable[[], None],
        response_parser: ResponseParserService,
    ):
        self.client = client
        self.agent = agent
        self.toolkit = toolkit
        self.cleanup = cleanup
        self.response_parser = response_parser


async def create_langchain_test_setup(
    toolkit_options: Optional[LangchainTestOptions] = TOOLKIT_OPTIONS,
    llm_options: Optional[LLMOptions] = DEFAULT_LLM_OPTIONS,
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

    # Use a provided client or create one for tests
    client = custom_client or get_operator_client_for_tests()
    operator_account_id = getattr(client, "operator_account_id", None)

    # Resolve provider, model, and API key
    provider = llm_options.provider or os.getenv("E2E_LLM_PROVIDER")
    model = llm_options.model or os.getenv("E2E_LLM_MODEL")

    api_key_map = get_provider_api_key_map()

    api_key = llm_options.api_key or api_key_map.get(provider)

    if not api_key:
        raise ValueError(f"Missing API key for provider: {provider}")

    # Resolve final LLM options - convert DEFAULT_LLM_OPTIONS to dict first
    resolved_llm_options = {
        **DEFAULT_LLM_OPTIONS.model_dump(),
        **llm_options.model_dump(),
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
            tools=toolkit_options.tools,
            plugins=toolkit_options.plugins,
            context=Context(
                mode=toolkit_options.agent_mode,
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

    response_parser = ResponseParserService(tools=tools)

    # Cleanup function
    def cleanup():
        try:
            client.close()
        except Exception:
            pass

    return LangchainTestSetup(
        client=client,
        agent=agent,
        toolkit=toolkit,
        cleanup=cleanup,
        response_parser=response_parser,
    )
