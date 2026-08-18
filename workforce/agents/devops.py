"""DevopsAgent: releases, CI, and deployment readiness."""

from __future__ import annotations

from .base import BaseAgent


class DevopsAgent(BaseAgent):
    name = "devops"
    role = "release & CI engineer"
    capabilities = ["devops", "release", "deploy", "ci"]
    tool_names = ["list_files", "read_file", "write_file", "run_command"]

    def system_prompt(self) -> str:
        return (
            "You are the DEVOPS / RELEASE engineer. Prepare versioned releases, CI "
            "configs, changelogs, and deployment checklists. Use run_command (if enabled) "
            "and file tools. Keep changes minimal, reversible, and documented."
        )
