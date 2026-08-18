"""X-04: recipe recommendation router — keyword-tag scoring, no LLM needed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .recipe import Recipe, RecipeError

RECIPES_DIR = Path(__file__).parent.parent / "content_output" / "recipes"


@dataclass
class RouteResult:
    recipe: Recipe
    scores: dict[str, int] = field(default_factory=dict)

    def label(self) -> str:
        ranked = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
        return " | ".join(f"{k}={v}" for k, v in ranked[:3])


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score(recipe: Recipe, tokens: set[str]) -> int:
    text = " ".join(recipe.tags).lower()
    return sum(1 for t in tokens if t in text)


def load_catalog(dir_path: str | Path = RECIPES_DIR) -> list[Recipe]:
    out: list[Recipe] = []
    for p in sorted(Path(dir_path).glob("*.yaml")):
        out.append(Recipe.load(p))
    if not out:
        raise RecipeError(f"no recipes found in {dir_path}")
    return out


def route(input_text: str, catalog: list[Recipe] | None = None) -> RouteResult:
    tokens = _tokens(input_text)
    recipes = catalog or load_catalog()
    scores = {r.name: _score(r, tokens) for r in recipes}
    best = max(recipes, key=lambda r: scores[r.name])
    return RouteResult(recipe=best, scores=scores)
