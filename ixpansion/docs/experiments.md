# IXPANSION — Experiment Ideas

IXPANSION is an experiment platform for turning raw inputs into structured,
published content ("recipes" produce "reports"). The scaffold points at:

- `src/core` — domain logic (recipes, reports, pipelines)
- `src/services` — integrations (LLM providers, APIs, storage)
- `api/` — experiment runner / content endpoints
- `content_output/recipes` + `content_output/reports` — artifacts
- `tests/` — evaluation harness
- `.github/workflows` — scheduled smoke runs

Every experiment below is designed to be run with the workforce in
`/root/Hub_spot` (plan → research → code → review loop) and to leave a real
artifact in `content_output/`.

---


## Progress
- **X-01** done — recipe engine + CLI implemented (committed).
- **X-02** done — recipe catalog of 5 reusable recipes committed (`summary`, `research-brief`, `organism-sync`, `redteam-scan`, `release-note`).
- Next up: **X-03** LLM-judge evaluation harness.

## Principles

1. **One hypothesis per experiment** — change one variable at a time.
2. **Every run must produce a report** in `content_output/reports/<experiment>/`.
3. **Cheap first, correct later** — default to the cheapest model that answers the
   question, then scale.
4. **Automate the loop** — a recipe + CI trigger should re-run experiments on a
   schedule, no human in the middle.

---

## Phase 1 — Prove the pipeline (quick wins, ~1 session each)

### X-01 Baseline recipe engine
- **Hypothesis:** a deterministic recipe (steps + slot prompts) can turn a raw
  input (URL, note, dataset) into a usable structured report with zero code per run.
- **Build:** `src/core/recipe.py` (recipe schema), `src/core/engine.py` (step
  runner), CLI: `ixpansion run <recipe> <input>`.
- **Measure:** end-to-end success rate, time, cost, report schema validity.
- **Success:** 90%+ of runs produce a schema-valid report in `content_output/reports`.

### X-02 Recipe catalog
- **Hypothesis:** a small catalog of 5 reusable recipes (brief, summary, pricing,
  how-to, risk) covers most inputs users care about.
- **Build:** `content_output/recipes/*.yaml` + a registry in `src/core/catalog.py`.
- **Measure:** coverage of a test corpus (10 sample inputs per recipe).
- **Success:** every corpus item maps to ≥1 recipe with no manual edits.

### X-03 Evaluation harness
- **Hypothesis:** LLM-as-judge scoring (relevance, accuracy, structure) tracks
  quality well enough to rank recipe changes.
- **Build:** `src/services/evaluator.py` (judge prompts, rubric), `tests/eval/`.
- **Measure:** inter-rater agreement with human labels on 30 samples.
- **Success:** judge score mean abs error ≤ 10 pts vs human.

---

## Phase 2 — Make it adaptive (medium bets, 1–2 sessions each)

### X-04 Recipe recommendation
- **Hypothesis:** routing an input to the right recipe by keywords+topic beats
  "ask the user" and beats "only default recipe".
- **Build:** `src/services/router.py` (embed or classify → recipe), blended A/B.
- **Measure:** human preference rate + judge scores across 3 routing strategies.
- **Success:** router beats default recipe by ≥15% judge points.

### X-05 Self-revising reports
- **Hypothesis:** one critique pass (reviewer agent) on draft reports improves
  judged quality more than running the same model twice.
- **Build:** loop in `src/core/engine.py`: draft → critique → revise (max 2).
- **Measure:** judge score before/after; cost delta.
- **Success:** +10 pts quality for <2× cost.

### X-06 Feedback flywheel
- **Hypothesis:** thumbs-up/down + edits from a small pilot group measurably
  steer recipe outputs within 50 runs.
- **Build:** `api/feedback` endpoint, `src/services/feedback_store.py`, weekly
  recipe adjust job in CI.
- **Measure:** rising accept-rate trend over 4 weeks.
- **Success:** +20% accept rate vs baseline.

---

## Phase 3 — Expand the surface (bigger bets)

### X-07 Multi-source synthesis
- **Hypothesis:** merging 3+ sources (URL, doc, dataset) with a dedicated
  synthesis recipe yields reports that beat any single-source report.
- **Build:** `src/services/ingest/` (fetch, parse, normalize), synthesis recipe.
- **Measure:** judge scores multi vs best-single-source on 20 topics.
- **Success:** multi-source wins ≥70% of comparisons.

### X-08 Model/provider A/B bench
- **Hypothesis:** on IXPANSION's workload the cheapest model can be chosen per
  step (route, draft, critique) without losing quality.
- **Build:** `src/services/bench.py` — run same corpus across providers/models,
  log cost/latency/quality to `content_output/reports/bench/`.
- **Measure:** quality/cost pareto frontier.
- **Success:** identify a config that cuts cost ≥40% at ≤5 pts quality loss.

### X-09 Scheduled autopilot
- **Hypothesis:** nightly CI runs of the whole catalog (with alerts on quality
  dips) keep reports current at near-zero maintenance.
- **Build:** `.github/workflows/experiments.yml` (cron: run, eval, report,
  notify on regressions).
- **Success:** 4 consecutive weeks with no manual intervention.

### X-10 Public API + gallery
- **Hypothesis:** exposing a tiny API (`POST /run`, `GET /reports/:id`) with a
  gallery of generated reports creates pull for the platform.
- **Build:** `api/main.py` (FastAPI-free, stdlib server OK), `api/gallery.py`.
- **Measure:** usage, repeat runs.
- **Success:** ≥1 external consumer running ≥10 reports.

---

## Running the ideas

Use the workforce in `/root/Hub_spot` as the experiment executor:

```bash
cd /root/Hub_spot
python3 -m workforce run "Scaffold IXPANSION experiment X-01: recipe engine in src/core with CLI and a sample report" --mock
```

Each run plans, researches, implements, reviews, and drops a report into
`data/runs/<id>/report.md` — copy accepted artifacts into
`sdcard/Download/ixpansion_source_2026-08-08` (or repoint `tools.sandbox` there
in `workforce.yaml` to write directly).

**Suggested order:** X-01 → X-03 → X-02 → X-05 → X-04 → X-06 → X-08 → X-07 → X-09 → X-10.
Pick one per session, measure, commit, ship.
