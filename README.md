# Minecraft Stats Dashboard

Interactive web dashboard that turns raw Minecraft server stats files into visual dashboards, deployed automatically via GitHub Pages.

## Features

- **Player profiles** — Playtime, deaths, mobs killed, blocks mined, distances traveled, items crafted, with automatic archetype detection (Miner, Fighter, Explorer, Builder, Farmer)
- **Badge system** — 32 badges across 4 tiers (Bronze → Silver → Gold → Diamond), with progression tooltips on hover
- **Interactive visualizations** — Chart.js charts: playtime breakdown, distances by travel mode, blocks mined, mobs killed, estimated time spent per activity
- **Leaderboards** — Rankings across 15+ metrics
- **Fun facts** — Fun facts automatically generated for each player
- **Automated pipeline** — Push JSON data → GitHub Actions regenerates the HTML → deployed to GitHub Pages

## Tech stack

| Component | Technology |
|---|---|
| Generation | Python 3.12+ (stdlib only) |
| Frontend | HTML5 / CSS3 / vanilla JavaScript (ES6+) |
| Charts | Chart.js 4.4.1 |
| Fonts | JetBrains Mono, Space Grotesk |
| CI/CD | GitHub Actions |
| Hosting | GitHub Pages |
| Local sync | PowerShell |

## Project structure

```
├── scripts/
│   ├── generate.py          # Main generator (JSON → HTML)
│   ├── minecraft/
│   │   └── badges.py        # Badge definitions + per-player tier computation
│   ├── build_icons.py       # Pre-renders local Minecraft icon PNGs (stdlib only)
│   └── sync-stats.ps1       # Windows sync script
├── stats/
│   ├── assets/
│   │   ├── icons/           # Pre-rendered 256×256 Minecraft icon PNGs (committed)
│   │   ├── styles.css       # Shared dashboard stylesheet
│   │   └── app.js           # Shared dashboard runtime
│   └── <server-name>/
│       ├── data/            # Raw JSON files (Minecraft stats)
│       ├── index.html       # Automatically generated dashboard
│       └── .uuid_cache.json # UUID → Mojang username cache
└── .github/workflows/
    ├── update-stats.yml     # Regenerates the dashboard on every change
    └── static.yml           # Deploys to GitHub Pages
```

## Usage

### Requirements

- Python 3.12+
- Git

### Generate a dashboard locally

```bash
python scripts/generate.py stats/<server-name>/data --title "Server Name"
```

The file `stats/<server-name>/index.html` is generated automatically.

### Sync stats from a server (Windows)

```powershell
.\scripts\sync-stats.ps1
```

This script copies modified JSON files from Crafty Controller, commits and pushes to GitHub.

### CI/CD pipeline

1. `sync-stats.ps1` copies the JSON files and pushes to GitHub
2. GitHub Actions (`update-stats.yml`) detects changes in `stats/*/data/`
3. `generate.py` regenerates the `index.html` files
4. GitHub Actions (`static.yml`) deploys to GitHub Pages

## Technical details

### UUID resolution

Minecraft UUIDs are resolved to usernames via the Mojang Session Server API, with a local cache (`.uuid_cache.json`) to avoid rate-limiting.

### Unit conversion

| Minecraft unit | Conversion |
|---|---|
| `play_one_minute` (ticks) | ÷ 72,000 → hours |
| `*_one_cm` (distances) | ÷ 100,000 → km |
| `damage_*` | ÷ 20 → hearts |

### Badges

The 32 badges span 8 categories: Mining, Combat, Survival, Exploration, Farming, Crafting, Daily life, and Prestige. Each badge has 4 progressive thresholds with a visual progression indicator. Thresholds and tiers are computed in `scripts/minecraft/badges.py`; `app.js` is a pure renderer.

### Shared frontend assets

`stats/assets/styles.css` and `stats/assets/app.js` are shared across every server dashboard — `generate.py` only emits a small HTML shell that injects `window.PLAYERS_DATA` and loads these static files. Minecraft icons under `stats/assets/icons/` are pre-rendered locally (via `scripts/build_icons.py`) and committed to the repo so the dashboard is self-contained.
