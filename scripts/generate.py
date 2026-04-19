#!/usr/bin/env python3
"""
generate.py — Tickstats Dashboard Generator
===================================================
Reads Minecraft stats JSON files from a directory,
resolves UUIDs to usernames via the Mojang API,
and generates a complete index.html dashboard.

Usage:
    python generate.py <data_dir_path> [--title "Server title"]

Example:
    python generate.py stats/<server-name>/data --title "Server name"

The index.html file is created in the parent directory of <data_dir_path>.
e.g. stats/<server-name>/data → stats/<server-name>/index.html
"""

import json
import os
import sys
import argparse
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from minecraft.badges import compute_player_badges
from minecraft.history import (
    compute_daily_play_hours,
    compute_deltas,
    compute_rank_changes,
    find_baseline_snapshot,
    load_baseline_metrics,
)


# ═══════════════════════════════════════════════════════════
# 1. UUID → USERNAME RESOLUTION (Mojang API)
# ═══════════════════════════════════════════════════════════

def resolve_uuid(uuid: str) -> str:
    """Resolve a Minecraft UUID to a username via the Mojang API."""
    clean = uuid.replace("-", "")
    url = f"https://sessionserver.mojang.com/session/minecraft/profile/{clean}"
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read())
        return data.get("name", uuid[:8])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  [!] Could not resolve {uuid}: {e}")
        return uuid[:8]


def resolve_all_uuids(uuids: list[str], cache_path: Path | None = None) -> dict[str, str]:
    """
    Resolve a list of UUIDs, using a local cache to avoid
    re-hitting the API on every run.
    """
    cache = {}
    if cache_path and cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)

    result = {}
    for uuid in uuids:
        if uuid in cache:
            result[uuid] = cache[uuid]
            print(f"  + {uuid} -> {cache[uuid]} (cache)")
        else:
            name = resolve_uuid(uuid)
            result[uuid] = name
            cache[uuid] = name
            print(f"  + {uuid} -> {name} (API)")
            time.sleep(0.5)  # Mojang rate limiting

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2)

    return result


# ═══════════════════════════════════════════════════════════
# 2. STATS EXTRACTION & NORMALIZATION
# ═══════════════════════════════════════════════════════════

def clean_key(k: str) -> str:
    return k.replace("minecraft:", "")


def clean_dict(d: dict, top_n: int | None = None) -> dict:
    cleaned = {clean_key(k): v for k, v in d.items()}
    if top_n:
        cleaned = dict(sorted(cleaned.items(), key=lambda x: -x[1])[:top_n])
    return cleaned


