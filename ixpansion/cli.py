"""IXPANSION CLI: run recipes, list catalog, list reports."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core.engine import Engine
from .core.recipe import Recipe
from .services.llm import make_provider
from .core.evaluate import evaluate_report

RECIPES = Path(__file__).parent / "content_output" / "recipes"
REPORTS = Path(__file__).parent / "content_output" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ixpansion", description="Recipe-based experiment platform")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run a recipe on an input")
    run.add_argument("input", help="raw input text (quote it)")
    run.add_argument("--recipe", default="summary", help="recipe name or YAML path (default: summary)")
    run.add_argument("--mock", action="store_true", help="offline deterministic provider")
    run.add_argument("--out", default=str(REPORTS), help="reports output dir")

    sub.add_parser("recipes", help="list catalog")
    sub.add_parser("reports", help="list generated reports")

    ev = sub.add_parser("evaluate", help="run a recipe and LLM-judge the report")
    ev.add_argument("input", help="raw input text (quote it)")
    ev.add_argument("--recipe", default="summary")
    ev.add_argument("--mock", action="store_true")
    ev.add_argument("--out", default=str(REPORTS))

    args = parser.parse_args(argv)
    if args.cmd == "recipes":
        for p in sorted(RECIPES.glob("*.yaml")):
            r = Recipe.load(p)
            print(f"{r.name:<16} {r.description} ({len(r.steps)} steps)")
        return 0
    if args.cmd == "reports":
        for p in sorted(REPORTS.glob("**/*.md")):
            print(p)
        return 0

    recipe_path = Path(args.recipe)
    if recipe_path.is_file():
        recipe = Recipe.load(recipe_path)
    else:
        candidates = list(RECIPES.glob(f"{args.recipe}.yaml"))
        if not candidates:
            print(f"error: no recipe named '{args.recipe}' in {RECIPES}")
            return 1
        recipe = Recipe.load(candidates[0])

    result = Engine(make_provider(mock=args.mock), output_dir=args.out).run(recipe, args.input)
    if args.cmd == "evaluate":
        report_text = Path(result.report_path).read_text(encoding="utf-8")
        ev = evaluate_report(report_text, args.input, mock=args.mock)
        print(f"[judge] relevance={ev.relevance:.0f} accuracy={ev.accuracy:.0f} structure={ev.structure:.0f} mean={ev.mean:.0f}")
        print(f"[judge] comments: {ev.comments[:160]}")
    print(f"[{result.status}] {result.recipe} -> {result.report_path} ({result.steps} steps via {result.provider})")
    return 0
