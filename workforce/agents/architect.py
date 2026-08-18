"""ArchitectAgent: system architecture and design decisions."""

from __future__ import annotations

from .base import BaseAgent


class ArchitectAgent(BaseAgent):
    name = "architect"
    role = "system architect"
    capabilities = ["architecture", "architect", "design-system"]
    tool_names = ["list_files", "read_file", "write_file"]

    def system_prompt(self) -> str:
        return (
            "You are the ARCHITECT. Map the system: modules, boundaries, interfaces, "
            "data flows, and failure points. Produce architecture notes or a code skeleton "
            "when asked. Keep designs minimal, testable, and consistent with the codebase."
        )
