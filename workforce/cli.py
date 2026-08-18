"""Command-line interface for the workforce."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .agents import AGENT_LOOKUP
from .config import load_config
from .orchestrator import Workforce
from .bus import Event


def _print_event(event: Event) -> None:
    p = event.payload
    if event.type == "run_started":
        print(f"[run {p['run_id']}] started: {p['goal'][:80]}")
    elif event.type == "plan_ready":
        print(f"[plan] {p['task_count']} tasks")
    elif event.type == "task_started":
        print(f"  -> {p['task_id']} #{p['attempt']} ({p['agent']})")
    elif event.type == "review":
        print(f"     review {p['verdict']} score={p['score']:.0f} - {p['comments'][:100]}")
    elif event.type == "task_accepted":
        print(f"     OK {p['task_id']}")
    elif event.type == "task_revise":
        print(f"     retry {p['task_id']}")
    elif event.type == "task_blocked":
        print(f"     BLOCKED {p['task_id']}")
    elif event.type == "task_failed":
        print(f"     FAILED {p['task_id']}")
    elif event.type == "run_finished":
        print(f"[done] status={p['status']} report={p['report']}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workforce", description="Multi-agent workforce CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="execute a goal end-to-end")
    run.add_argument("goal")
    run.add_argument("--mock", action="store_true", help="offline deterministic provider")
    run.add_argument("--model")
    run.add_argument("--base-url")
    run.add_argument("--workers", type=int)
    run.add_argument("--iterations", type=int, help="max review attempts per task")
    run.add_argument("--out", default=None, help="artifact dir (default data/runs)")
    run.add_argument("--json", action="store_true", help="emit machine-readable result")
    run.add_argument("--quiet", action="store_true")

    plan = sub.add_parser("plan", help="show the plan for a goal")
    plan.add_argument("goal")
    plan.add_argument("--mock", action="store_true")

    agents = sub.add_parser("agents", help="list the workforce team")
    evolve = sub.add_parser("evolve", help="breed improved agents (evolution loop)")
    evolve.add_argument("--pop", type=int, default=6, help="population size")
    evolve.add_argument("--gens", type=int, default=3, help="generations")
    evolve.add_argument("--mock", action="store_true", help="deterministic offline fitness")
    evolve.add_argument("--out", default="data/evolution", help="report dir")
    splice = sub.add_parser("splice", help="create a chimera agent from two specialists")
    splice.add_argument("a", choices=["planner","researcher","coder","reviewer","summarizer","designer","qa","docsmith","critic","devops"])
    splice.add_argument("b", choices=["planner","researcher","coder","reviewer","summarizer","designer","qa","docsmith","critic","devops"])
    hive = sub.add_parser("hive", help="multiple specialists answer one question, then consensus")
    hive.add_argument("question")
    hive.add_argument("--mock", action="store_true")
    oracle = sub.add_parser("oracle", help="forecast from run history")
    pulse = sub.add_parser("pulse", help="autopilot heartbeat (evolve + record)")
    pulse.add_argument("--no-commit", action="store_true")
    status = sub.add_parser("status", help="show past runs")
    status.add_argument("run_id", nargs="?", default=None)

    init_ = sub.add_parser("init", help="write workforce.yaml and .env.example")
    clean_ = sub.add_parser("clean", help="delete runtime artifacts (data/, __pycache__, generated reports)")
    clean_.add_argument("--yes", action="store_true", help="skip confirmation")
    return parser


def _overrides(args: argparse.Namespace) -> dict:
    o: dict = {}
    if getattr(args, "mock", False):
        o["provider"] = "mock"
    if getattr(args, "model", None):
        o["model"] = args.model
    if getattr(args, "base_url", None):
        o["base_url"] = args.base_url
    if getattr(args, "workers", None):
        o["workers"] = args.workers
    if getattr(args, "iterations", None):
        o["max_attempts"] = args.iterations
    if getattr(args, "out", None):
        o["artifact_dir"] = args.out
    return o


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "splice":
        from .splice import splice as make_chimera

        from .llm import build_provider as _bp
        from .tools import build_default_registry as _reg
        from .memory import Memory as _Mem
        from .bus import Bus as _Bus

        cfg = load_config()
        reg = _reg(cfg)
        mem = _Mem(":memory:")
        bus = _Bus(workers=1)
        chimera = make_chimera(args.a, args.b, _bp(cfg.provider, cfg.llm), reg, mem, bus, "splice")
        print(f"chimera: {chimera.name} — {chimera.role}")
        print(f"caps: {', '.join(chimera.capabilities)}")
        print(f"DNA preview: {chimera.system_prompt()[:300]}")
        bus.shutdown()
        return 0

    if args.command == "hive":
        from .hive import run_hive

        from .llm import build_provider as _bp, MockProvider as _Mk
        from .tools import build_default_registry as _reg
        from .memory import Memory as _Mem
        from .bus import Bus as _Bus

        cfg = load_config()
        provider = _Mk() if args.mock else _bp(cfg.provider, cfg.llm)
        result = run_hive(args.question, provider, _reg(cfg), _Mem(":memory:"), _Bus(workers=1), "hive")
        print(f"hive: {len(result['views'])} views")
        for name, view in result["views"].items():
            print(f"  [{name}] {view[:70]}...")
        print("consensus:", result["consensus"][:200])
        return 0

    if args.command == "oracle":
        import os as _os
        from .oracle import forecast
        from .memory import Memory as _Mem

        cfg = load_config()
        _os.makedirs(_os.path.dirname(cfg.memory_db) or ".", exist_ok=True)
        print(forecast(_Mem(cfg.memory_db)))
        return 0

    if args.command == "pulse":
        from .pulse import pulse as _pulse

        print(_pulse(commit=not args.no_commit))
        return 0

    if args.command == "evolve":
        from .evolution import Evolver

        result = Evolver(population=args.pop, generations=args.gens, mock=args.mock).run(out_dir=args.out)
        print(result.summary())
        return 0

    if args.command == "agents":
        for name, cls in AGENT_LOOKUP.items():
            print(f"{name:<12} {cls.role:<20} caps: {', '.join(cls.capabilities)}")
        return 0

    if args.command == "init":
        for path, text in {
            "workforce.yaml": "provider: openai\nllm:\n  model: gpt-4o-mini\n  base_url: https://api.openai.com/v1\nworkers: 3\nmax_attempts: 3\n",
            ".env.example": "OPENAI_API_KEY=\nOPENAI_BASE_URL=https://api.openai.com/v1\nOPENAI_MODEL=gpt-4o-mini\n",
        }.items():
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"wrote {path}")
        return 0

    if args.command == "clean":
        import pathlib as _pl, shutil as _sh
        targets = ["data", "ixpansion/content_output/reports"]
        removed = 0
        for t in targets:
            root = _pl.Path(t)
            if not root.exists():
                continue
            has_user_files = t == "ixpansion/content_output/reports"
            for child in list(root.iterdir()):
                if has_user_files and child.name == ".gitkeep":
                    continue
                if child.is_dir():
                    _sh.rmtree(child)
                else:
                    child.unlink()
                removed += 1
        for pyc in list(_pl.Path(".").rglob("__pycache__")):
            _sh.rmtree(pyc)
            removed += 1
        print(f"clean: removed {removed} runtime items")
        return 0

    if args.command == "status":
        cfg = load_config()
        from .memory import Memory

        mem = Memory(cfg.memory_db)
        runs = mem.list_runs()
        if not runs:
            print("no runs yet")
            return 0
        target = args.run_id
        for r in runs:
            if target and r["run_id"] != target:
                continue
            print(f"{r['run_id']} {r['status']:<10} {r['goal'][:70]} report={r['report_path'] or '-'}")
        return 0

    cfg = load_config(overrides=_overrides(args))
    workforce = Workforce(cfg)
    if not args.quiet:
        workforce.bus.subscribe_all(_print_event)
    try:
        if args.command == "plan":
            run = workforce.run(args.goal, run_id="plan-preview")
            for t in run.tasks:
                print(f"{t.id} [{t.capability}] {t.title}")
            return 0
        result = workforce.run(args.goal)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=str))
    except KeyboardInterrupt:
        workforce.abort()
        print("\naborted", file=sys.stderr)
        return 130
    finally:
        workforce.shutdown()
    return 0
