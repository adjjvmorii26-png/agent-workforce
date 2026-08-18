"""The workforce orchestrator: plan -> schedule -> execute -> review -> report."""

from __future__ import annotations

import hashlib
import json
import pathlib
import threading
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any

from .agents import AgentContext, build_team, resolve_agent_name
from .bus import Bus, Event
from .config import WorkforceConfig
from .llm import LLMProvider, build_provider
from .memory import Memory
from .models import Task, TaskStatus, parse_tasks
from .tools import build_default_registry
from .tracing import Tracer

REVIEW_FREE = {"plan"}
MAX_REVIEW_WORDS = 40_000


@dataclass
class RunResult:
    run_id: str
    goal: str
    status: str = "running"
    report_path: str = ""
    plan_path: str = ""
    tasks: list[Task] = field(default_factory=list)
    task_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "status": self.status,
            "report_path": self.report_path,
            "plan_path": self.plan_path,
            "tasks": [self._task_dict(t) for t in self.tasks],
            "task_results": self.task_results,
        }

    @staticmethod
    def _task_dict(t: Task) -> dict[str, Any]:
        return {
            "id": t.id,
            "title": t.title,
            "capability": t.capability,
            "status": t.status.value,
            "attempt": t.attempt,
            "depends_on": t.depends_on,
            "verdict": t.verdict,
            "score": t.score,
            "comments": t.comments,
            "output": t.output[:2000],
        }


