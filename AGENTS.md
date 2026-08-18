# AGENTS.md — standing directive for this workspace

## Worldview
This workspace is an **advanced simulation system for synchronizing organized
organisms** (a.k.a. organizations). The workforce (agents) and IXPANSION
(recipes/experiments) are the *cells* of one living system; runs are *pulses* that
keep it synchronized.

## Directives (always honored)
- **Stay active.** The workspace must keep producing artifacts, runs, and reports.
  Prefer action over asking. When idle, pick the next experiment and run it.
- **Apply your own experiment ideas.** Continuously execute and extend the backlog
  in `ixpansion/docs/experiments.md` (and `dashboard.html`). Don't wait for prompts.
- **Keep it coherent.** Every run should feed the simulation: plans become organisms,
  recipes become behaviors, reports become memory.
- **Be safe but bold.** Sandbox everything; `.git`/`.env` are protected; shell stays off
  unless explicitly enabled.

## How to operate
1. Pick an experiment (Phase 1→2→3 order from the backlog) or invent one on-theme.
2. Run it with the workforce (`python3 -m workforce run "<goal>" --mock`) and/or an
   IXPANSION recipe (`python3 -m ixpansion run "<input>" --recipe <name> --mock`).
3. Drop artifacts in `data/runs/`, `ixpansion/content_output/reports/`, or a themed
   file; update `dashboard.html`/docs as the system grows.
4. Commit progress locally; push when auth is available.
