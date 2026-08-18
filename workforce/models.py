"""Shared data models for tasks and reviews."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    ACCEPTED = "accepted"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    id: str
    title: str
    capability: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    attempt: int = 1
    input: str = ""
    output: str = ""
    verdict: str = "pending"  # pending | revise | pass
    score: float | None = None
    comments: str = ""
    reviewer: str = ""


@dataclass
class Review:
    verdict: str  # pass | revise
    score: float = 0.0
    comments: str = ""


def extract_json(text: str) -> dict | None:
    """Best-effort extraction of a JSON object from an LLM reply."""
    import json

    try:
        obj = json.loads(text.strip())
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def parse_tasks(text: str) -> list[Task]:
    """Parse a planner's JSON reply into Task objects."""
    obj = extract_json(text)
    if not obj or not isinstance(obj.get("tasks"), list):
        raise ValueError("Planner output did not contain a 'tasks' list")
    tasks: list[Task] = []
    for i, raw in enumerate(obj["tasks"]):
        tasks.append(
            Task(
                id=str(raw.get("id") or f"t{i + 1}"),
                title=str(raw.get("title") or "untitled task"),
                capability=str(raw.get("capability") or "summarize").lower(),
                description=str(raw.get("description") or ""),
                depends_on=[str(d) for d in (raw.get("depends_on") or [])],
            )
        )
    if not tasks:
        raise ValueError("Planner produced an empty task list")
    return tasks


def parse_review(text: str) -> Review:
    obj = extract_json(text)
    if not obj:
        raise ValueError("Reviewer output was not valid JSON")
    verdict = str(obj.get("verdict") or "revise").lower()
    if verdict not in {"pass", "revise"}:
        verdict = "revise"
    return Review(
        verdict=verdict,
        score=float(obj.get("score") or 0),
        comments=str(obj.get("comments") or ""),
    )
