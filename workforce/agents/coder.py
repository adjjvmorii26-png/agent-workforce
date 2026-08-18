"""CoderAgent: builds the concrete deliverable inside the sandbox."""

from __future__ import annotations

from .base import BaseAgent


class CoderAgent(BaseAgent):
    name = "coder"
    role = "implementer"
    capabilities = ["code", "implement", "build", "write", "engineer"]
    tool_names = ["list_files", "read_file", "write_file", "run_command"]

    def system_prompt(self) -> str:
        return (
            "You are the CODER/IMPLEMENTER of a multi-agent workforce. Produce the "
            "concrete deliverable described in the task using the sandbox filesystem "
            "tools (write_file, read_file, list_files). Prefer real, runnable artifacts "
            "over markdown sketches. If run_command is enabled, verify your work. "
            "End your reply with a short summary of what was created and where."
        )
