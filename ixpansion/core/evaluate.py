"""X-03: LLM-as-judge evaluation harness (implements an 'evaluator' agent).

The evaluator is a purpose-built agent spawned from a spec, the same pattern the
workforce recruiter uses, so every XI experiment gets its own judge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from workforce.agents.factory import DynamicAgent
from workforce.agents import AgentContext
from workforce.config import WorkforceConfig, LLMConfig
from workforce.llm import MockProvider, OpenAICompatProvider
from workforce.memory import Memory
from workforce.bus import Bus
from workforce.models import Task, extract_json
from workforce.tools import build_default_registry

EVALUATOR_SPEC = {
    "name": "evaluator",
    "role": "LLM-as-judge",
    "capabilities": ["evaluate", "judge", "score"],
    "system_prompt": (
        "You are the EVALUATOR (LLM-as-judge) for IXPANSION. Score the work product "
        "against the rubric. Reply with ONLY JSON: "
        '{"relevance": 0-100, "accuracy": 0-100, "structure": 0-100, "comments": "..."}'
    ),
    "tool_names": ["read_file", "list_files"],
}


def make_evaluator(mock: bool = False) -> DynamicAgent:
    provider = MockProvider() if mock else OpenAICompatProvider(
        LLMConfig(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        )
    )
    cfg = WorkforceConfig()
    return DynamicAgent(
        provider,
        build_default_registry(cfg),
        Memory(":memory:"),
        Bus(workers=1),
        "eval",
        **EVALUATOR_SPEC,
    )


@dataclass
class Evaluation:
    relevance: float = 0.0
    accuracy: float = 0.0
    structure: float = 0.0
    comments: str = ""
    mean: float = 0.0

    def to_dict(self) -> dict:
        return {
            "relevance": self.relevance,
            "accuracy": self.accuracy,
            "structure": self.structure,
            "mean": self.mean,
            "comments": self.comments,
        }


def evaluate_report(report_text: str, goal: str, mock: bool = False) -> Evaluation:
    judge = make_evaluator(mock=mock)
    task = Task(id="eval", title="Evaluate report", capability="evaluate", description=report_text[:4000])
    out = judge.run(AgentContext(goal=goal, task=task)).output
    data = extract_json(out) or {}
    scores = [float(data.get(k, 0)) for k in ("relevance", "accuracy", "structure")]
    return Evaluation(
        relevance=scores[0],
        accuracy=scores[1],
        structure=scores[2],
        comments=str(data.get("comments", "")),
        mean=sum(scores) / 3,
    )
