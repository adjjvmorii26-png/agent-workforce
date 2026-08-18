"""Chimera factory: splice two specialists into one hybrid agent (DNA-style)."""

from __future__ import annotations

from .agents.factory import DynamicAgent
from .agents import AGENT_LOOKUP


def splice(name_a: str, name_b: str, llm, registry, memory, bus, run_id: str,
           extra_rule: str = "Keep the best of both styles; no contradictions.") -> DynamicAgent:
    a = AGENT_LOOKUP.get(name_a)
    b = AGENT_LOOKUP.get(name_b)
    pa = a.system_prompt(a) if a else f"You are the {name_a} specialist."
    pb = b.system_prompt(b) if b else f"You are the {name_b} specialist."
    hybrid = (
        f"You are a CHIMERA — an intentional hybrid of '{name_a}' and '{name_b}'.\n"
        f"Trait A ({name_a}): {pa}\n"
        f"Trait B ({name_b}): {pb}\n"
        f"Rule: {extra_rule}\n"
        "When both traits conflict, explain the tradeoff, then pick the safest bold choice."
    )
    caps = sorted({*(a.capabilities if a else []), *(b.capabilities if b else []), "hybrid"})
    tool_names = sorted({*(a.tool_names if a else []), *(b.tool_names if b else [])})
    return DynamicAgent(
        llm, registry, memory, bus, run_id,
        name=f"{name_a}x{name_b}",
        role=f"chimera: {name_a} × {name_b}",
        capabilities=caps,
        system_prompt=hybrid,
        tool_names=tool_names,
    )
