"""PlannerAgent: turns a goal into an ordered task graph."""

from __future__ import annotations

from .base import BaseAgent, AgentContext, AgentResult
from ..models import parse_tasks


class PlannerAgent(BaseAgent):
    name = "planner"
    role = "chief planner"
    capabilities = ["plan", "planning", "decompose"]
    tool_names: list[str] = []

    def system_prompt(self) -> str:
        return (
            "You are the PLANNER of a multi-agent workforce. Break the goal into a "
            "small task graph the team can execute. Reply with ONLY a JSON object:\n"
            '{"tasks": [{"id": "t1", "title": "...", "capability": "research|code|summarize", '
            '"description": "...", "depends_on": ["t1", ...]}]}\n'
            "- research: gather facts and sources from the web\n"
            "- code: produce the concrete deliverable (files, code, docs)\n"
            "- design: build self-contained HTML/CSS/JS dashboards or UIs\n"
            "- test: write/run QA tests and find coverage gaps\n"
            "- docs: write documentation, READMEs, guides\n"
            "- redteam: adversarial critique and risk analysis\n"
            "- devops: releases, CI, deployment readiness\n"
            "- recruit: spawn a purpose-built agent for novel work\n"
            "- architecture: design system architecture\n"
            "- analytics: quantitative analysis and benchmarks\n"
            "- curate: maintain knowledge, docs, and dashboards\n"
            "- summarize: write the final report\n"
            "Use 3-6 tasks. IDs must be unique and depends_on must reference earlier ids."
        )

    @property
    def json_mode(self) -> bool:
        return True

    def run(self, context: AgentContext) -> AgentResult:
        result = super().run(context)
        try:
            tasks = parse_tasks(result.output)
        except ValueError as exc:
            result.output = f"ERROR planning: {exc}\n--- raw ---\n{result.output}"
            return result
        planner_json = "\n".join(
            f"{t.id}\t{t.capability}\t{t.title}\t" + ",".join(t.depends_on)
            for t in tasks
        )
        result.output = planner_json
        return result
