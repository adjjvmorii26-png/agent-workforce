"""Hive mind: several specialists answer one question, then merge into consensus."""

from __future__ import annotations

from .agents import AGENT_LOOKUP, AgentContext, AgentResult
from .models import Task
from .bus import Event


def run_hive(question: str, llm, registry, memory, bus, run_id: str,
             members: list[str] | None = None, run_id_suffix: str = "hive") -> dict:
    members = members or ["researcher", "critic", "coder"]
    task = Task(id=run_id_suffix, title="Hive question", capability="hive", description=question)
    views: dict[str, str] = {}
    for name in members:
        cls = AGENT_LOOKUP.get(name)
        if not cls:
            continue
        agent = cls(llm, registry, memory, bus, f"{run_id}-{name}")
        views[name] = agent.run(AgentContext(goal=question, task=task)).output
        bus.publish(Event("hive_view", {"agent": name, "preview": views[name][:80]}, source="hive"))
    conductor = AGENT_LOOKUP["summarizer"](llm, registry, memory, bus, f"{run_id}-conductor")
    merged = "\n\n".join(f"## {k}\n{v[:800]}" for k, v in views.items())
    task = Task(id=run_id_suffix, title="Consensus", capability="summarize", description=question + "\n\n" + merged)
    consensus = conductor.run(AgentContext(goal=question, task=task)).output
    return {"question": question, "views": views, "consensus": consensus}
