# Tickstats

Static Minecraft stats dashboards generated from Minecraft server stats JSON files, deployed via GitHub Pages.

## Commands

```bash
# Generate a dashboard from stats JSON files
python scripts/generate.py stats/<server>/data --title "Server Name"

# Rebuild the local Minecraft icon set (stats/assets/icons/*.png)
python scripts/build_icons.py

# Sync stats from Crafty Controller to repo + push (Windows)
.\scripts\sync-stats.ps1

# Full pipeline (automatic on push to stats/*/data/**)
# sync-stats.ps1 → push → update-stats.yml → static.yml → GitHub Pages
```

No dependencies beyond Python 3.12+ stdlib. No pip install needed.

## Architecture

```
├── scripts/
│   ├── generate.py          # Main generator: JSON → HTML dashboard
│   ├── minecraft/
│   │   ├── badges.py        # Badge definitions + per-player tier computation
│   │   └── history.py       # Snapshot-based deltas, streaks, daily hours, aggregates, rank changes
│   ├── build_icons.py       # Pre-renders Minecraft icon PNGs (stdlib only)
│   └── sync-stats.ps1       # Windows: copy stats from Crafty + git push
├── tests/                   # unittest suite (stdlib only) for history.py + badges.py
├── docs/                    # Internal dev planning logs — EXCLUDED from public mirror
├── stats/
│   ├── assets/
│   │   ├── icons/           # Pre-rendered 256×256 Minecraft icon PNGs (committed)
│   │   ├── styles.css       # Dashboard stylesheet (shared across servers)
│   │   ├── colors.js        # Identity palette, block colors, CHART_PALETTE — loaded before app.js
│   │   ├── i18n.js          # T (fr+en), t(), label(), mcIcon() — loaded before app.js
│   │   └── app.js           # Dashboard runtime (shared across servers)
│   └── <server-name>/       # One folder per server (repeatable)
│       ├── data/            # Raw Minecraft stats JSON (UUID-named)
│       ├── snapshots/       # Dated copies of data/ (YYYY-MM-DD/*.json), 1/day max
│       ├── index.html       # Generated — DO NOT EDIT BY HAND
│       └── .uuid_cache.json # Mojang UUID→name cache (auto-managed)
└── .github/workflows/
    ├── update-stats.yml     # Detects data/ changes, runs generate.py
    └── static.yml           # Deploys to GitHub Pages after update-stats
```

### generate.py internals

1. **UUID resolution** — Mojang API with local `.uuid_cache.json` to avoid rate limits (0.5s delay between calls)
2. **Stats extraction** — `process_player()` normalizes Minecraft JSON: ticks→hours, cm→km, strips `minecraft:` prefixes, then calls `compute_player_badges()` and attaches the result under the `badges` key
3. **7-day deltas** — `main()` calls `find_baseline_snapshot()` once, loads the baseline metrics, then attaches `delta_7d` to each player dict via `compute_deltas()` (key absent when no usable baseline)
4. **HTML generation** — Small f-string shell (~30 lines) that injects `window.PLAYERS_DATA` / `window.SYNC` / `window.BASELINE_DATE` / `window.ICONS_HR` / `window.SERVER_DAILY` / `window.RANK_CHANGES` / `window.SNAPSHOT_DATES`, then loads `../assets/styles.css` + the three JS assets in order: `colors.js`, `i18n.js`, `app.js` (classic scripts, shared global scope). CSS/JS are not embedded — they ship as static files under `stats/assets/`.

### build_icons.py internals

1. **Sources** — pixel-art sprites from InventivetalentDev CDN (native 16×16, palette PNGs with bit depth 4) + 3D block renders from minecraft.wiki (native ~300×300, RGBA)
2. **Pipeline** — parse PNG → unfilter → expand sub-byte palette indices → convert to RGBA → nearest-neighbor upscale pixel art to 256×256 → write
3. **Post-normalize** — every generated icon is re-canvassed so its opaque-bbox occupies a uniform 85% of the frame (keeps 2D sprites and 3D blocks visually the same size in the dashboard)
4. **Stdlib only** — pure `zlib` + `struct`, no Pillow (matches project no-deps constraint)

### Icon rendering in generate.py

