# Minecraft Stats Dashboard

Static HTML dashboards generated from Minecraft server stats JSON files, deployed via GitHub Pages.

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
│   │   └── badges.py        # Badge definitions + per-player tier computation
│   ├── build_icons.py       # Pre-renders Minecraft icon PNGs (stdlib only)
│   └── sync-stats.ps1       # Windows: copy stats from Crafty + git push
├── stats/
│   ├── assets/
│   │   ├── icons/           # Pre-rendered 256×256 Minecraft icon PNGs (committed)
│   │   ├── styles.css       # Dashboard stylesheet (shared across servers)
│   │   └── app.js           # Dashboard runtime (shared across servers)
│   ├── serveur-2026/
│   │   ├── data/            # Raw Minecraft stats JSON (UUID-named)
│   │   ├── index.html       # Generated — DO NOT EDIT BY HAND
│   │   └── .uuid_cache.json # Mojang UUID→name cache (auto-managed)
│   └── serveur-2020/
│       ├── data/
│       └── index.html
└── .github/workflows/
    ├── update-stats.yml     # Detects data/ changes, runs generate.py
    └── static.yml           # Deploys to GitHub Pages after update-stats
```

### generate.py internals

1. **UUID resolution** — Mojang API with local `.uuid_cache.json` to avoid rate limits (0.5s delay between calls)
2. **Stats extraction** — `process_player()` normalizes Minecraft JSON: ticks→hours, cm→km, strips `minecraft:` prefixes, then calls `compute_player_badges()` and attaches the result under the `badges` key
3. **HTML generation** — Small f-string shell (~30 lines) that injects `window.PLAYERS_DATA` / `window.SYNC` then loads `../assets/styles.css` and `../assets/app.js`. CSS/JS are not embedded — they ship as static files under `stats/assets/`.

### build_icons.py internals

1. **Sources** — pixel-art sprites from InventivetalentDev CDN (native 16×16, palette PNGs with bit depth 4) + 3D block renders from minecraft.wiki (native ~300×300, RGBA)
2. **Pipeline** — parse PNG → unfilter → expand sub-byte palette indices → convert to RGBA → nearest-neighbor upscale pixel art to 256×256 → write
3. **Post-normalize** — every generated icon is re-canvassed so its opaque-bbox occupies a uniform 85% of the frame (keeps 2D sprites and 3D blocks visually the same size in the dashboard)
4. **Stdlib only** — pure `zlib` + `struct`, no Pillow (matches project no-deps constraint)

### Icon rendering in generate.py

- `MC_ICONS_HR` (set) lists icons shipped locally under `stats/assets/icons/` — rendered via `<img class="mc-icon-hr">` with `image-rendering: auto` (bilinear, crisp at fractional DPRs like Windows 125%)
- Anything not in that set falls back to a CDN `<img class="mc-icon">` with `image-rendering: pixelated` (works correctly only at integer DPRs)
- Display size is 32×32 for both classes; hi-res sources are 256×256 so they downscale smoothly

### Workflow chain

`update-stats.yml` commits regenerated HTML → but `github-actions[bot]` commits don't trigger other workflows → `static.yml` uses `workflow_run` trigger to redeploy after stats update.

### badges.py internals

- `BADGES` list — each entry declares `{id, name, icon, cat, tiers: [{label, min}], value: callable(player)}`. Meta-badges (`all_rounder`, `legende`) are computed after the standard pass using already-assigned tiers.
- `compute_player_badges(player)` returns the list embedded in each player dict under `badges` (icon stored as a name like `diamond_pickaxe`, not rendered HTML).
- `app.js` is a dumb renderer — `buildBadgesHtml` reads `p.badges` directly and calls `mcIcon(b.icon)`. No badge thresholds or tier logic live in JS.

## Code style

### generate.py template (the f-string)

- `generate_html()` only holds the HTML shell + data injection — keep it short. Real markup is built by `app.js` from `window.PLAYERS_DATA`.
- The two injected values are `{data_json}` (compact JSON of all players) and the sync-date strings. Any literal `{` / `}` in the shell still need doubling (e.g. the `window.SYNC` object literal).
- Do **not** reintroduce inline CSS/JS here — edit `stats/assets/styles.css` and `stats/assets/app.js` instead (no escaping needed, full syntax highlighting, lintable).

### Dashboard language conventions

- **French** for all UI: titles, section headers, labels, navigation, stat tile names, distance types (Marche, Sprint, Elytra)
- **English** for Minecraft entity names: blocks, items, mobs. Formatted automatically from snake_case → Title Case via JS `label()` function
- The `LABELS` dict in JS only contains French overrides for distance types. Everything else falls through to auto-formatting.
- **i18n dict (`T` in app.js)** — `T.fr` is the complete source of truth; `T.en` only holds overrides. Lookups use `T[lang]?.[k] ?? T.fr[k]`, so any missing EN key silently falls back to French. When adding a new UI string, add it to `T.fr`; only add a matching `T.en` entry if it needs a non-French value.

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
- **sync-stats.ps1 paths are hardcoded** — Source: `A:\crafty-4\servers\...\stats`, Dest: `C:\Users\jules\Desktop\minecraft\stats\serveur-2026\data`
- **Workflow title match matters** — `static.yml` triggers on `workflow_run` matching the exact `name:` of `update-stats.yml` ("Update Minecraft Stats Dashboard")
- **`[skip ci]` in commit message** — update-stats.yml commits with `[skip ci]` to avoid infinite loops. The deploy is triggered via `workflow_run`, not the push.
- **Icon PNGs are committed, not fetched at runtime** — `stats/assets/icons/*.png` (~100 KB total) ship with the repo so the dashboard is self-contained. Rebuild with `python scripts/build_icons.py` after editing the `ICONS` / `WIKI_HIRES` dicts.
- **Adding a new icon** — add its name to `ICONS` (or `WIKI_HIRES`) in `build_icons.py`, run the script, then add the same name to `MC_ICONS_HR` in `generate.py` so the dashboard uses the local hi-res file instead of the CDN fallback.
