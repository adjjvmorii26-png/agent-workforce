"""Recipe engine (X-01): run recipe steps over an input, emit a report."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from .recipe import Recipe, RecipeError
from ..services.llm import make_provider


@dataclass
class ReportResult:
    recipe: str
    report_path: str
    provider: str
    steps: int
    status: str = "ok"


class Engine:
    def __init__(self, provider=None, output_dir: str = "ixpansion/content_output/reports") -> None:
        self.provider = provider or make_provider(mock=False)
        self.output_dir = Path(output_dir)

    def run(self, recipe: Recipe, input_text: str, *, out_name: str | None = None) -> ReportResult:
        if not input_text.strip():
            raise RecipeError("input is empty")
        outputs: dict[str, str] = {}
        prev = input_text
        for step in recipe.steps:
            prompt = self._format(step.prompt, input_text, prev, outputs)
            response = self.provider.chat(
                [
                    {"role": "system", "content": f"You are executing recipe step '{step.name}' of '{recipe.name}'. Follow the prompt exactly."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=step.max_tokens,
            )
            outputs[step.name] = response.text
            prev = response.text
        report = self._render(recipe, input_text, outputs)
        run_dir = self.output_dir / recipe.name
        run_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = run_dir / f"{out_name or stamp}.md"
        path.write_text(report, encoding="utf-8")
        return ReportResult(
            recipe=recipe.name,
            report_path=str(path),
            provider=self.provider.name,
            steps=len(recipe.steps),
        )

    @staticmethod
    def _format(template: str, input_text: str, prev: str, outputs: dict[str, str]) -> str:
        import string

        ctx = {"input": input_text, "prev": prev, **outputs}
        return string.Formatter().vformat(template, (), _DefaultMap(ctx))

    @staticmethod
    def _render(recipe: Recipe, input_text: str, outputs: dict[str, str]) -> str:
        parts = [recipe.catalog_header(), f"\n_Input:_ {input_text[:500]}\n"]
        for step in recipe.steps:
            parts.append(f"## {step.name}\n\n{outputs.get(step.name, '')}\n")
        return "\n".join(parts)


class _DefaultMap(dict):
    def __missing__(self, key: str):
        return f"{{{key}}}"