- `stats/assets/icons/manifest.json` lists every hi-res icon present on disk — it's written by `build_icons.py` at the end of its run. `generate.py` loads it via `load_icons_manifest()` and injects it as `window.ICONS_HR` into the HTML. `app.js` builds `MC_ICONS_HR = new Set(window.ICONS_HR || [])` and icons in the set render via `<img class="mc-icon-hr">` with `image-rendering: auto` (bilinear, crisp at fractional DPRs like Windows 125%)
- Anything not in that set falls back to a CDN `<img class="mc-icon">` with `image-rendering: pixelated` (works correctly only at integer DPRs)
- Display size is 32×32 for both classes; hi-res sources are 256×256 so they downscale smoothly
- No manual sync needed: adding an icon to `ICONS` / `WIKI_HIRES` in `build_icons.py` and running the script updates the PNG folder **and** the manifest in one pass

### Workflow chain

`update-stats.yml` commits regenerated HTML → but `github-actions[bot]` commits don't trigger other workflows → `static.yml` uses `workflow_run` trigger to redeploy after stats update.

### badges.py internals

- `BADGES` list — 33 standard badges, each entry declares `{id, name, icon, cat, tiers: [{label, min}], value: callable(player)}`. Categories: `mining` (5) / `combat` (6) / `survival` (4) / `exploration` (6) / `farming` (4) / `craft` (4) / `daily` (3) / `prestige` (1). 4 tiers per badge (Bronze → Silver → Gold → Diamond).
- `META_CATEGORIES` drives two meta-badges (`all_rounder`, `legende`, both in `prestige`) computed after the standard pass using already-assigned tiers.
- `compute_player_badges(player)` returns the list embedded in each player dict under `badges` (icon stored as a name like `diamond_pickaxe`, not rendered HTML).
- `app.js` is a dumb renderer — `buildBadgesHtml` reads `p.badges` directly and calls `mcIcon(b.icon)`. No badge thresholds or tier logic live in JS.

### history.py internals

- `DELTA_KEYS` — the four metrics tracked: `play_hours`, `total_mined`, `mob_kills`, `total_crafted`. Adding a new tracked key requires updating this tuple **and** the renderers in `app.js` (`deltaTotals` + the matching tile).
- `find_baseline_snapshot(snapshots_root, target_days=7, min_days=6, max_days=30)` — scans `snapshots/YYYY-MM-DD/` directories, keeps those whose age ∈ `[min_days, max_days]`, returns the one closest to `target_days`. Returns `None` if no candidate qualifies (empty dir, only fresh snapshots, or all snapshots > 30 days old).
- `load_baseline_metrics(snapshot_dir)` — reads each `<uuid>.json` and runs `_extract_metrics()`, mirroring `process_player()`'s conversions for the 4 tracked keys (ticks→hours, sums for mined/crafted).
- `compute_deltas(current, baseline)` — returns `{key: round(current - baseline, 1)}` or `None` when baseline is missing. `None` is the contract that lets callers omit `player["delta_7d"]` entirely so the JS side can hide the sub-line cleanly (no misleading `+0` displayed).
- The actual baseline window may differ from 7 days — `app.js` reads `BASELINE_DATE` and labels the sub-line with the real day count (e.g. `↑ +13.5h (6j)` for a 6-day-old snapshot), keeping the figure honest after gaps in the snapshot cadence.
- `compute_daily_play_hours(snapshots_root)` — returns `{uuid: {YYYY-MM-DD: hours}}` from **consecutive** snapshot pairs only. If snapshot D and D-1 both exist, the delta is attributed to date D; otherwise the day is omitted (no faked zeros for gaps). Drives the per-player activity heatmap. Negative deltas (world reset) are filtered out. `generate.py` attaches the per-player map under `player["daily_hours"]` (key absent if no entries).
- `compute_streaks(daily_hours, today=None)` — per UUID, returns `{current, longest, total_active_days}` computed from the output of `compute_daily_play_hours`. `current` is the run ending at `today` (0 if today's date isn't present). Drives the streak suffix under the heatmap meta line. `generate.py` attaches it under `player["streaks"]` (key absent if no entries).
- `aggregate_daily_hours(daily_hours)` — sums per-day hours across every player, rounded to 2 decimals. Injected as `window.SERVER_DAILY` and drives the server-wide heatmap card on the overview. Empty dict → card absent (returns `''` client-side).
- `compute_rank_changes(current_players, baseline_metrics, uuid_to_name, keys=DELTA_KEYS)` — per metric, ranks players at baseline and now, emits an entry only when a player improved rank AND a specific overtaken player (just behind now, ahead at baseline) can be named. Gain-only narrative (never "X got overtaken"). Sorted by `|delta_rank|` desc, capped at 10. Exposed as `window.RANK_CHANGES`.
- `list_snapshot_dates(snapshots_root)` — sorted list of ISO dates with a snapshot dir on disk. Injected as `window.SNAPSHOT_DATES` so the heatmap tooltip can distinguish *"no snapshot for this day"* from *"snapshot present but the previous day is missing, so no delta is computable"* (two tooltip strings: `hm_no_data` vs `hm_snapshot_gap`). Both cases still render as empty cells — the cadence-gap rule from `compute_daily_play_hours` is untouched.