def process_player(uuid: str, name: str, filepath: str) -> dict:
    """Extract and normalize all stats for a player."""
    with open(filepath) as f:
        data = json.load(f)

    stats = data.get("stats", {})
    custom = stats.get("minecraft:custom", {})

    # Play time: play_time (1.17+) or play_one_minute (legacy)
    play_ticks = custom.get("minecraft:play_time",
                            custom.get("minecraft:play_one_minute", 0))

    # Distances (cm → km)
    dist_keys = [
        "walk_one_cm", "sprint_one_cm", "swim_one_cm", "fly_one_cm",
        "aviate_one_cm", "boat_one_cm", "horse_one_cm", "minecart_one_cm",
        "climb_one_cm", "crouch_one_cm", "fall_one_cm",
        "walk_on_water_one_cm", "walk_under_water_one_cm",
    ]
    distances = {}
    for key in dist_keys:
        mc_key = f"minecraft:{key}"
        if mc_key in custom:
            distances[key.replace("_one_cm", "")] = round(custom[mc_key] / 100_000, 2)

    # Badge-specific stats (items that may not be in top 15/10)
    mined_all = {clean_key(k): v for k, v in stats.get("minecraft:mined", {}).items()}
    killed_all = {clean_key(k): v for k, v in stats.get("minecraft:killed", {}).items()}
    crafted_all = {clean_key(k): v for k, v in stats.get("minecraft:crafted", {}).items()}

    badge_data = {
        "diamond_ore": mined_all.get("diamond_ore", 0) + mined_all.get("deepslate_diamond_ore", 0),
        "ancient_debris": mined_all.get("ancient_debris", 0),
        "netherrack": mined_all.get("netherrack", 0),
        "logs": sum(mined_all.get(t, 0) for t in [
            "oak_log", "spruce_log", "birch_log", "dark_oak_log",
            "acacia_log", "jungle_log", "cherry_log",
        ]),
        "crops": sum(mined_all.get(t, 0) for t in [
            "wheat", "beetroots", "carrots", "potatoes",
        ]),
        "enderman": killed_all.get("enderman", 0),
        "wither_skeleton": killed_all.get("wither_skeleton", 0),
        "blaze": killed_all.get("blaze", 0),
        "pillager": killed_all.get("pillager", 0),
        "vindicator": killed_all.get("vindicator", 0),
        "ravager": killed_all.get("ravager", 0),
        "paper": crafted_all.get("paper", 0),
        "total_broken": sum(stats.get("minecraft:broken", {}).values()),
    }

    player = {
        "uuid": uuid,
        "play_hours": round(play_ticks / 20 / 3600, 1),
        "play_ticks": play_ticks,
        "deaths": custom.get("minecraft:deaths", 0),
        "mob_kills": custom.get("minecraft:mob_kills", 0),
        "player_kills": custom.get("minecraft:player_kills", 0),
        "jumps": custom.get("minecraft:jump", 0),
        "damage_dealt": custom.get("minecraft:damage_dealt", 0),
        "damage_taken": custom.get("minecraft:damage_taken", 0),
        "animals_bred": custom.get("minecraft:animals_bred", 0),
        "fish_caught": custom.get("minecraft:fish_caught", 0),
        "enchant_item": custom.get("minecraft:enchant_item", 0),
        "open_chest": custom.get("minecraft:open_chest", 0),
        "sleep_in_bed": custom.get("minecraft:sleep_in_bed", 0),
        "traded_with_villager": custom.get("minecraft:traded_with_villager", 0),
        "talked_to_villager": custom.get("minecraft:talked_to_villager", 0),
        "distances": distances,
        "total_distance_km": round(sum(distances.values()), 2),
        "mined_top15": clean_dict(stats.get("minecraft:mined", {}), 15),
        "total_mined": sum(stats.get("minecraft:mined", {}).values()),
        "killed_top10": clean_dict(stats.get("minecraft:killed", {}), 10),
        "total_killed": sum(stats.get("minecraft:killed", {}).values()),
        "killed_by": clean_dict(stats.get("minecraft:killed_by", {})),
        "crafted_top15": clean_dict(stats.get("minecraft:crafted", {}), 15),
        "total_crafted": sum(stats.get("minecraft:crafted", {}).values()),
        "total_used": sum(stats.get("minecraft:used", {}).values()),
        "total_picked_up": sum(stats.get("minecraft:picked_up", {}).values()),
        "total_dropped": sum(stats.get("minecraft:dropped", {}).values()),
        "broken": clean_dict(stats.get("minecraft:broken", {})),
        "badge_data": badge_data,
    }
    player["badges"] = compute_player_badges(player)
    return player


# ═══════════════════════════════════════════════════════════
# 3. HTML GENERATION
# ═══════════════════════════════════════════════════════════

ICONS_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "stats" / "assets" / "icons" / "manifest.json"


