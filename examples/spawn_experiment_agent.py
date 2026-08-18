"""Recruiter demo: spawn a purpose-built agent for an experiment, then run it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workforce.agents.factory import RecruiterAgent, materialize_spec
from workforce.agents import AgentContext
from workforce.bus import Bus
from workforce.config import WorkforceConfig
from workforce.llm import MockProvider
from workforce.memory import Memory
from workforce.models import Task
from workforce.tools import build_default_registry

cfg = WorkforceConfig()
cfg.tools.sandbox = "workspace"
llm = MockProvider()
reg = build_default_registry(cfg)
mem = Memory(":memory:")
bus = Bus(workers=1)

task = Task(id="r1", title="Recruit for experiment", capability="recruit",
            description="I need an agent that turns ideas into structured experiment specs.")

need = AgentContext(goal="Run the next IXPANSION experiment", task=task)
spec_out = RecruiterAgent(llm, reg, mem, bus, "demo").run(need).output
print("recruiter spec:", spec_out.splitlines()[0] if spec_out else "")

agent = materialize_spec(spec_out, llm, reg, mem, bus, "demo")
out = agent.run(AgentContext(goal="Demo run", task=task)).output
print(f"spawned agent '{agent.name}' ran, output preview: {out[:90]}...")
bus.shutdown()
