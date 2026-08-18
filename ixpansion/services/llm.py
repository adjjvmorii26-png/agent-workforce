"""LLM facade for IXPANSION, reusing the central hub's provider layer."""

from __future__ import annotations

import os

from workforce.llm import MockProvider, OpenAICompatProvider
from workforce.config import LLMConfig


def make_provider(mock: bool = False):
    if mock:
        return MockProvider()
    return OpenAICompatProvider(
        LLMConfig(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        )
    )