def load_icons_manifest() -> list[str]:
    """Return the list of hi-res icons shipped locally (written by build_icons.py)."""
    if not ICONS_MANIFEST_PATH.exists():
        print(f"[WARN] Icons manifest not found at {ICONS_MANIFEST_PATH} — all icons will use CDN fallback")
        return []
    with open(ICONS_MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def generate_html(
    players_data: dict,
    title: str,
    baseline_date: str | None = None,
    rank_changes: list | None = None,
) -> str:
    """Generate the full HTML dashboard file."""
    data_json = json.dumps(players_data, separators=(",", ":"))
    baseline_json = json.dumps(baseline_date)
    icons_json = json.dumps(load_icons_manifest(), separators=(",", ":"))
    rank_changes_json = json.dumps(rank_changes or [], separators=(",", ":"))
    now = datetime.now(ZoneInfo("Europe/Paris"))
    sync_date_fr = now.strftime("%d/%m/%Y à %H:%M")
    sync_date_en = now.strftime("%Y-%m-%d at %H:%M")
    return f'''<!DOCTYPE html>
<html lang="fr" id="html-root">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="icon" href="https://cdn2.steamgriddb.com/icon/0678c572b0d5597d2d4a6b5bd135754c/32/128x128.png">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
<div class="app">
<div class="header">
  <h1><img class="mc-icon-hr" style="width:48px;height:48px;margin-right:.3rem" src="../assets/icons/diamond_pickaxe.png" alt="pickaxe"> {title}</h1>
  <p id="subtitle"></p>
  <div class="meta" id="globalMeta"></div>
  <div class="sync-date" id="syncDate"></div>
  <button id="langToggle" class="lang-toggle"></button>
</div>
<div class="nav" id="nav"></div>
<div id="content"></div>
</div>
<script>
window.PLAYERS_DATA = {data_json};
window.SYNC = {{"fr": "{sync_date_fr}", "en": "{sync_date_en}"}};
window.BASELINE_DATE = {baseline_json};
window.ICONS_HR = {icons_json};
window.RANK_CHANGES = {rank_changes_json};
</script>
<script src="../assets/app.js"></script>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════
# 4. MAIN
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML dashboard from Minecraft stats JSON files."
    )
    parser.add_argument(
        "data_dir",
        help="Path to the directory containing the stats JSON files (e.g. stats/<server-name>/data)"
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Server title displayed in the dashboard (default: parent directory name)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output HTML file path (default: <parent_dir>/index.html)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"[ERR] Directory {data_dir} does not exist.")
        sys.exit(1)

    # Title: from argument or formatted parent directory name
    if args.title:
        title = args.title
    else:
        parent_name = data_dir.parent.name
        title = parent_name.replace("-", " ").replace("_", " ").title()

    # Output file
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = data_dir.parent / "index.html"

    # UUID cache (persists across runs)
    cache_path = data_dir.parent / ".uuid_cache.json"

    print(f"[MC] Generating dashboard: {title}")
    print(f"[IN] Data directory: {data_dir}")
    print(f"[OUT] Output: {output_path}")
    print()

    # Find JSON files
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print("[ERR] No JSON file found in the directory.")
        sys.exit(1)

    print(f"[DATA] {len(json_files)} stats file(s) found")

    # Extract UUIDs
    uuids = [f.stem for f in json_files]

    # Resolve usernames
    print("\n[UUID] Resolving Mojang usernames...")
    uuid_to_name = resolve_all_uuids(uuids, cache_path)

    # 7-day baseline (snapshots/YYYY-MM-DD/) for stat-tile deltas
    snapshots_dir = data_dir.parent / "snapshots"
    baseline_dir = find_baseline_snapshot(snapshots_dir)
    baseline_metrics = load_baseline_metrics(baseline_dir) if baseline_dir else {}
    baseline_date = baseline_dir.name if baseline_dir else None
    if baseline_date:
        print(f"[HIST] Baseline snapshot: {baseline_date} ({len(baseline_metrics)} players)")
    else:
        print(f"[HIST] No baseline snapshot >= 6 days old - deltas hidden")

    # Per-day play_hours from consecutive snapshots → activity heatmap
    daily_hours = compute_daily_play_hours(snapshots_dir)
    if daily_hours:
        print(f"[HIST] Daily heatmap data: {sum(len(v) for v in daily_hours.values())} cells across {len(daily_hours)} players")

    # Process stats
    print("\n[STATS] Processing statistics...")
    players_data = {}
    for json_file in json_files:
        uuid = json_file.stem
        name = uuid_to_name[uuid]
        player = process_player(uuid, name, str(json_file))
        delta = compute_deltas(player, baseline_metrics.get(uuid))
        if delta is not None:
            player["delta_7d"] = delta
        if daily_hours.get(uuid):
            player["daily_hours"] = daily_hours[uuid]
        players_data[name] = player
        print(f"  + {name}: {player['play_hours']}h, {player['total_mined']} blocks, {player['mob_kills']} kills")

    # Rank movements vs baseline (only computed when we have a baseline)
    rank_changes = (
        compute_rank_changes(players_data, baseline_metrics, uuid_to_name)
        if baseline_metrics else []
    )
    if rank_changes:
        print(f"[HIST] Rank changes detected: {len(rank_changes)}")

    # Generate HTML
    print(f"\n[HTML] Generating HTML...")
    html = generate_html(players_data, title, baseline_date, rank_changes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Dashboard generated: {output_path} ({len(html):,} bytes)")
    print(f"   {len(players_data)} players - {sum(p['play_hours'] for p in players_data.values()):.0f}h total playtime")


if __name__ == "__main__":
    main()