### Snapshots archive

- `sync-stats.ps1` writes a full copy of `data/*.json` into `stats/<server-name>/snapshots/YYYY-MM-DD/` after the normal sync. Only created if the dated folder doesn't already exist (1 snapshot/day max, first run of the day wins).
- Date is `Get-Date -Format 'yyyy-MM-dd'` (local time, which is Europe/Paris on the dev machine — consistent with the project tz convention).
- `git add` covers both `data/*.json` and `snapshots/` so each daily sync commit carries the archive.
- `update-stats.yml` only triggers on `stats/*/data/**`, so a snapshot-only commit (unlikely in practice) would not rebuild the dashboard — the sync script always touches `data/` when it writes a snapshot.
- `generate.py` reads the snapshots through `history.py` (sibling `snapshots/` dir) to compute the 7-day deltas exposed on the dashboard stat-tiles. Without snapshots the build still succeeds — `find_baseline_snapshot()` returns `None` and the deltas are omitted client-side.

### Navigation & routing (app.js)

- Two fixed nav tabs (`Vue globale`, `Classements`), a `<select id="playerSelect">` listing players sorted by hours, and a `🔀 Comparer` button that toggles an inline 2-select form (+ Go) pre-filled with the top-2 most-played. No player buttons anymore (doesn't scale past ~6 players on mobile).
- Hash router: `location.hash` reflects the active section — `''` (overview), `#leaderboards`, `#player/<name>`, `#compare/<a>/<b>`. `navigateTo()` uses `history.pushState` so dashboard-triggered navigation doesn't fire `hashchange`; `hashchange` + `popstate` listeners sync the UI when the URL changes externally (back/forward, paste a deep-link).
- Compare section is lazy-rendered (cache `renderedCompares`) like player sections. Deep-link `#compare/A/A` redirects silently to `#player/A` via `hashToSection`. Unknown player names fall back to `overview`.

## Code style

### generate.py template (the f-string)

- `generate_html()` only holds the HTML shell + data injection — keep it short. Real markup is built by `app.js` from `window.PLAYERS_DATA`.
- Placeholders injected today: `{data_json}`, `{sync_date_fr}` / `{sync_date_en}`, `{baseline_json}`, `{icons_json}`, `{server_daily_json}`, `{rank_changes_json}`, `{title}`. Any literal `{` / `}` in the shell still need doubling (e.g. the `window.SYNC` object literal).
- Do **not** reintroduce inline CSS/JS here — edit the files under `stats/assets/` instead (no escaping needed, full syntax highlighting, lintable). Script load order in the shell is `colors.js` → `i18n.js` → `app.js` (classic scripts share the global scope).

### Color palette

- Five **semantic** CSS vars in `stats/assets/styles.css :root`, one per stat category: `--c-mining` (green), `--c-combat` (red), `--c-survival` (orange), `--c-travel` (blue), `--c-craft` (teal). Every stat-tile, leaderboard and card-icon binds to exactly one of these — a given category always has the same color across overview, per-player sections and leaderboards.
- Palettes and block-color maps live in `stats/assets/colors.js`: the 8-hue `PALETTE` is **player identity only** (used to derive `PLAYER_COLORS_MAP` in `app.js` for comparative charts — radar, distance stack, deaths aggregate — and the active-player select border), the 15-hue `CHART_PALETTE` is the unified fallback for all chart datasets (death-causes doughnut, distance stacked, per-player dist bar, treemap fallback), and `BLOCK_COLORS` / `DYE_COLORS` / `WOOD_COLORS` / `LEAF_COLORS` + `blockColor()` drive the treemap's in-game-hue mapping. Never reuse `PALETTE` colors for stat categories.
- Muted text uses `--text-muted: #8080a0` (WCAG AA on the `--bg` / `--bg-card` pair).

### Dashboard language conventions

- **French** for all UI: titles, section headers, labels, navigation, stat tile names, distance types (Marche, Sprint, Elytra)
- **English** for Minecraft entity names: blocks, items, mobs. Formatted automatically from snake_case → Title Case via JS `label()` function
- The `LABELS` dict in JS only contains French overrides for distance types. Everything else falls through to auto-formatting.
- **i18n dict (`T` in `stats/assets/i18n.js`)** — `T.fr` is the complete source of truth; `T.en` only holds overrides. Lookups use `T[lang]?.[k] ?? T.fr[k]`, so any missing EN key silently falls back to French. When adding a new UI string, add it to `T.fr`; only add a matching `T.en` entry if it needs a non-French value. `t()`, `label()`, `mcIcon()` and the `lang` binding live in the same file — all shared with `app.js` through the classic-script global scope.

### Stats units

| Minecraft raw | Converted to | Division |
|---|---|---|
| play_time / play_one_minute (ticks) | hours | ÷ 72,000 |
| *_one_cm (distances) | km | ÷ 100,000 |
| damage_dealt / damage_taken | raw (÷20 for hearts in display) | — |

## Important rules

- **Never edit index.html manually** — it's overwritten by generate.py on every run
- **Timezone is Europe/Paris** — uses `ZoneInfo("Europe/Paris")` for sync timestamp, not UTC
- **Avatar service is mc-heads.net** — Crafatar is dead (521 errors). URL pattern: `https://mc-heads.net/avatar/{uuid}/64`
- **UUID cache is critical** — Mojang rate-limits aggressively. Cache persists across runs. Don't delete `.uuid_cache.json` without reason.
- **`play_time` vs `play_one_minute`** — Minecraft 1.17+ uses `play_time`, older versions use `play_one_minute`. `process_player()` checks both with fallback.
- **mined_top15 / killed_top10 / crafted_top15** — Only contain the top N items, not all items. If a badge or feature needs a specific item (e.g. `diamond_ore`), extract it explicitly in `process_player()`.
- **sync-stats.ps1 takes params with local defaults** — `-Source` (Crafty stats folder), `-Repo` (repo root), `-ServerName` (sub-folder under `stats/`). Defaults point at the dev machine's paths; override at call site when running elsewhere. The script writes `stats/<ServerName>/snapshots/YYYY-MM-DD/` (1/day max) and includes it in the daily commit.
- **Workflow title match matters** — `static.yml` triggers on `workflow_run` matching the exact `name:` of `update-stats.yml` ("Update Minecraft Stats Dashboard")
- **`[skip ci]` in commit message** — update-stats.yml commits with `[skip ci]` to avoid infinite loops. The deploy is triggered via `workflow_run`, not the push.
- **Icon PNGs are committed, not fetched at runtime** — `stats/assets/icons/*.png` (~100 KB total) ship with the repo so the dashboard is self-contained. Rebuild with `python scripts/build_icons.py` after editing the `ICONS` / `WIKI_HIRES` dicts. The script also rewrites `stats/assets/icons/manifest.json`, which `generate.py` reads at build time to tell `app.js` which icons are local.
- **Adding a new icon** — add its name to `ICONS` (or `WIKI_HIRES`) in `build_icons.py`, run the script, commit the new PNG + the updated `manifest.json`. No other file needs editing — `generate.py` picks up the manifest automatically on the next run.
- **Delta window is `[6, 30]` days** — too-recent snapshots produce noisy "weekly" deltas; snapshots older than 30 days mislead after a long pause. The label shows the **actual** baseline age (computed JS-side from `window.BASELINE_DATE`), never a hardcoded `7j` — so a 6-day baseline labels itself `(6j)`.

## Public template repo

This repo has **two remotes**: `origin` (private-ish personal data hosted via Pages) and `public` (clean template published at a second GitHub repo). A single local branch `public-main` mirrors `main` minus personal data.

### Mirror workflow

`scripts/mirror-to-public.ps1` rebuilds `public-main` from `main`:

- Switches to `public-main` (creates as orphan if missing), recopies `main`'s tree, removes paths listed in `-Exclude` (default: `stats/serveur-2026`, `stats/serveur-2020`, `stats/hermitcraft-s10`, `scripts/sync-stats.ps1`, `scripts/mirror-to-public.ps1`, `docs`), commits `"mirror from main @ <sha>"`.
- `public-main` history is a linear chain of mirror commits (orphan root). Personal-data commits from `main` never appear in `public-main`'s history, so pushing to the public remote doesn't leak them.
- Run after every code change that should land in the public template: `.\scripts\mirror-to-public.ps1 -Push` (requires `git remote add public <url>` once).

### What's excluded from the public mirror

- `stats/serveur-2026/`, `stats/serveur-2020/`, `stats/hermitcraft-s10/` — personal and demo server data + snapshots
- `scripts/sync-stats.ps1` — Crafty-specific + Windows-specific, too niche for a template
- `docs/` — internal dev planning logs (historiques FR des refactorings)

Shared assets (`stats/assets/`), workflows, generator, badges, and docs are all kept — the template is fully functional out of the box, users just drop their own `stats/<server>/data/*.json` in.
