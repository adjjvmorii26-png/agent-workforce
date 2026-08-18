"""Base agent runtime shared by every worker in the workforce."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..llm import chat_with_tools


@dataclass
class AgentContext:
    goal: str
    task: Any  # Task
    feedback: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    sandbox: str = "workspace"


@dataclass
class AgentResult:
    output: str = ""
    message_count: int = 0


class BaseAgent:
    """Common plumbing: system prompt, memory-injected context, tool loop."""

    name = "base"
    role = "generic worker"
    capabilities: list[str] = []
    tool_names: list[str] = []

    def __init__(self, llm, registry, memory, bus, run_id: str) -> None:
        self.llm = llm
        self.registry = registry
        self.memory = memory
        self.bus = bus
        self.run_id = run_id

    # ------------------------------------------------------------------ #
    def system_prompt(self) -> str:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    def run(self, context: AgentContext) -> AgentResult:
        signature = self.system_prompt()
        signature += self._prompt_tools()
        user_msg = self._user_message(context)
        system = signature + self._prompt_facts(context.facts)

        tools = {
            n: f for n, f in self.registry.executors().items() if n in self.tool_names
        }
        tool_specs = {
            n: s for n, s in self.registry.tool_specs().items() if n in self.tool_names
        }
        response, transcript = chat_with_tools(
            self.llm,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            tools=tools,
            tool_specs=tool_specs,
            json_mode=self.json_mode,
            max_rounds=self.llm.cfg.max_tool_rounds
            if hasattr(self.llm, "cfg")
            else 8,
        )
        self._log(context, transcript)
        return AgentResult(
            output=response.text.strip(),
            message_count=len(transcript),
        )

    # ------------------------------------------------------------------ #
    @property
    def json_mode(self) -> bool:
        return False

    def _user_message(self, context: AgentContext) -> str:
        parts = [f"# Goal\n{context.goal}"]
        parts.append(f"# Task\n{context.task.title}\n{context.task.description}")
        if context.feedback:
            parts.append(f"# Reviewer feedback (address it)\n{context.feedback}")
        return "\n\n".join(parts)

    def _prompt_facts(self, facts: dict[str, Any]) -> str:
        if not facts:
            return ""
        import json

        return "\n\n# Long-term memory facts\n" + json.dumps(facts, indent=2, default=str)

    def _prompt_tools(self) -> str:
        if not self.tool_names:
            return ""
        enabled = [n for n in self.tool_names if n in self.registry.enabled_names()]
        return (
            "\n\n# Tools available\n"
            + ", ".join(enabled)
            + "\nUse them when they help; when calling a tool, wait for its result "
            "before continuing."
        )

    def _log(self, context: AgentContext, transcript: list[dict[str, Any]]) -> None:
        task_id = getattr(context.task, "id", None)
        for msg in transcript:
            self.memory.log_message(self.run_id, self.name, msg["role"], msg.get("content") or "", task_id=task_id)
