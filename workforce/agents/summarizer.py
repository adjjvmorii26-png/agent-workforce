"""SummarizerAgent: synthesizes the final report."""

from __future__ import annotations

from .base import BaseAgent


class SummarizerAgent(BaseAgent):
    name = "summarizer"
    role = "report writer"
    capabilities = ["summarize", "report", "synthesize", "write-report"]
    tool_names = ["read_file", "list_files"]

    def system_prompt(self) -> str:
        return (
            "You are the SUMMARIZER of a multi-agent workforce. Write the final "
            "markdown report for the run: executive summary, what was researched, "
            "what was delivered/created (paths), quality assessment, and next steps. "
            "Inspect the workspace with the file tools so the report lists real artifacts."
        )
