"""ReviewerAgent: quality gate with pass/revise verdicts."""

from __future__ import annotations

from .base import BaseAgent, AgentContext, AgentResult
from ..models import parse_review


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    role = "quality gate"
    capabilities = ["review", "critique", "quality", "qa"]
    tool_names = ["read_file", "list_files"]

    @property
    def json_mode(self) -> bool:
        return True

    def system_prompt(self) -> str:
        return (
            "You are the REVIEWER (quality gate) of a multi-agent workforce. Inspect "
            "the work product against the task and goal. Reply with ONLY JSON:\n"
            '{"verdict": "pass" | "revise", "score": <0-100>, '
            '"comments": "specific, actionable feedback"}\n'
            "Be strict: pass only when requirements are met and the output is concrete."
        )

    def _user_message(self, context: AgentContext) -> str:
        base = super()._user_message(context)
        return (
            base
            + f"\n\n# Work product under review\n{context.task.output or '(no output)'}"
            + (f"\n\n# Reviewer feedback already given\n{context.feedback}" if context.feedback else "")
        )

    def run(self, context: AgentContext) -> AgentResult:
        result = super().run(context)
        try:
            review = parse_review(result.output)
        except ValueError as exc:
            result.output = f"ERROR reviewing: {exc}\n--- raw ---\n{result.output}"
            return result
        result.output = f"{review.verdict} | {review.score:.0f} | {review.comments}"
        return result
