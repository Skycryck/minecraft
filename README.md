# Tickstats

**A free, zero-backend stats dashboard for your Minecraft server.**

Drop the raw stats JSON files your Minecraft server already writes into this repo, push, and GitHub Pages serves an interactive dashboard — per-player profiles, leaderboards, badges, charts, fun facts. No database, no server to maintain, no paid services.

## What you get

- **Per-player profiles** — playtime, deaths, mobs killed, blocks mined, distances by travel mode, items crafted, with automatic archetype detection (Miner, Fighter, Explorer, Builder, Farmer)
- **Badge system** — 33 badges + 2 meta badges across 4 tiers (Bronze → Silver → Gold → Diamond) with progression tooltips
- **12 leaderboards** grouped by activity category
- **Interactive charts** (Chart.js) — radar comparison, distance stacks, deaths aggregate, treemaps
- **Fun facts** auto-generated for each player
- **Deep-linkable views** — share a URL that opens straight to a specific player (`#player/<name>`)
- **Daily historical snapshots** — archived JSON under `snapshots/YYYY-MM-DD/`, ready for future time-series viz
- **Multi-server** — one dashboard per server folder, all hosted under the same repo

The UI is currently in French with English fallbacks in place; both languages are wired up through an i18n dict you can extend in `stats/assets/app.js`.

## Deploy your own

### 1. Create your repo

Click **"Use this template"** → **"Create a new repository"** at the top of this page. Make it **public** — GitHub Pages on the free plan only serves from public repos.

### 2. Enable GitHub Pages

In your new repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**. This must be set before the first deploy or the workflow will fail.

### 3. Locate your Minecraft stats files

Your Minecraft server writes one JSON file per player (named by UUID) into a `stats/` folder inside the world directory. Common paths:

| Setup | Path |
|---|---|
| Vanilla / Paper / Purpur | `<world-folder>/stats/*.json` |
| Forge / Fabric | `<world-folder>/stats/*.json` |
| Crafty Controller | `servers/<server-uuid>/world/players/stats/*.json` |
| Managed host (Aternos, Apex, etc.) | browse the world folder via the host's file manager |

You need *read access* to those files. That's it — nothing is modified on the server.

### 4. Add the JSON to your repo

Clone your new repo locally, then:

```bash
mkdir -p stats/my-server/data
cp /path/to/world/stats/*.json stats/my-server/data/
git add stats/my-server/data/
git commit -m "Add my-server stats"
git push
```

Replace `my-server` with any name you like — it becomes part of the URL and the dashboard title. You can have multiple servers side by side (`stats/smp/`, `stats/creative/`, etc.).

### 5. Wait for the deploy

Two GitHub Actions workflows run automatically:

1. `update-stats.yml` regenerates the HTML dashboard from your JSON
2. `static.yml` deploys the site to Pages

Watch the **Actions** tab for progress — the whole pipeline takes ~1–2 minutes. Your dashboard is then served at:

```
https://<your-username>.github.io/<repo-name>/stats/<server-name>/
```

### 6. Keep it updated

Whenever you want a refresh, copy the newer JSON files into the same `stats/<server-name>/data/` folder, commit, and push. The rest is automatic.

Automating the copy step is up to you — cron + rsync, a scheduled PowerShell task, a webhook from your host, or just manual copy/paste. A daily sync is plenty for most cases.

---

## How it works

No dependencies beyond Python 3.12+ stdlib. No pip install, no `node_modules`, no database.

### Tech stack

| Component | Technology |
|---|---|
| Generation | Python 3.12+ (stdlib only) |
| Frontend | HTML5 / CSS3 / vanilla JavaScript (ES6+) |
| Charts | Chart.js 4.4.1 |
| Fonts | JetBrains Mono, Space Grotesk |
| CI/CD | GitHub Actions |
| Hosting | GitHub Pages |

### Project structure

```
├── scripts/
│   ├── generate.py          # Main generator (JSON → HTML)
│   ├── minecraft/
│   │   └── badges.py        # Badge definitions + per-player tier computation
│   └── build_icons.py       # Pre-renders local Minecraft icon PNGs (stdlib only)
├── stats/
│   ├── assets/
│   │   ├── icons/           # Pre-rendered 256×256 Minecraft icon PNGs (committed)
│   │   ├── styles.css       # Shared dashboard stylesheet
│   │   └── app.js           # Shared dashboard runtime
│   └── <server-name>/       # One folder per server (repeatable)
│       ├── data/            # Raw JSON files (Minecraft stats)
│       ├── snapshots/       # Dated archive (YYYY-MM-DD/*.json), 1/day
│       ├── index.html       # Automatically generated dashboard
│       └── .uuid_cache.json # UUID → Mojang username cache
└── .github/workflows/
    ├── update-stats.yml     # Regenerates the dashboard on every change
    └── static.yml           # Deploys to GitHub Pages
```

### Pipeline

1. You push changes under `stats/*/data/**`
2. `update-stats.yml` detects which servers changed and runs `scripts/generate.py` for each
3. The regenerated `index.html` is auto-committed back to the repo (with `[skip ci]`)
4. `static.yml` picks up the new commit and deploys it to Pages

### UUID resolution

Minecraft UUIDs are resolved to usernames via the Mojang session-server API. Results are cached in `stats/<server>/.uuid_cache.json` to avoid rate-limiting (Mojang is aggressive about this) — commit the cache alongside the rest so CI doesn't re-hit the API every run.

### Unit conversion

| Minecraft raw | Converted to | Division |
|---|---|---|
| `play_time` / `play_one_minute` (ticks) | hours | ÷ 72,000 |
| `*_one_cm` (distances) | km | ÷ 100,000 |
| `damage_dealt` / `damage_taken` | hearts (display only) | ÷ 20 |

### Badges

33 standard badges + 2 meta badges (`all_rounder`, `legende`) across 8 categories: Mining, Combat, Survival, Exploration, Farming, Crafting, Daily life, and Prestige. Each badge has 4 progressive thresholds (Bronze → Silver → Gold → Diamond). Thresholds and tiers are computed server-side in `scripts/minecraft/badges.py`; `stats/assets/app.js` is a pure renderer — no badge logic lives in JS.

### Shared frontend assets

`stats/assets/styles.css` and `stats/assets/app.js` are shared across every server dashboard. `generate.py` only emits a ~30-line HTML shell that injects `window.PLAYERS_DATA` and loads these static files. Minecraft icons under `stats/assets/icons/` are pre-rendered 256×256 PNGs (via `scripts/build_icons.py`) committed to the repo so the dashboard has no runtime CDN dependency for its core visuals.

### Running the generator locally

If you want to iterate on a dashboard without going through CI:

```bash
python scripts/generate.py stats/<server-name>/data --title "Server Name"
```

Open the resulting `stats/<server-name>/index.html` in a browser. Same output as what CI produces.
