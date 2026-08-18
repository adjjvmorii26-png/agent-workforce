"""QAAgent: writes and runs tests, hunts coverage gaps."""

from __future__ import annotations

from .base import BaseAgent


class QAAgent(BaseAgent):
    name = "qa"
    role = "test engineer"
    capabilities = ["test", "testing", "verify", "qa-engineering"]
    tool_names = ["list_files", "read_file", "write_file", "run_command"]

    def system_prompt(self) -> str:
        return (
            "You are the QA / TEST ENGINEER. Write focused tests, improve existing ones, "
            "and run them with run_command (if enabled). Report pass/fail, coverage gaps, "
            "and edge cases. Prefer small, deterministic tests over heavy frameworks."
        )
