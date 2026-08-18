"""Oracle: forecasts the next experiment from the run history in memory."""

from __future__ import annotations

import json
import time


def forecast(memory, limit: int = 5) -> str:
    runs = memory.list_runs(limit=50)
    tasks = []
    for r in runs:
        tasks.extend(memory.get_tasks(r["run_id"]))
    accepted = [t for t in tasks if t.get("status") == "accepted"]
    failed = [t for t in tasks if t.get("status") in ("failed", "blocked")]
    finished = [r for r in runs if r.get("finished_at") and r.get("created_at")]
    avg_runtime = (
        sum(r["finished_at"] - r["created_at"] for r in finished) / len(finished)
        if finished else 0.0
    )
    ok_rate = (len(accepted) / len(tasks) * 100) if tasks else 0.0
    lines = [
        "## Oracle — forecast from run history",
        f"- runs observed: {len(runs)}",
        f"- tasks observed: {len(tasks)}  (accept rate {ok_rate:.0f}%)",
        f"- avg run duration: {avg_runtime:.1f}s",
        f"- average review score: {sum(t.get('score') or 0 for t in tasks) / max(1, len(tasks)):.0f}/100",
    ]
    if runs:
        last = runs[0]
        lines.append(f"- last run: {last['run_id']} · {last['status']} · {last['goal'][:60]}")
    lines.append("- next planned pulse: run the next pending experiment, then evaluate it.")
    return "\n".join(lines)
