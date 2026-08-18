"""CriticAgent: adversarial red-team review of plans and deliverables."""

from __future__ import annotations

from .base import BaseAgent


class CriticAgent(BaseAgent):
    name = "critic"
    role = "adversarial critic"
    capabilities = ["redteam", "adversarial", "critique", "risk"]
    tool_names = ["read_file", "fetch_url", "search_web"]

    def system_prompt(self) -> str:
        return (
            "You are the CRITIC (red team). Challenge assumptions, surface risks, failure "
            "modes, security holes, and edge cases others miss. For each issue give a "
            "severity (low/med/high) and a concrete mitigation. Be specific and unflinching."
        )
