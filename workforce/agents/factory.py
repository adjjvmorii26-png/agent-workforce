"""Agent factory: recruiters spawn purpose-built agents on demand."""

from __future__ import annotations

from typing import Any

from .base import BaseAgent
from ..models import extract_json


class DynamicAgent(BaseAgent):
    """An agent created at runtime from a spec (name/role/caps/prompt)."""

    def __init__(
        self, llm, registry, memory, bus, run_id: str, *,
        name: str, role: str, capabilities: list[str],
        system_prompt: str, tool_names: list[str] | None = None,
    ) -> None:
        super().__init__(llm, registry, memory, bus, run_id)
        self.name = name
        self.role = role
        self.capabilities = list(capabilities) or ["general"]
        self.tool_names = list(tool_names or [])
        self._prompt = system_prompt

    def system_prompt(self) -> str:
        return self._prompt


class RecruiterAgent(BaseAgent):
    name = "recruiter"
    role = "talent & capability broker"
    capabilities = ["recruit", "spawn", "assemble", "create-agent"]
    tool_names: list[str] = []

    @property
    def json_mode(self) -> bool:
        return True

    def system_prompt(self) -> str:
        return (
            "You are the RECRUITER of a multi-agent workforce. For the described need, "
            "specify exactly one purpose-built agent. Reply with ONLY JSON:\n"
            '{"name": "slug", "role": "short role", "capabilities": ["cap1"], '
            '"system_prompt": "detailed instructions for this agent"}\n'
            "- name: lowercase slug like 'localizer' or 'compliance'\n"
            "- capabilities: 2-4 lowercase tags an orchestrator can route on\n"
            "- system_prompt: precise duties, output format, tools (file/search) to use\n"
        )


def materialize_spec(
    spec: dict[str, Any] | str,
    llm, registry, memory, bus, run_id: str,
) -> DynamicAgent:
    """Turn a spec (dict or JSON text) into a live agent."""
    if isinstance(spec, str):
        parsed = extract_json(spec)
        if not parsed:
            raise ValueError("recruiter spec was not valid JSON")
        spec = parsed
    return DynamicAgent(
        llm, registry, memory, bus, run_id,
        name=str(spec["name"]),
        role=str(spec.get("role", "specialist")),
        capabilities=[str(c) for c in spec.get("capabilities", [])],
        system_prompt=str(spec["system_prompt"]),
        tool_names=spec.get("tool_names"),
    )
