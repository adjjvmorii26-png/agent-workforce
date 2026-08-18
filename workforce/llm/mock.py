"""Deterministic offline provider so the whole workforce runs without a key."""

from __future__ import annotations

import json
from typing import Any

from .base import LLMResponse


def _system(messages: list[dict[str, Any]]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return m.get("content", "")
    return ""


def _all_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(m.get("content", "") or "" for m in messages)


class MockProvider:
    """Returns plausible, deterministic answers keyed off the agent role.

    The reviewer is stateful per conversation: the first review asks for a
    revision, the second accepts, so orchestration loops can be demoed offline.
    """

    name = "mock"

    def __init__(self) -> None:
        self._reviews: dict[str, int] = {}

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        system = _system(messages)
        text = _all_text(messages)
        lower = system.lower()

        if "planner" in lower:
            return self._plan(text)
        if "researcher" in lower:
            return self._research(text)
        if "coder" in lower:
            return self._code(text)
        if "reviewer" in lower:
            return self._review(system, text)
        if "summarizer" in lower or "summarize" in lower:
            return self._summary(text)
        if "recruiter" in lower:
            return self._recruit(text)

        return LLMResponse(text=f"[mock] processed request: {text[:200]}")

    def _recruit(self, text: str) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(
                {
                    "name": "localizer",
                    "role": "localization specialist",
                    "capabilities": ["localize", "i18n", "translate"],
                    "system_prompt": (
                        "You are a LOCALIZER. Adapt content to target locales: "
                        "translate text, preserve tone, and flag cultural issues. "
                        "Use file tools when asked."
                    ),
                    "tool_names": ["read_file", "write_file", "list_files"],
                },
                indent=2,
            )
        )

    # ------------------------------------------------------------------ #
    def _plan(self, text: str) -> LLMResponse:
        goal = text.strip() or "the goal"
        tasks = [
            {
                "id": "t1",
                "title": "Research",
                "capability": "research",
                "description": f"Gather facts about: {goal}",
                "depends_on": [],
            },
            {
                "id": "t2",
                "title": "Implement",
                "capability": "code",
                "description": f"Produce a concrete deliverable for: {goal}",
                "depends_on": ["t1"],
            },
            {
                "id": "t3",
                "title": "Summarize",
                "capability": "summarize",
                "description": "Write the final report.",
                "depends_on": ["t2"],
            },
        ]
        return LLMResponse(text=json.dumps({"tasks": tasks}, indent=2))

    def _research(self, text: str) -> LLMResponse:
        return LLMResponse(
            text=(
                "Findings:\n"
                "- Key fact A about the topic.\n"
                "- Key fact B with source notes.\n"
                "- Open questions remain around cost and timeline.\n\n"
                f"Based on the request: {text[:250]}"
            )
        )

    def _code(self, text: str) -> LLMResponse:
        return LLMResponse(
            text=(
                "```python\n"
                "def deliverable():\n"
                '    return "workforce deliverable is complete"\n'
                "\n\n"
                'if __name__ == "__main__":\n'
                "    print(deliverable())\n"
                "```\n\n"
                f"Rationale: generated for request - {text[:250]}"
            )
        )

    def _review(self, system: str, text: str) -> LLMResponse:
        key = f"{system[:40]}|{text[:40]}"
        count = self._reviews.get(key, 0)
        self._reviews[key] = count + 1
        if count % 2 == 0:  # first review: request revision
            return LLMResponse(
                text=json.dumps(
                    {
                        "verdict": "revise",
                        "score": 62,
                        "comments": "Solid draft; needs references and a clearer conclusion.",
                    }
                )
            )
        return LLMResponse(
            text=json.dumps(
                {
                    "verdict": "pass",
                    "score": 92,
                    "comments": "Meets all requirements.",
                }
            )
        )

    def _summary(self, text: str) -> LLMResponse:
        return LLMResponse(
            text=(
                "# Final Report\n\n"
                "## Summary\n"
                "The workforce completed the requested work end-to-end "
                "(planning, research, implementation, review), producing an "
                "accepted deliverable.\n\n"
                "## Highlights\n"
                "- Completed tasks 1-3 with review acceptance.\n"
                "- Artifacts written to the workspace.\n\n"
                "## Next steps\n"
                "- Run with a live provider: `workforce run 'your goal'`.\n\n"
                f"Goal: {text[:400]}"
            )
        )
