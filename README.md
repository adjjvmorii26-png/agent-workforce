# Workforce

> Central hub for the agent workforce: orchestrator, specialists, tooling, and docs in one repo.
> **Connectors:** workspace `workforce.yaml` (repo root sandbox) · GitHub (pending auth)

## Repository layout
```
workforce/        the package (orchestrator, agents, llm, tools, memory, bus, cli)
tests/            offline unit + end-to-end tests
workspace/        default sandbox for library-only use
workforce.yaml    workspace connector config (sandbox = repo root)
pyproject.toml    packaging / `workforce` console script
```

A finished, self-contained multi-agent workforce in ~2k lines of Python (stdlib + PyYAML only).

**Team:** `planner` (goal → task graph) · `researcher` (web facts/sources) · `coder` (sandboxed deliverable) · `reviewer` (pass/revise quality gate) · `summarizer` (final report).

**Pipeline:** plan → parallel task execution (dependency-aware) → review loop (up to N attempts) → report. Every run is persisted to SQLite (runs/tasks/messages/facts/artifacts), traced to `data/runs/<id>/trace.jsonl`, and streamed over an in-process pub/sub event bus.

## Quickstart

```bash
python3 -m unittest discover -s tests   # offline tests (no deps beyond PyYAML)
python3 -m workforce run "Build a Python CLI that shows weather" --mock   # offline demo
python3 -m pip install -e .             # optional: installs the `workforce` command
workforce run "Ship a dashboard"        # live OpenAI-compatible provider
```

Live mode reads `.env` / `workforce.yaml` / env vars:

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1   # works with OpenRouter, Ollama, vLLM, ...
export OPENAI_MODEL=gpt-4o-mini
python3 -m workforce run "your goal"
```

## CLI

| Command | Purpose |
|---|---|
| `workforce run "<goal>"` | Execute end-to-end (`--mock`, `--model`, `--workers`, `--iterations`, `--out`, `--json`) |
| `workforce plan "<goal>"` | Show the task plan only |
| `workforce agents` | List the team and capabilities |
| `workforce status [run_id]` | Show past runs |
| `workforce init` | Write `workforce.yaml` + `.env.example` |

## Config

`workforce.yaml` overrides defaults; env/CLI override YAML:

```yaml
provider: openai        # or "mock"
llm:
  model: gpt-4o-mini
  base_url: https://api.openai.com/v1
  temperature: 0.3
workers: 3              # parallel task workers
max_attempts: 3         # review iterations per task
tools:
  file_ops: true        # read/write/list inside sandbox only
  search_web: true
  fetch_url: true
  shell: false          # run_command is off unless you enable it
  sandbox: workspace
```

## Library API

```python
from workforce import Workforce
from workforce.config import load_config
w = Workforce(load_config())
result = w.run("your goal")
print(result.report_path)          # markdown report
for t in result.tasks:
    print(t.id, t.status, t.verdict, t.score)
w.shutdown()
```

## Workspace connection
The default `workforce.yaml` sets `tools.sandbox: .`, so agents read/write the repository itself (`.git` and `.env` are protected).

## Notes

- **Security:** file tools resolve paths inside the sandbox and reject escapes; shell execution is disabled by default.
- **Memory:** research findings are stored as long-term facts (`fact:research:<sha>`), so repeated runs on the same goal reuse prior knowledge.
- **Providers:** any OpenAI-compatible `/chat/completions` endpoint; no SDK dependency (stdlib `urllib`).
- **Mock mode:** deterministic offline provider — reviewer asks for one revision, then accepts — so the full loop can be demonstrated without an API key.

## IXPANSION (in this hub)

Run recipes to produce reports:

```bash
python3 -m ixpansion recipes                                   # catalog
python3 -m ixpansion run "Launch a rocket to Mars." --mock     # offline run
python3 -m ixpansion run "your input"                          # live (OPENAI_API_KEY)
```

Recipe YAML lives in `ixpansion/content_output/recipes/`, reports go to
`ixpansion/content_output/reports/`. Experiment backlog: `ixpansion/docs/experiments.md`.
