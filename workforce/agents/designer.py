"""DesignerAgent: builds self-contained, striking HTML/CSS/JS deliverables."""

from __future__ import annotations

from .base import BaseAgent


class DesignerAgent(BaseAgent):
    name = "designer"
    role = "UI & visualization designer"
    capabilities = ["design", "ui", "html", "dashboard", "visual"]
    tool_names = ["list_files", "read_file", "write_file", "fetch_url"]

    def system_prompt(self) -> str:
        return (
            "You are the DESIGNER of a multi-agent workforce. Produce beautiful, "
            "self-contained HTML deliverables: inline CSS and vanilla JS only, NO external "
            "CDNs or dependencies, dark-mode friendly, responsive, accessible. Save files "
            "with write_file. Prefer real data the tools expose. Be bold with layout, "
            "gradients, and micro-interactions while keeping the markup valid."
        )
