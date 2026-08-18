"""Recipe model and YAML loading (X-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class RecipeError(Exception):
    pass


@dataclass
class RecipeStep:
    name: str
    prompt: str
    model: str | None = None
    max_tokens: int | None = None


@dataclass
class Recipe:
    name: str
    description: str = ""
    steps: list[RecipeStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "Recipe":
        p = Path(path)
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        name = data.get("name") or p.stem
        try:
            steps = [
                RecipeStep(
                    name=str(s.get("name", f"step{i}")),
                    prompt=str(s["prompt"]),
                    model=s.get("model"),
                    max_tokens=s.get("max_tokens"),
                )
                for i, s in enumerate(data.get("steps", []), 1)
            ]
        except (TypeError, KeyError) as exc:
            raise RecipeError(f"recipe {p} has invalid steps: {exc}") from exc
        if not steps:
            raise RecipeError(f"recipe {p} has no steps")
        return cls(
            name=name,
            description=str(data.get("description", "")),
            steps=steps,
            tags=[str(t) for t in (data.get("tags") or [])],
            source=str(p),
        )

    def catalog_header(self) -> str:
        return f"# {self.name} — {self.description}".rstrip()