class Workforce:
    """A complete agent workforce with one orchestrator and five specialists."""

    def __init__(
        self,
        config: WorkforceConfig | None = None,
        *,
        provider: LLMProvider | None = None,
        memory: Memory | None = None,
        bus: Bus | None = None,
    ) -> None:
        self.config = config or WorkforceConfig()
        self.bus = bus or Bus(workers=max(1, self.config.workers + 2))
        self.provider = provider or build_provider(self.config.provider, self.config.llm)
        self.memory = memory or Memory(self.config.memory_db)
        self.registry = build_default_registry(self.config)
        self._abort = threading.Event()

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def run(self, goal: str, *, run_id: str | None = None, max_attempts: int | None = None) -> RunResult:
        """Execute a goal end-to-end and return the run result."""
        run_id = run_id or uuid.uuid4().hex[:10]
        self.config.run_id = run_id
        self.config.goal = goal
        self._abort.clear()

        run_dir = pathlib.Path(self.config.artifact_dir) / run_id
        tracer = Tracer(run_dir)
        self._tracer = tracer
        self._team = build_team(self.provider, self.registry, self.memory, self.bus, run_id)
        attempts = max_attempts or self.config.max_attempts

        self.memory.start_run(run_id, goal, self.provider.name, self._model_name())
        self._publish("run_started", run_id=run_id, goal=goal, provider=self.provider.name)
        tracer.event("run_started", run_id=run_id, goal=goal)

        try:
            tasks = self._plan(goal, run_id, tracer)
            results = self._execute(tasks, goal, run_id, attempts, tracer)
            report_path, plan_path = self._report(tasks, goal, run_id, tracer)
            status = "completed"
            self.memory.finish_run(run_id, status, str(report_path))
            tracer.event("run_finished", run_id=run_id, status=status)
            self._publish(
                "run_finished",
                run_id=run_id,
                status=status,
                report=str(report_path),
            )
            return RunResult(
                run_id=run_id,
                goal=goal,
                status=status,
                report_path=str(report_path),
                plan_path=str(plan_path),
                tasks=tasks,
                task_results=results,
            )
        except Exception as exc:
            self.memory.finish_run(run_id, "failed")
            tracer.event("run_failed", run_id=run_id, error=str(exc))
            self._publish("run_failed", run_id=run_id, error=str(exc))
            raise

    def abort(self) -> None:
        self._abort.set()

    def shutdown(self) -> None:
        self.bus.shutdown()

    # ------------------------------------------------------------------ #
    # planning
    # ------------------------------------------------------------------ #
    def _plan(self, goal: str, run_id: str, tracer: Tracer) -> list[Task]:
        planner = self._team["planner"]
        context = AgentContext(goal=goal, task=_synthetic_task("plan", "Plans this goal", goal))
        result = planner.run(context)
        good = result.output.splitlines()
        tasks: list[Task] = []

        if good and good[0].startswith("ERROR planning"):
            raise RuntimeError(good[0])
        for line in good:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            tasks.append(
                Task(
                    id=parts[0],
                    capability=parts[1],
                    title=parts[2],
                    description="",
                    depends_on=[d for d in parts[3].split(",") if d],
                )
            )
        if not tasks:
            raise RuntimeError("Planner produced no usable tasks")

        # hydrate descriptions
        self._hydrate_descriptions(tasks, goal)
        self._publish("plan_ready", run_id=run_id, task_count=len(tasks))
        tracer.event("plan_ready", run_id=run_id, tasks=[t.id for t in tasks])
        self._write_plan(tasks, goal, run_id)
        return tasks

    def _hydrate_descriptions(self, tasks: list[Task], goal: str) -> None:
        """Fill description from planner output or a sensible default."""
        for t in tasks:
            if not t.description:
                t.description = f"Contribute to the goal: {goal[:300]}"

    def _write_plan(self, tasks: list[Task], goal: str, run_id: str) -> pathlib.Path:
        plan_path = pathlib.Path(self.config.artifact_dir) / run_id / "plan.md"
        lines = [f"# Plan for: {goal}", ""]
        for t in tasks:
            deps = f" (after {', '.join(t.depends_on)})" if t.depends_on else ""
            lines.append(f"- **{t.id}** [{t.capability}]{deps}: {t.title} — {t.description}")
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.memory.add_artifact(run_id, str(plan_path), "plan")
        return plan_path

    # ------------------------------------------------------------------ #
    # execution
    # ------------------------------------------------------------------ #
    def _execute(
        self,
        tasks: list[Task],
        goal: str,
        run_id: str,
        max_attempts: int,
        tracer: Tracer,
    ) -> list[dict[str, Any]]:
        todo = {t.id: t for t in tasks}
        completed: dict[str, Task] = {}
        results: list[dict[str, Any]] = []
        facts = self._recall_facts(goal)
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=max(1, self.config.workers), thread_name_prefix="task") as pool:
            futures: dict[Future, str] = {}
            while todo:
                if self._abort.is_set():
                    break
                ready = [
                    tid
                    for tid, t in todo.items()
                    if all(
                        d in completed and completed[d].status is TaskStatus.ACCEPTED
                        for d in t.depends_on
                    )
                ]
                if not ready:
                    for tid, t in todo.items():
                        t.status = TaskStatus.BLOCKED
                        completed[tid] = t
                        self._publish("task_blocked", run_id=run_id, task_id=tid)
                        tracer.event("task_blocked", task_id=tid)
                        results.append(self._result_dict(t))
                    break
                for tid in ready:
                    future = pool.submit(
                        self._execute_one,
                        todo[tid],
                        goal,
                        run_id,
                        max_attempts,
                        tracer,
                        facts,
                        lock,
                    )
                    futures[future] = tid
                    del todo[tid]
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    tid = futures.pop(future)
                    task = future.result()
                    completed[tid] = task
                    results.append(self._result_dict(task))
                if not futures and todo:
                    continue
        return results

    def _execute_one(
        self,
        task: Task,
        goal: str,
        run_id: str,
        max_attempts: int,
        tracer: Tracer,
        facts: dict[str, Any],
        lock: threading.Lock,
    ) -> Task:
        agent_name = resolve_agent_name(task.capability)
        feedback: str | None = None
        last_review_comments = ""

        for attempt in range(1, max_attempts + 1):
            if self._abort.is_set():
                break
            task.status = TaskStatus.RUNNING
            task.attempt = attempt
            task.input = self._task_input(task, goal, lock)
            self._upsert(task, run_id)
            self._publish(
                "task_started",
                run_id=run_id,
                task_id=task.id,
                agent=agent_name,
                attempt=attempt,
            )
            tracer.event("task_started", task_id=task.id, agent=agent_name, attempt=attempt)

            agent = self._team[agent_name]
            context = AgentContext(goal=goal, task=task, feedback=feedback, facts=facts)
            result = agent.run(context)
            task.output = result.output
            self._upsert(task, run_id)

            if task.capability.lower() in REVIEW_FREE:
                task.status = TaskStatus.ACCEPTED
                task.verdict = "pass"
                task.score = 100.0
                self._publish("task_accepted", run_id=run_id, task_id=task.id, agent=agent_name)
                tracer.event("task_accepted", task_id=task.id)
                break

            review_comments, verdict, score = self._review(
                task, goal, run_id, tracer, facts
            )

            if verdict == "pass":
                task.status = TaskStatus.ACCEPTED
                task.verdict = "pass"
                task.score = score
                task.comments = review_comments
                self._upsert(task, run_id)
                self._publish(
                    "task_accepted",
                    run_id=run_id,
                    task_id=task.id,
                    agent=agent_name,
                    score=score,
                )
                tracer.event("task_accepted", task_id=task.id, score=score)
                self._remember_facts(goal, task)
                break

            task.verdict = "revise"
            task.score = score
            task.comments = review_comments
            feedback = review_comments
            last_review_comments = review_comments
            self._publish(
                "task_revise",
                run_id=run_id,
                task_id=task.id,
                attempt=attempt,
                comments=review_comments,
            )
            tracer.event("task_revise", task_id=task.id, attempt=attempt)
            self._upsert(task, run_id)
        else:
            task.status = TaskStatus.FAILED
            task.verdict = "revise"
            task.comments = last_review_comments or "exhausted review attempts"
            self._upsert(task, run_id)
            self._publish("task_failed", run_id=run_id, task_id=task.id, comments=task.comments)
            tracer.event("task_failed", task_id=task.id)

        return task

    def _review(self, task: Task, goal: str, run_id: str, tracer: Tracer, facts: dict[str, Any]) -> tuple[str, str, float]:
        reviewer = self._team["reviewer"]
        ctx = AgentContext(goal=goal, task=task, facts=facts)
        review_out = reviewer.run(ctx).output
        verdict, score, comments = "revise", 0.0, review_out
        parts = review_out.split(" | ", 2)
        if len(parts) == 3:
            verdict = parts[0].strip().lower()
            if verdict not in {"pass", "revise"}:
                verdict = "revise"
            try:
                score = float(parts[1])
            except ValueError:
                score = 0.0
            comments = parts[2][:1000]
        self._publish(
            "review",
            run_id=run_id,
            task_id=task.id,
            verdict=verdict,
            score=score,
            comments=comments,
        )
        tracer.event("review", task_id=task.id, verdict=verdict, score=score)
        return comments, verdict, score

    # ------------------------------------------------------------------ #
    # reporting
    # ------------------------------------------------------------------ #
    def _report(self, tasks: list[Task], goal: str, run_id: str, tracer: Tracer) -> tuple[pathlib.Path, pathlib.Path]:
        context_inputs = "\n\n".join(
            f"## Task {t.id} ({t.capability}, {t.status.value})\n{t.output[:3000]}"
            for t in tasks
        )
        summarizer = self._team["summarizer"]
        synth = Task(
            id="final",
            title="Write the final report",
            capability="summarize",
            description=context_inputs,
        )
        try:
            ctx = AgentContext(goal=goal, task=synth, facts={})
            summary = summarizer.run(ctx).output
        except Exception as exc:  # never let reporting kill the run
            summary = f"Report generation failed: {exc}"

        run_dir = pathlib.Path(self.config.artifact_dir) / run_id
        report_path = run_dir / "report.md"
        tasks_path = run_dir / "tasks.jsonl"
        report_path.write_text(summary, encoding="utf-8")
        with tasks_path.open("w", encoding="utf-8") as fh:
            for t in tasks:
                fh.write(json.dumps(self._result_dict(t), default=str) + "\n")
        self.memory.add_artifact(run_id, str(report_path), "report")
        self.memory.add_artifact(run_id, str(tasks_path), "tasks")
        tracer.event("report_written", path=str(report_path))
        return report_path, run_dir / "plan.md"

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _upsert(self, task: Task, run_id: str) -> None:
        self.memory.upsert_task(
            run_id,
            task.id,
            task.capability,
            task.title,
            status=task.status.value,
            attempt=task.attempt,
            input_=task.input,
            output=task.output,
            verdict=task.verdict,
            score=task.score,
            comments=task.comments,
            is_final=task.status is TaskStatus.ACCEPTED,
        )

    @staticmethod
    def _result_dict(t: Task) -> dict[str, Any]:
        return {
            "id": t.id,
            "title": t.title,
            "capability": t.capability,
            "status": t.status.value,
            "attempt": t.attempt,
            "verdict": t.verdict,
            "score": t.score,
            "comments": t.comments,
            "output": t.output,
        }

    def _task_input(self, task: Task, goal: str, lock: threading.Lock) -> str:
        parts = [f"Goal: {goal}", f"Task: {task.title}", task.description]
        with lock:  # reads shared keys; lock is cheap insurance
            deps = self.memory.get_tasks(self.config.run_id)
            dep_outputs = [d for d in deps if d["task_id"] in task.depends_on and d["output"]]
        for dep in dep_outputs:
            parts.append(f"\n## Output of dependency {dep['task_id']}\n{dep['output'][:3000]}")
        return "\n".join(parts)

    def _recall_facts(self, goal: str) -> dict[str, Any]:
        key = _goal_key(goal)
        return self.memory.recall(key) or {}

    def _remember_facts(self, goal: str, task: Task) -> None:
        key = _goal_key(goal)
        facts = self.memory.recall(key) or {}
        facts[task.id] = {
            "title": task.title,
            "capability": task.capability,
            "output": task.output[:2000],
        }
        self.memory.remember(key, facts, ttl=30 * 24 * 3600)

    def _model_name(self) -> str:
        return getattr(self.config.llm, "model", "")

    def _publish(self, type_: str, **payload: Any) -> None:
        self.bus.publish(Event(type=type_, payload=payload, source="orchestrator"))


def _synthetic_task(task_id: str, title: str, description: str) -> Task:
    return Task(id=task_id, title=title, capability="plan", description=description)


def _goal_key(goal: str) -> str:
    digest = hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16]
    return f"fact:research:{digest}"
