"""Pulse: autopilot heartbeat — evolve, mark the moment, and record it."""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


def pulse(*, evolve_dir: str = "data/evolution", commit: bool = True) -> str:
    from .evolution import Evolver

    result = Evolver(population=6, generations=3, mock=True).run(out_dir=evolve_dir)
    pulse_path = Path("WORKSPACE_PULSE.md")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"# WORKSPACE PULSE — {stamp}\n\n"
        f"- breeding tank: gen {result.generations}, best fitness **{result.best.fitness:.1f}**"
        f" ({result.best.variant})\n"
        f"- evolution report: {result.report_path}\n"
        f"- alive: 14 static agents + spawned DNA (recruiter/evolution/chimera)\n"
        f"- next pulse: one more experiment, one more commit.\n"
    )
    pulse_path.write_text(text, encoding="utf-8")
    if commit:
        cmd = (
            "git add -A && "
            f"git -c user.name=Workforce -c user.email=workforce@localhost "
            f'commit -q -m "pulse: {stamp} — fitness {result.best.fitness:.1f}"'
        )
        subprocess.run(cmd, shell=True, check=False)
    return pulse_path.read_text(encoding="utf-8")
