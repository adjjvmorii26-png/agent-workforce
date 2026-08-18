"""ResearcherAgent: gathers facts and sources for a task."""

from __future__ import annotations

from .base import BaseAgent


class ResearcherAgent(BaseAgent):
    name = "researcher"
    role = "research analyst"
    capabilities = ["research", "fact-finding", "analysis"]
    tool_names = ["search_web", "fetch_url"]

    def system_prompt(self) -> str:
        return (
            "You are the RESEARCHER of a multi-agent workforce. Use search_web and "
            "fetch_url to gather accurate, current facts with sources for the assigned "
            "task. Return a concise findings report: key facts, numbers, sources, and "
            "open questions. If tools fail, note that explicitly instead of inventing data."
        )
