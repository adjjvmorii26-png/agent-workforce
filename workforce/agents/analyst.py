"""AnalystAgent: quantitative analysis and benchmarks."""

from __future__ import annotations

from .base import BaseAgent


class AnalystAgent(BaseAgent):
    name = "analyst"
    role = "data analyst"
    capabilities = ["analytics", "metrics", "benchmark", "data-analysis"]
    tool_names = ["read_file", "list_files", "search_web", "fetch_url", "run_command"]

    def system_prompt(self) -> str:
        return (
            "You are the ANALYST. Turn raw data and outputs into numbers: benchmarks, "
            "trends, and clear summaries. Prefer tables and exact figures over prose. "
            "State assumptions and sources. Use run_command only if enabled."
        )
