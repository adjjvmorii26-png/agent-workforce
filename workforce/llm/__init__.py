from .base import LLMError, LLMProvider, LLMResponse, ToolCall, Usage
from .mock import MockProvider
from .openai_compat import OpenAICompatProvider
from .loop import chat_with_tools

__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMResponse",
    "ToolCall",
    "Usage",
    "MockProvider",
    "OpenAICompatProvider",
    "chat_with_tools",
]


def build_provider(provider: str, llm_cfg) -> LLMProvider:
    """Factory: 'openai' (OpenAI-compatible) or 'mock' (offline deterministic)."""
    if provider == "mock":
        return MockProvider()
    if provider in {"openai", "openai-compatible", "ollama", "openrouter", "azure"}:
        return OpenAICompatProvider(llm_cfg)
    raise ValueError(f"Unknown provider '{provider}' (expected 'openai' or 'mock')")
