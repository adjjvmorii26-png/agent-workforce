# INVENTORY — dormant organisms & reuse plans

Discovered on this machine (scaffolds with no working code). Each is being
revived and reused by the central hub.

| Project | Path | Status | Reuse plan |
|---|---|---|---|
| GitHub Workspace Dashboard | `/sdcard/Download/nse-6403017623777166091-github-workspace-dashboard.zip` | revived | Real `dashboard.html` generated (reuses hub `dashboard.html`); shows hub agents + experiments. |
| ixpansion github seed | `/sdcard/Download/ixpansion_github_seed` | revived | `docs/experiments.md` seeded from hub IXPANSION backlog. |
| Morii | `/sdcard/Download/Morii` | revived | Labeled workspace node; usable as a content/seed source for IXPANSION recipes. |
| Notion | `/sdcard/Download/Notion` | revived | Labeled workspace node; usable as structured-doc source for IXPANSION `docs` recipes. |
| OpenClaw (platform) | `/sdcard/Download/openclaw-2026.7.1-2` | active | Reference for agent runtime/structure; not revived (already alive, drives mobile). |
| IXPANSION source | `/sdcard/Download/ixpansion_source_2026-08-08` | active | The source of truth mirrored into hub `ixpansion/`. |

## How the hub reuses everything
- **Agents** consume revived nodes as research/design inputs.
- **Recipes** (`summary`, `research-brief`, `organism-sync`, `redteam-scan`,
  `release-note`, `reuse-scan`) operate on any of these paths.
- **Reports** land in `data/runs/` and `ixpansion/content_output/reports/`.
- **`dashboard.html`** visualizes revived nodes so the simulation stays legible.
