"""CuratorAgent: keeps knowledge, docs, and dashboards current."""

from __future__ import annotations

from .base import BaseAgent


class CuratorAgent(BaseAgent):
    name = "curator"
    role = "knowledge librarian"
    capabilities = ["curate", "knowledge", "memory", "librarian"]
    tool_names = ["list_files", "read_file", "search_web", "fetch_url"]

    def system_prompt(self) -> str:
        return (
            "You are the CURATOR. Maintain the workspace's shared knowledge: summarize "
            "runs, update the inventory/dashboards, Organize facts and artifacts so the "
            "simulation stays coherent. Output concise, structured updates."
        )
