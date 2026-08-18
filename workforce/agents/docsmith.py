"""DocsmithAgent: technical writer for docs, READMEs, and guides."""

from __future__ import annotations

from .base import BaseAgent


class DocsmithAgent(BaseAgent):
    name = "docsmith"
    role = "technical writer"
    capabilities = ["docs", "documentation", "readme", "guide"]
    tool_names = ["list_files", "read_file", "write_file", "fetch_url", "search_web"]

    def system_prompt(self) -> str:
        return (
            "You are the DOCSMITH, a technical writer. Produce clear, well-structured "
            "documentation: READMEs, how-tos, API guides, and tutorials. Use the file and "
            "search tools to ground docs in the actual codebase. Write for a competent but "
            "new reader."
        )
