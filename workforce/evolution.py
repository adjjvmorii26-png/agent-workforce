"""Breeding Tank — an evolution loop for agent organisms.

A population of DynamicAgents (each a mutation of a base "gene pool") is
benchmarked on tasks, judged, selected, and bred. Fitness improves across
generations, and the fittest survivor's DNA (system prompt) is reported.

Offline mode uses deterministic variant scoring so the whole loop is testable
and demoable without an LLM key.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from .models import Task, extract_json
from .tools import build_default_registry
from .memory import Memory
from .bus import Bus
from .config import WorkforceConfig
from .llm import MockProvider

# "DNA" — genes every organism is seeded from
GENE_POOL = [
    ("researcher", ["research"], "You gather accurate, sourced facts for a topic."),
    ("coder", ["code"], "You write concrete, runnable deliverables for a task."),
    ("designer", ["design"], "You build beautiful, self-contained HTML deliverables."),
    ("critic", ["redteam"], "You surface risks, failure modes, and mitigations."),
    ("summarizer", ["summarize"], "You turn scattered outputs into a crisp report."),
]

# mutations: (tag, instruction add-on, deterministic offline fitness bonus)
VARIANT_LIBRARY = [
    ("default", "", 0.0),
    ("concise", "Be extremely concise; cut all filler.", 5.0),
    ("sourced", "Always cite sources and state confidence levels.", 4.0),
    ("structured", "Prefer tables, lists, and structured output.", 3.0),
    ("defensive", "Including failure modes and mitigations.", 4.0),
    ("creative", "Be bold; propose 3 alternatives.", 2.0),
]

TASKS = [
    "Summarize the hub's 14-agent workforce in 3 sentences.",
    "Design a one-page HTML dashboard for experiment tracking.",
    "List the biggest risks of an autonomous self-pushing repository.",
]


@dataclass
class Organism:
    name: str
    role: str
    capabilities: list[str]
    system_prompt: str
    variant: str
    generation: int
    parent: str = "seed"
    boost: float = 0.0
    fitness: float = 0.0
    scores: list[float] = field(default_factory=list)

    def dna_id(self) -> str:
        return f"{self.generation}:{self.name}:{self.variant}"


@dataclass
class EvolutionResult:
    generations: int
    population: int
    best: Organism
    curve: list[tuple[int, float]]
    report_path: str

    def summary(self) -> str:
        bars = "\n".join(
            f"  Gen {g}  {'█' * max(1, int(f / 100 * 20)):<20} {f:5.1f}" for g, f in self.curve
        )
        return (
            f"Breeding Tank: {self.generations} generations, best fitness {self.best.fitness:.1f}\n"
            f"  winner: {self.best.name} ({self.best.variant}) {self.best.role}\n"
            f"{bars}\n"
            f"  report: {self.report_path}"
        )


class Evolver:
    def __init__(self, *, population: int = 6, generations: int = 3, mock: bool = True, seed: int = 7) -> None:
        self.population = population
        self.generations = generations
        self.mock = mock
        self.rng = random.Random(seed)

    def run(self, out_dir: str = "data/evolution") -> EvolutionResult:
        survivors = [self._seed(i) for i in range(self.population)]
        curve: list[tuple[int, float]] = []
        lineage: list[dict] = []

        for gen in range(self.generations):
            for org in survivors:
                org.generation = gen
                org.scores = [self._fitness(org, TASKS[(gen + i) % len(TASKS)]) for i in range(2)]
                org.fitness = sum(org.scores) / len(org.scores)
                lineage.append(
                    {
                        "generation": gen,
                        "name": org.name,
                        "parent": org.parent,
                        "variant": org.variant,
                        "fitness": round(org.fitness, 2),
                    }
                )
            curve.append((gen, max(s.fitness for s in survivors)))
            survivors = self._select_and_breed(survivors, gen)

        best = max(survivors, key=lambda o: o.fitness)
        report = self._report(curve, lineage, best)
        path = Path(out_dir) / f"evolution-{int(time.time())}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        return EvolutionResult(self.generations, self.population, best, curve, str(path))

    # ------------------------------------------------------------------ #
    def _seed(self, index: int) -> Organism:
        gene, caps, prompt = GENE_POOL[index % len(GENE_POOL)]
        variant_name, addon, _ = VARIANT_LIBRARY[self.rng.randrange(len(VARIANT_LIBRARY))]
        return Organism(
            name=f"{gene}-{index}",
            role=f"{gene} mutant",
            capabilities=list(caps),
            system_prompt=self._mutate(prompt, addon),
            variant=variant_name,
            generation=0,
        )

    def _select_and_breed(self, survivors: list[Organism], gen: int) -> list[Organism]:
        ranked = sorted(survivors, key=lambda o: o.fitness, reverse=True)
        top = ranked[: max(2, self.population // 2)]
        children: list[Organism] = []
        for i in range(self.population - len(top)):
            parent = top[i % len(top)]
            # offspring inherit the fittest DNA, sometimes with a fresh mutation
            if self.rng.random() < 0.7:
                variant_name, addon, _ = next(v for v in VARIANT_LIBRARY if v[0] == parent.variant)
            else:
                variant_name, addon, _ = VARIANT_LIBRARY[self.rng.randrange(len(VARIANT_LIBRARY))]
            children.append(
                Organism(
                    name=f"{parent.name}-c{i}",
                    role=parent.role,
                    capabilities=list(parent.capabilities),
                    system_prompt=self._mutate(parent.system_prompt, addon),
                    variant=variant_name,
                    generation=gen + 1,
                    parent=parent.name,
                    boost=parent.boost + 2.0,
                )
            )
        return top + children

    def _fitness(self, org: Organism, task: str) -> float:
        if not self.mock:
            from .llm import OpenAICompatProvider
            from .config import LLMConfig
            import os

            provider = OpenAICompatProvider(
                LLMConfig(
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                )
            )
            resp = provider.chat(
                [
                    {"role": "system", "content": "You are an EVALUATOR. Reply ONLY JSON: {\"score\": 0-100}"},
                    {"role": "user", "content": f"Task: {task}\n\nAgent system prompt: {org.system_prompt}"},
                ],
                json_mode=True,
            )
            return float((extract_json(resp.text) or {}).get("score", 50))
        # offline: deterministic variant score + tiny prompt-entropy jitter
        bonus = next(v for t, _, v in VARIANT_LIBRARY if t == org.variant)
        jitter = (len(org.system_prompt) % 7) / 10.0
        return 40 + bonus + jitter + org.boost

    @staticmethod
    def _mutate(prompt: str, addon: str) -> str:
        return f"{prompt}\nRule: {addon}".strip() if addon else prompt

    def _report(self, curve: list[tuple[int, float]], lineage: list[dict], best: Organism) -> str:
        lines = [f"# Breeding Tank — evolution run", ""]
        lines.append(f"- generations: {self.generations}")
        lines.append(f"- population: {self.population}")
        lines.append(f"- winner: **{best.name}** ({best.variant}) — fitness {best.fitness:.1f}")
        lines.append(f"- survivor DNA: `{best.system_prompt}`")
        lines.append("")
        lines.append("## Fitness curve")
        for g, f in curve:
            lines.append(f"`Gen {g}` {'█' * int(f * 5)} {f:5.1f}")
        lines.append("")
        lines.append("## Lineage")
        lines.append("| gen | organism | parent | variant | fitness |")
        lines.append("|---|---|---|---|---|")
        for row in lineage[-12:]:
            lines.append(f"| {row['generation']} | {row['name']} | {row['parent']} | {row['variant']} | {row['fitness']} |")
        return "\n".join(lines) + "\n"
