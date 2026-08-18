"""Specialized workforce agents and capability routing."""

from .base import AgentContext, AgentResult, BaseAgent
from .planner import PlannerAgent
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .reviewer import ReviewerAgent
from .summarizer import SummarizerAgent

TEAM = {
    "plan": PlannerAgent,
    "research": ResearcherAgent,
    "code": CoderAgent,
    "review": ReviewerAgent,
    "summarize": SummarizerAgent,
}

CAPABILITY_TO_AGENT = {}
for _agent_cls in TEAM.values():
    for _cap in _agent_cls.capabilities:
        CAPABILITY_TO_AGENT.setdefault(_cap, _agent_cls.name)

AGENT_LOOKUP = {cls.name: cls for cls in TEAM.values()}


def build_team(llm, registry, memory, bus, run_id: str) -> dict[str, BaseAgent]:
    return {
        cls.name: cls(llm, registry, memory, bus, run_id)
        for cls in TEAM.values()
    }


def resolve_agent_name(capability: str) -> str:
    cap = capability.lower()
    if cap in AGENT_LOOKUP:
        return cap
    return CAPABILITY_TO_AGENT.get(cap, "summarizer")


__all__ = [
    "AgentContext",
    "AgentResult",
    "TEAM",
    "CAPABILITY_TO_AGENT",
    "AGENT_LOOKUP",
    "build_team",
    "resolve_agent_name",
    "PlannerAgent",
    "ResearcherAgent",
    "CoderAgent",
    "ReviewerAgent",
    "SummarizerAgent",
]
