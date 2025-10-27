from enum import Enum
from typing import Optional, Union

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class LLMOptions(BaseModel):
    """Configuration options for the LLM factory."""

    provider: LLMProvider = Field(
        ..., description="The LLM provider (OpenAI, Anthropic, or Groq)"
    )
    model: Optional[str] = Field(
        None, description="Model name (if not provided, defaults will be used)"
    )
    temperature: float = Field(
        0.0, ge=0.0, le=1.0, description="Controls randomness in generation"
    )
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Custom base URL (OpenAI only)")
    max_iterations: Optional[int] = Field(1, description="Maximum reasoning iterations")
    system_prompt: Optional[str] = Field(
        "", description="System prompt for initialization"
    )



class LLMFactory:
    """Factory for creating configured LangChain LLMs across different providers."""

    @staticmethod
    def create_llm(options: Union[LLMOptions, dict]) -> BaseChatModel:
        """
        Creates and configures an LLM instance.

        Args:
            options (LLMOptions | dict): Configuration options.

        Returns:
            BaseChatModel: Configured LangChain-compatible chat model.

        Raises:
            ValueError: If provider is unsupported or configuration invalid.
        """
        if isinstance(options, dict):
            options = LLMOptions(**options)

        model = options.model or LLMFactory.get_default_model(options.provider)

        match options.provider:
            case LLMProvider.OPENAI:
                return ChatOpenAI(
                    model=model,
                    temperature=options.temperature,
                    api_key=options.api_key,
                    base_url=options.base_url,
                )
            case LLMProvider.ANTHROPIC:
                api_key = SecretStr(options.api_key)
                return ChatAnthropic(
                    model_name=model,
                    temperature=options.temperature,
                    api_key=api_key,
                    timeout=None,
                    stop=None,
                )
            case LLMProvider.GROQ:
                return ChatGroq(
                    model=model,
                    temperature=options.temperature,
                    api_key=options.api_key,
                )
            case _:
                raise ValueError(f"Unsupported LLM provider: {options.provider}")

    @staticmethod
    def get_default_model(provider: LLMProvider) -> str:
        """Returns the default model for a given provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.ANTHROPIC: "claude-3-7-sonnet-20250219",
            LLMProvider.GROQ: "llama3-8b-8192",
        }
        if provider not in defaults:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return defaults[provider]
