#!/usr/bin/env python3
"""
generate.py — Minecraft Stats Dashboard Generator
===================================================
Lit les fichiers JSON de stats Minecraft dans un dossier,
résout les UUIDs en pseudos via l'API Mojang,
et génère un fichier index.html complet avec le dashboard.

Usage:
    python generate.py <chemin_dossier_data> [--title "Titre du serveur"]

Exemples:
    python generate.py stats/serveur-2026/data --title "Serveur 2026"
    python generate.py stats/serveur-confinement-2020/data --title "Serveur Confinement 2020"

Le fichier index.html est créé dans le dossier parent de <chemin_dossier_data>.
Ex: stats/serveur-2026/data → stats/serveur-2026/index.html
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


# ═══════════════════════════════════════════════════════════
# 1. RÉSOLUTION UUID → PSEUDO (Mojang API)
# ═══════════════════════════════════════════════════════════

def resolve_uuid(uuid: str) -> str:
    """Résout un UUID Minecraft en pseudo via l'API Mojang."""
    clean = uuid.replace("-", "")
    url = f"https://sessionserver.mojang.com/session/minecraft/profile/{clean}"
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read())
        return data.get("name", uuid[:8])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  [!] Impossible de resoudre {uuid}: {e}")
        return uuid[:8]


def resolve_all_uuids(uuids: list[str], cache_path: Path | None = None) -> dict[str, str]:
    """
    Résout une liste d'UUIDs, avec cache local pour éviter
    de re-requêter l'API à chaque exécution.
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
            time.sleep(0.5)  # Rate limiting Mojang

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2)

    return result


# ═══════════════════════════════════════════════════════════
# 2. EXTRACTION & NORMALISATION DES STATS
# ═══════════════════════════════════════════════════════════

def clean_key(k: str) -> str:
    return k.replace("minecraft:", "")


def clean_dict(d: dict, top_n: int | None = None) -> dict:
    cleaned = {clean_key(k): v for k, v in d.items()}
    if top_n:
        cleaned = dict(sorted(cleaned.items(), key=lambda x: -x[1])[:top_n])
    return cleaned


def process_player(uuid: str, name: str, filepath: str) -> dict:
    """Extrait et normalise toutes les stats d'un joueur."""
    with open(filepath) as f:
        data = json.load(f)

    stats = data.get("stats", {})
    custom = stats.get("minecraft:custom", {})

    # Temps de jeu : play_time (1.17+) ou play_one_minute (legacy)
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

    return {
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


# ═══════════════════════════════════════════════════════════
# 3. GÉNÉRATION HTML
# ═══════════════════════════════════════════════════════════

def generate_html(players_data: dict, title: str) -> str:
    """Génère le fichier HTML complet du dashboard."""
    data_json = json.dumps(players_data, separators=(",", ":"))
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
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0c0c0f;--bg-card:#16161a;--bg-card-alt:#1c1c22;--bg-hover:#222230;
  --border:#2a2a35;--border-light:#3a3a48;
  --text:#e8e6e3;--text-dim:#8b8b96;--text-muted:#5c5c68;
  --accent:#7c6aef;--accent-light:#9b8df7;--accent-dim:#5a4bb8;
  --green:#3ecf8e;--green-dim:#2a9d68;
  --red:#ef6a6a;--orange:#efaa6a;--blue:#6aafef;--cyan:#6aefd9;
  --yellow:#efd96a;--pink:#ef6ac0;--teal:#6aefe0;
  --font-mono:'JetBrains Mono',monospace;
  --font-sans:'Space Grotesk',system-ui,sans-serif;
  --radius:10px;--radius-sm:6px;
}}
html{{font-size:15px;scroll-behavior:smooth}}
body{{
  background:var(--bg);color:var(--text);font-family:var(--font-sans);
  min-height:100vh;line-height:1.5;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%,rgba(124,106,239,.08),transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%,rgba(62,207,142,.04),transparent);
}}
a{{color:var(--accent-light);text-decoration:none}}
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
.app{{max-width:1400px;margin:0 auto;padding:1rem}}
.header{{text-align:center;padding:2.5rem 1rem 2rem;position:relative}}
.header h1{{
  font-size:2.6rem;font-weight:700;letter-spacing:-.03em;
  background:linear-gradient(135deg,var(--accent-light),var(--green),var(--cyan));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:.3rem;
}}
.header p{{color:var(--text-dim);font-size:.95rem;font-family:var(--font-mono)}}
.header .meta{{display:flex;gap:1.5rem;justify-content:center;margin-top:1rem;flex-wrap:wrap}}
.header .meta span{{
  font-family:var(--font-mono);font-size:.8rem;color:var(--text-muted);
  background:var(--bg-card);padding:.35rem .8rem;border-radius:20px;border:1px solid var(--border);
}}
.header .meta span b{{color:var(--accent-light);font-weight:600}}
.sync-date{{font-family:var(--font-mono);font-size:.75rem;color:var(--text-muted);margin-top:.8rem}}
.nav{{
  display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap;
  padding:1rem 0;position:sticky;top:0;z-index:100;
  background:rgba(12,12,15,.4);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);margin-bottom:1.5rem;
}}
.nav button{{
  font-family:var(--font-mono);font-size:.78rem;
  padding:.5rem 1rem;border-radius:20px;border:1px solid var(--border);
  background:var(--bg-card);color:var(--text-dim);cursor:pointer;transition:all .2s;white-space:nowrap;
}}
.nav button:hover{{border-color:var(--accent);color:var(--text)}}
.nav button.active{{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 0 20px rgba(124,106,239,.25)}}
.card{{
  background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.25rem;margin-bottom:1rem;transition:border-color .2s;
}}
.card:hover{{border-color:var(--border-light)}}
.card h3{{
  font-size:.85rem;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-muted);margin-bottom:1rem;font-family:var(--font-mono);
  display:flex;align-items:center;gap:.5rem;
}}
.card h3 .icon{{font-size:1.1rem}}
img.mc-icon{{image-rendering:pixelated;image-rendering:-moz-crisp-edges;image-rendering:crisp-edges;-ms-interpolation-mode:nearest-neighbor;vertical-align:middle;display:inline-block;width:16px;height:16px}}
.card h3 img.mc-icon{{width:32px;height:32px}}
.badge-icon img.mc-icon{{width:16px;height:16px}}
.fun-fact img.mc-icon{{width:16px;height:16px;flex-shrink:0}}
.archetype img.mc-icon{{width:16px;height:16px}}
.nav button img.mc-icon{{width:16px;height:16px}}
.grid{{display:grid;gap:1rem}}
.grid-2{{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}}
.grid-3{{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}}
.grid-4{{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}}
.stat-tile{{
  background:var(--bg-card-alt);border-radius:var(--radius-sm);
  padding:1rem;text-align:center;border:1px solid var(--border);transition:transform .15s,border-color .15s;
}}
.stat-tile:hover{{transform:translateY(-2px);border-color:var(--accent-dim)}}
.stat-tile .value{{font-size:1.8rem;font-weight:700;font-family:var(--font-mono);line-height:1.1;margin-bottom:.2rem}}
.stat-tile .label{{font-size:.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;font-family:var(--font-mono)}}
.stat-tile .sub{{font-size:.7rem;color:var(--text-dim);margin-top:.15rem;font-family:var(--font-mono)}}
.leaderboard{{list-style:none}}
.leaderboard li{{
  display:flex;align-items:center;gap:.75rem;
  padding:.6rem .8rem;border-radius:var(--radius-sm);transition:background .15s;font-family:var(--font-mono);font-size:.82rem;
}}
.leaderboard li:hover{{background:var(--bg-hover)}}
.leaderboard .rank{{
  width:1.6rem;height:1.6rem;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:.7rem;font-weight:700;flex-shrink:0;border:1px solid var(--border);color:var(--text-muted);
}}
.leaderboard li:nth-child(1) .rank{{background:linear-gradient(135deg,#ffd700,#b8860b);color:#000;border:none}}
.leaderboard li:nth-child(2) .rank{{background:linear-gradient(135deg,#c0c0c0,#808080);color:#000;border:none}}
.leaderboard li:nth-child(3) .rank{{background:linear-gradient(135deg,#cd7f32,#8b4513);color:#fff;border:none}}
.leaderboard .name{{flex:1;color:var(--text)}}
.leaderboard .val{{color:var(--accent-light);font-weight:600}}
.leaderboard .bar-bg{{flex:1;height:6px;background:var(--bg);border-radius:3px;overflow:hidden;min-width:60px}}
.leaderboard .bar-fill{{height:100%;border-radius:3px;transition:width .6s ease}}
.chart-wrap{{position:relative;width:100%;max-height:350px}}
.chart-wrap canvas{{width:100%!important}}
.profile-header{{
  display:flex;align-items:center;gap:1.5rem;padding:1.5rem;
  background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:1.5rem;flex-wrap:wrap;
}}
.profile-avatar{{width:64px;height:64px;border-radius:var(--radius-sm);image-rendering:pixelated;border:2px solid var(--accent-dim);background:var(--bg)}}
.profile-info h2{{font-size:1.8rem;font-weight:700;letter-spacing:-.02em}}
.profile-info .uuid{{font-family:var(--font-mono);font-size:.7rem;color:var(--text-muted)}}
.profile-stats{{display:flex;gap:1.5rem;margin-left:auto;flex-wrap:wrap}}
.profile-stat{{text-align:center}}
.profile-stat .pv{{font-size:1.4rem;font-weight:700;font-family:var(--font-mono);color:var(--accent-light)}}
.profile-stat .pl{{font-size:.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;font-family:var(--font-mono)}}
.section{{display:none}}
.section.active{{display:block}}
.record-badge{{
  display:inline-block;padding:.1rem .4rem;border-radius:10px;font-size:.6rem;font-weight:700;margin-left:.3rem;
  background:linear-gradient(135deg,#ffd700,#b8860b);color:#000;
}}
.player-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
@media(max-width:768px){{
  .header h1{{font-size:1.6rem}}
  .grid-2,.grid-3,.grid-4{{grid-template-columns:1fr}}
  .profile-header{{flex-direction:column;align-items:flex-start}}
  .profile-stats{{margin-left:0}}
  .stat-tile .value{{font-size:1.3rem}}
  .app{{padding:.5rem}}
  .desktop-only{{display:none!important}}
}}
.mobile-only{{display:none}}
@media(max-width:768px){{.mobile-only{{display:block!important}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.card{{animation:fadeUp .4s ease both}}
.card:nth-child(2){{animation-delay:.05s}}
.card:nth-child(3){{animation-delay:.1s}}
.card:nth-child(4){{animation-delay:.15s}}
.archetype{{
  font-family:var(--font-mono);font-size:.72rem;padding:.25rem .7rem;border-radius:16px;
  display:inline-flex;align-items:center;gap:.35rem;margin-top:.4rem;border:1px solid;
}}
.treemap{{display:flex;flex-wrap:wrap;gap:2px;border-radius:var(--radius-sm);overflow:hidden;min-height:180px}}
.treemap-item{{
  position:relative;display:flex;align-items:flex-end;padding:5px 6px;
  min-width:28px;min-height:28px;cursor:default;transition:opacity .15s;border-radius:3px;overflow:hidden;
}}
.treemap-item:hover{{opacity:.8}}
.treemap-item span{{font-family:var(--font-mono);font-size:.58rem;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.8);line-height:1.15;word-break:break-word}}
.treemap-item .tm-count{{opacity:.7;font-size:.52rem}}
.fun-facts{{display:flex;flex-direction:column;gap:.5rem}}
.fun-fact{{
  display:flex;align-items:flex-start;gap:.6rem;padding:.6rem .8rem;
  background:var(--bg-card-alt);border-radius:var(--radius-sm);
  border-left:3px solid var(--accent);font-family:var(--font-mono);font-size:.78rem;color:var(--text-dim);
}}
.fun-fact .emoji{{font-size:1rem;flex-shrink:0;line-height:1.4}}
.broken-grid{{display:flex;flex-wrap:wrap;gap:.4rem}}
.broken-tag{{
  font-family:var(--font-mono);font-size:.7rem;padding:.25rem .6rem;
  border-radius:12px;background:var(--bg-hover);border:1px solid var(--border);color:var(--text-dim);
  display:inline-flex;align-items:center;gap:.3rem;
}}
.broken-tag .bt-count{{color:var(--red);font-weight:600}}
.badges-counter-wrap{{text-align:center;margin-bottom:.8rem}}
.badges-counter{{
  font-family:var(--font-mono);font-size:.85rem;color:var(--text-dim);
  padding:.5rem 1rem;background:var(--bg-card-alt);border:1px solid var(--border);border-radius:20px;
  display:inline-flex;gap:.4rem;align-items:center;
}}
.badges-counter b{{color:var(--accent-light)}}
.badges-cat-header{{
  font-family:var(--font-mono);font-size:.78rem;color:var(--text-muted);text-transform:uppercase;
  letter-spacing:.08em;margin:1.2rem 0 .6rem;padding-bottom:.4rem;border-bottom:1px solid var(--border);
}}
.badges-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:.5rem}}
.badge-card{{
  background:var(--bg-card-alt);border:1.5px solid var(--border);border-radius:var(--radius-sm);
  padding:.65rem .7rem;display:flex;flex-direction:column;gap:.25rem;transition:all .2s;
  position:relative;
}}
.badge-card:hover{{transform:translateY(-1px)}}
.badge-card.locked>*:not(.badge-tooltip){{opacity:.4;filter:grayscale(.5);transition:opacity .15s,filter .15s}}
.badge-card.locked:hover>*:not(.badge-tooltip){{opacity:.75;filter:grayscale(.3)}}
.badge-card.tier-bronze{{border-color:#cd7f32}}
.badge-card.tier-silver{{border-color:#c0c0c0}}
.badge-card.tier-gold{{border-color:#ffd700;box-shadow:0 0 6px rgba(255,215,0,.1)}}
.badge-card.tier-diamond{{border-color:#b9f2ff;box-shadow:0 0 10px rgba(185,242,255,.15)}}
.badge-header{{display:flex;align-items:center;gap:.4rem}}
.badge-icon{{font-size:1rem;flex-shrink:0}}
.badge-name{{font-family:var(--font-mono);font-size:.7rem;font-weight:600;color:var(--text);flex:1;line-height:1.2}}
.badge-tier{{
  font-size:.55rem;font-family:var(--font-mono);padding:.1rem .35rem;border-radius:8px;white-space:nowrap;font-weight:600;
}}
.badge-tier-locked{{background:rgba(92,92,104,.15);color:var(--text-muted)}}
.badge-tier-bronze{{background:rgba(205,127,50,.15);color:#cd7f32}}
.badge-tier-silver{{background:rgba(192,192,192,.15);color:#c0c0c0}}
.badge-tier-gold{{background:rgba(255,215,0,.15);color:#ffd700}}
.badge-tier-diamond{{background:rgba(185,242,255,.2);color:#b9f2ff}}
.badge-progress{{height:3px;background:var(--bg);border-radius:2px;overflow:hidden;margin-top:.15rem}}
.badge-progress-fill{{height:100%;border-radius:2px;transition:width .6s ease}}
.badge-progress-text{{
  font-family:var(--font-mono);font-size:.58rem;color:var(--text-muted);
  display:flex;justify-content:space-between;
}}
.badge-tooltip{{
  display:none;position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);
  background:var(--bg-card);border:1px solid var(--border-light);border-radius:var(--radius-sm);
  padding:.5rem .65rem;font-family:var(--font-mono);font-size:.62rem;color:var(--text-dim);
  white-space:nowrap;z-index:50;box-shadow:0 4px 16px rgba(0,0,0,.5);
  pointer-events:none;line-height:1.6;text-align:center;
}}
.badge-tooltip::after{{
  content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);
  border:5px solid transparent;border-top-color:var(--border-light);
}}
.badge-card:hover .badge-tooltip{{display:block}}
.tt-desc{{color:var(--text);font-weight:600;margin-bottom:.2rem}}
.tt-tier{{color:var(--text-muted)}}
.tt-tier.tt-done{{color:var(--green)}}
.tt-tier.tt-next{{color:var(--accent-light);font-weight:700}}
@media(max-width:768px){{.badges-grid{{grid-template-columns:repeat(auto-fill,minmax(145px,1fr))}}}}
.lang-toggle{{
  position:absolute;top:1rem;right:1rem;font-family:var(--font-mono);font-size:.78rem;
  padding:.35rem .8rem;border-radius:20px;border:1px solid var(--border);
  background:var(--bg-card);color:var(--text-dim);cursor:pointer;transition:all .2s;z-index:10;
}}
.lang-toggle:hover{{border-color:var(--accent);color:var(--text)}}
</style>
</head>
<body>
<div class="app">
<div class="header">
  <h1><img class="mc-icon" style="width:48px;height:48px;margin-right:.3rem" src="https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.21.5/assets/minecraft/textures/item/diamond_pickaxe.png" alt="pickaxe"> {title}</h1>
  <p id="subtitle"></p>
  <div class="meta" id="globalMeta"></div>
  <div class="sync-date" id="syncDate"></div>
  <button id="langToggle" class="lang-toggle"></button>
</div>
<div class="nav" id="nav"></div>
<div id="content"></div>
</div>
<script>
// ═══════════════════════════════════════
// DATA — auto-generated by generate.py
// ═══════════════════════════════════════
const PLAYERS_DATA = {data_json};

// ═══════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════
const PALETTE = ['#7c6aef','#3ecf8e','#ef6a6a','#efaa6a','#6aafef','#ef6ac0','#6aefd9','#efd96a','#a86aef'];
const PLAYER_COLORS_MAP = {{}};
const playerNames = Object.keys(PLAYERS_DATA).sort((a,b)=>PLAYERS_DATA[b].play_hours-PLAYERS_DATA[a].play_hours);
playerNames.forEach((n,i)=>PLAYER_COLORS_MAP[n]=PALETTE[i%PALETTE.length]);

// ═══════════════════════════════════════
// MINECRAFT ITEM ICONS
// ═══════════════════════════════════════
const _MI='https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.21.5/assets/minecraft/textures/item/';
const _MB='https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.21.5/assets/minecraft/textures/block/';
const _MW='https://minecraft.wiki/images/Invicon_';
const MC_ICONS={{
  diamond_pickaxe:_MI+'diamond_pickaxe.png',
  diamond_axe:_MI+'diamond_axe.png',
  diamond_sword:_MI+'diamond_sword.png',
  netherite_sword:_MI+'netherite_sword.png',
  iron_sword:_MI+'iron_sword.png',
  iron_chestplate:_MI+'iron_chestplate.png',
  shield:_MW+'Shield.png',
  bow:_MI+'bow.png',
  crossbow:_MI+'crossbow_standby.png',
  elytra:_MI+'elytra.png',
  fishing_rod:_MI+'fishing_rod.png',
  diamond:_MI+'diamond.png',
  blaze_rod:_MI+'blaze_rod.png',
  ender_pearl:_MI+'ender_pearl.png',
  emerald:_MI+'emerald.png',
  nether_star:_MI+'nether_star.png',
  golden_apple:_MI+'golden_apple.png',
  paper:_MI+'paper.png',
  saddle:_MI+'saddle.png',
  clock:_MI+'clock_00.png',
  compass:_MI+'compass_00.png',
  filled_map:_MI+'filled_map.png',
  enchanted_book:_MI+'enchanted_book.png',
  feather:_MI+'feather.png',
  wheat:_MI+'wheat.png',
  wheat_seeds:_MI+'wheat_seeds.png',
  rabbit_foot:_MI+'rabbit_foot.png',
  leather_boots:_MI+'leather_boots.png',
  gold_ingot:_MI+'gold_ingot.png',
  iron_ingot:_MI+'iron_ingot.png',
  copper_ingot:_MI+'copper_ingot.png',
  rotten_flesh:_MI+'rotten_flesh.png',
  skeleton_skull:_MW+'Skeleton_Skull.png',
  totem_of_undying:_MI+'totem_of_undying.png',
  oak_boat:_MI+'oak_boat.png',
  egg:_MI+'egg.png',
  torch:_MB+'torch.png',
  cod:_MI+'cod.png',
  oak_sapling:_MB+'oak_sapling.png',
  oak_door:_MI+'oak_door.png',
  oak_planks:_MB+'oak_planks.png',
  netherrack:_MW+'Netherrack.png',
  ancient_debris:_MW+'Ancient_Debris.png',
  crafting_table:_MW+'Crafting_Table.png',
  chest:_MW+'Chest.png',
  white_bed:_MW+'White_Bed.png',
  anvil:_MW+'Anvil.png',
  tnt:_MW+'TNT.png',
  target:_MW+'Target.png',
}};
function mcIcon(name){{
  const src=MC_ICONS[name]||(_MI+name+'.png');
  return '<img class="mc-icon" src="'+src+'" alt="'+name+'" loading="lazy">';
}}

// ═══════════════════════════════════════
// I18N
// ═══════════════════════════════════════
const SYNC_FR='{sync_date_fr}',SYNC_EN='{sync_date_en}';
let lang=localStorage.getItem('mc-dash-lang')||(navigator.language.startsWith('fr')?'fr':'en');
let currentSection='overview';
const T={{fr:{{
subtitle:'Dashboard de statistiques du serveur',sync_prefix:'Dernière synchronisation',
players:'joueurs',hours_played:'h de jeu',blocks_mined_meta:'blocs minés',mobs_killed_meta:'mobs tués',
nav_overview:mcIcon('filled_map')+' Vue globale',nav_leaderboards:mcIcon('nether_star')+' Classements',
total_playtime:'Temps de jeu total',blocks_mined:'Blocs minés',mobs_killed:'Mobs tués',items_crafted:'Items craftés',
chart_playtime:'Temps de jeu par joueur',chart_distance:'Distance totale (km)',
chart_mined:'Blocs minés par joueur',chart_kills:'Mobs tués par joueur',chart_multi:'Comparaison multi-stats',
axis_hours:'Heures',axis_blocks:'Blocs',axis_kills:'Kills',axis_km:'km',
radar_playtime:'Temps de jeu',radar_mined:'Blocs minés',radar_kills:'Mobs tués',
radar_distance:'Distance',radar_crafted:'Items craftés',radar_deaths:'Morts',
lb_playtime:mcIcon('clock')+' Temps de jeu',lb_mined:mcIcon('diamond_pickaxe')+' Blocs minés',lb_kills:mcIcon('diamond_sword')+' Mobs tués',
lb_deaths:mcIcon('skeleton_skull')+' Morts',lb_distance:mcIcon('filled_map')+' Distance',lb_crafted:mcIcon('crafting_table')+' Items craftés',
lb_pvp:mcIcon('iron_sword')+' PvP Kills',lb_enchant:mcIcon('enchanted_book')+' Enchantements',lb_fish:mcIcon('cod')+' Poissons',
lb_trades:mcIcon('emerald')+' Échanges PNJ',lb_breed:mcIcon('egg')+' Élevage',lb_jumps:mcIcon('rabbit_foot')+' Sauts',
chart_deathcauses:'Causes de mort (tous)',chart_dist_type:'Distances par type',
d_walk:'Marche',d_sprint:'Sprint',d_swim:'Nage',d_fly:'Vol créatif',
d_aviate:'Elytra',d_boat:'Bateau',d_horse:'Cheval',d_minecart:'Wagon',
d_climb:'Escalade',d_crouch:'Accroupi',d_fall:'Chute',
d_walk_on_water:"Sur l'eau",d_walk_under_water:"Sous l'eau",
arch_new:'Nouveau',arch_miner:'Mineur',arch_fighter:'Combattant',
arch_explorer:'Explorateur',arch_builder:'Bâtisseur',arch_farmer:'Fermier',
time_mining:'⛏ Minage',time_combat:'⚔ Combat',time_travel:'🚶 Déplacement',
time_craft:'🔨 Craft',time_other:'💤 Autre',
playtime:'Temps de jeu',kd_ratio:'K/D ratio',traveled:'Parcourus',per_hour:'/h',
deaths:'Morts',enchantments:'Enchantements',chests_opened:'Coffres ouverts',
fish_caught:'Poissons pêchés',npc_trades:'Échanges PNJ',pvp:'PvP',pve:'PvE',
card_time_est:'Répartition du temps estimée',card_distances:'Distances parcourues',
card_killed_by:'Tué par',card_treemap:'Blocs minés — Treemap',
card_top15_mined:'Top 15 blocs minés',card_top10_killed:'Top 10 mobs tués',
card_top10_crafted:'Top 10 items craftés',card_tools_broken:'Outils cassés',card_fun_facts:'Fun Facts',
no_death:'Aucune mort',no_data:'Pas assez de données',
no_blocks:'Aucun bloc miné',no_tools:'Aucun outil cassé',
badges_title:'Badges & Achievements',badges_unlocked:'badges débloqués',
tier_locked:'🔒',tier_bronze:mcIcon('copper_ingot')+' Bronze',tier_silver:mcIcon('iron_ingot')+' Argent',tier_gold:mcIcon('gold_ingot')+' Or',tier_diamond:mcIcon('diamond')+' Diamant',
cat_mining:mcIcon('diamond_pickaxe')+' Minage',cat_combat:mcIcon('diamond_sword')+' Combat',cat_survival:mcIcon('skeleton_skull')+' Survie',
cat_exploration:mcIcon('compass')+' Exploration',cat_farming:mcIcon('wheat')+' Farming & Économie',
cat_craft:mcIcon('crafting_table')+' Craft & Technique',cat_daily:mcIcon('white_bed')+' Vie Quotidienne',cat_prestige:mcIcon('nether_star')+' Prestige',
b_mineur:'Mineur',b_diamantaire:'Diamantaire',b_nether_mole:'Nether Mole',
b_ancient_debris:'Débris Anciens',b_bucheron:'Bûcheron',b_chasseur:'Chasseur',
b_ender_slayer:'Ender Slayer',b_nether_warrior:'Nether Warrior',b_berserker:'Berserker',
b_pvp_champion:'PvP Champion',b_raid_master:'Raid Master',b_increvable:'Increvable',
b_kamikaze:'Kamikaze',b_bouclier_humain:'Bouclier Humain',b_punching_bag:'Punching Bag',
b_globe_trotter:'Globe-trotter',b_marathonien:'Marathonien',b_sprinter:'Sprinter',
b_aviateur:'Aviateur',b_marin:'Marin',b_cavalier:'Cavalier',
b_fermier:'Fermier',b_pecheur:'Pêcheur',b_commercant:'Commerçant',
b_recolte:'Récolte',b_artisan:'Artisan',b_enchanteur:'Enchanteur',
b_paperasse:'Paperasse',b_forgeron:'Forgeron',b_rat_de_coffre:'Rat de coffre',
b_dormeur:'Dormeur',b_kangourou:'Kangourou',b_no_life:'No-Life',
b_all_rounder:'All-Rounder',b_legende:'Légende',
bd_mineur:'Miner des blocs au total',bd_diamantaire:'Miner du minerai de diamant',
bd_nether_mole:'Miner de la netherrack',bd_ancient_debris:'Miner des débris antiques',
bd_bucheron:'Couper des bûches (tous types)',bd_chasseur:'Tuer des mobs',
bd_ender_slayer:'Tuer des Endermen',bd_nether_warrior:'Tuer des Wither Skeletons & Blazes',
bd_berserker:'Infliger des dégâts (en cœurs)',bd_pvp_champion:"Tuer d'autres joueurs",
bd_raid_master:'Tuer Pillagers, Vindicators & Ravagers',bd_increvable:'Ratio heures jouées / morts',
bd_kamikaze:'Mourir de nombreuses fois',bd_bouclier_humain:"Se faire tuer par d'autres joueurs",
bd_punching_bag:'Encaisser des dégâts (en cœurs)',bd_globe_trotter:'Parcourir des km au total',
bd_marathonien:'Marcher en km',bd_sprinter:'Sprinter en km',bd_aviateur:'Voler en Elytra en km',
bd_marin:'Naviguer en bateau en km',bd_cavalier:'Chevaucher en km',bd_fermier:'Élever des animaux',
bd_pecheur:'Pêcher des poissons',bd_commercant:'Échanger avec des villageois',
bd_recolte:'Récolter blé, betteraves, carottes & patates',bd_artisan:'Crafter des items au total',
bd_enchanteur:'Enchanter des items',bd_paperasse:'Crafter du papier',
bd_forgeron:"Casser des outils à force d'usage",bd_rat_de_coffre:'Ouvrir des coffres',
bd_dormeur:'Dormir dans un lit',bd_kangourou:'Faire des sauts',
bd_no_life:'Accumuler des heures de jeu',bd_all_rounder:'Bronze dans chaque catégorie',
bd_legende:'Obtenir Or ou mieux sur des badges',
ff_endermen:(n,s)=>`A tué ${{n}} Endermen — environ ${{s}} stacks d'Ender Pearls`,
ff_death_rate:(m)=>`Meurt en moyenne toutes les ${{m}} minutes`,
ff_walk:(km,mar)=>`A marché ${{km}} km — soit ${{mar}} marathons`,
ff_jumps:(jph)=>`Saute ${{jph}} fois par heure en moyenne`,
ff_mining:(bpm)=>`Mine ${{bpm}} blocs par minute en moyenne`,
ff_sleep:(n,nph)=>`A dormi ${{n}} nuits Minecraft — ${{nph}} par heure de jeu`,
ff_chests:(n)=>`A ouvert ${{n}} coffres — un vrai fouineur`,
ff_pvp_target:(n)=>`Tué ${{n}} fois par d'autres joueurs — cible favorite du serveur`,
ff_elytra:(km,n)=>`${{km}} km en Elytra — l'équivalent de ${{n}} traversées de Paris`,
ff_damage:(h)=>`A infligé ${{h}} cœurs de dégâts au total`,
ff_trades:(n)=>`${{n}} échanges avec des villageois — le capitaliste du serveur`,
ff_tools:(n)=>`A cassé ${{n}} outils — pas très soigneux`,
ff_mob_kills:(n,kph)=>`${{n}} mobs tués — soit ${{kph}} par heure`,
ff_breeding:(n)=>`A élevé ${{n}} animaux — fermier dans l'âme`,
ff_fishing:(n)=>`A pêché ${{n}} poissons — le pêcheur du serveur`,
ff_total_dist:(km,eq)=>`${{km}} km parcourus au total — l'équivalent d'un ${{eq}}`,
ff_equiv_long:'Paris-Barcelone',ff_equiv_short:'Paris-Londres'
}},en:{{
subtitle:'Server statistics dashboard',sync_prefix:'Last sync',
players:'players',hours_played:'hours played',blocks_mined_meta:'blocks mined',mobs_killed_meta:'mobs killed',
nav_overview:mcIcon('filled_map')+' Overview',nav_leaderboards:mcIcon('nether_star')+' Leaderboards',
total_playtime:'Total playtime',blocks_mined:'Blocks mined',mobs_killed:'Mobs killed',items_crafted:'Items crafted',
chart_playtime:'Playtime per player',chart_distance:'Total distance (km)',
chart_mined:'Blocks mined per player',chart_kills:'Mobs killed per player',chart_multi:'Multi-stats comparison',
axis_hours:'Hours',axis_blocks:'Blocks',axis_kills:'Kills',axis_km:'km',
radar_playtime:'Playtime',radar_mined:'Blocks mined',radar_kills:'Mobs killed',
radar_distance:'Distance',radar_crafted:'Items crafted',radar_deaths:'Deaths',
lb_playtime:mcIcon('clock')+' Playtime',lb_mined:mcIcon('diamond_pickaxe')+' Blocks mined',lb_kills:mcIcon('diamond_sword')+' Mobs killed',
lb_deaths:mcIcon('skeleton_skull')+' Deaths',lb_distance:mcIcon('filled_map')+' Distance',lb_crafted:mcIcon('crafting_table')+' Items crafted',
lb_pvp:mcIcon('iron_sword')+' PvP Kills',lb_enchant:mcIcon('enchanted_book')+' Enchantments',lb_fish:mcIcon('cod')+' Fish caught',
lb_trades:mcIcon('emerald')+' NPC trades',lb_breed:mcIcon('egg')+' Breeding',lb_jumps:mcIcon('rabbit_foot')+' Jumps',
chart_deathcauses:'Death causes (all)',chart_dist_type:'Distance by type',
d_walk:'Walk',d_sprint:'Sprint',d_swim:'Swim',d_fly:'Creative flight',
d_aviate:'Elytra',d_boat:'Boat',d_horse:'Horse',d_minecart:'Minecart',
d_climb:'Climbing',d_crouch:'Crouching',d_fall:'Falling',
d_walk_on_water:'On water',d_walk_under_water:'Underwater',
arch_new:'Newcomer',arch_miner:'Miner',arch_fighter:'Fighter',
arch_explorer:'Explorer',arch_builder:'Builder',arch_farmer:'Farmer',
time_mining:'⛏ Mining',time_combat:'⚔ Combat',time_travel:'🚶 Travel',
time_craft:'🔨 Crafting',time_other:'💤 Other',
playtime:'Playtime',kd_ratio:'K/D ratio',traveled:'Traveled',per_hour:'/h',
deaths:'Deaths',enchantments:'Enchantments',chests_opened:'Chests opened',
fish_caught:'Fish caught',npc_trades:'NPC trades',pvp:'PvP',pve:'PvE',
card_time_est:'Estimated time breakdown',card_distances:'Distances traveled',
card_killed_by:'Killed by',card_treemap:'Blocks mined — Treemap',
card_top15_mined:'Top 15 blocks mined',card_top10_killed:'Top 10 mobs killed',
card_top10_crafted:'Top 10 items crafted',card_tools_broken:'Tools broken',card_fun_facts:'Fun Facts',
no_death:'No deaths',no_data:'Not enough data',
no_blocks:'No blocks mined',no_tools:'No tools broken',
badges_title:'Badges & Achievements',badges_unlocked:'badges unlocked',
tier_locked:'🔒',tier_bronze:mcIcon('copper_ingot')+' Bronze',tier_silver:mcIcon('iron_ingot')+' Silver',tier_gold:mcIcon('gold_ingot')+' Gold',tier_diamond:mcIcon('diamond')+' Diamond',
cat_mining:mcIcon('diamond_pickaxe')+' Mining',cat_combat:mcIcon('diamond_sword')+' Combat',cat_survival:mcIcon('skeleton_skull')+' Survival',
cat_exploration:mcIcon('compass')+' Exploration',cat_farming:mcIcon('wheat')+' Farming & Economy',
cat_craft:mcIcon('crafting_table')+' Craft & Tech',cat_daily:mcIcon('white_bed')+' Daily life',cat_prestige:mcIcon('nether_star')+' Prestige',
b_mineur:'Miner',b_diamantaire:'Diamond Hunter',b_nether_mole:'Nether Mole',
b_ancient_debris:'Ancient Debris',b_bucheron:'Lumberjack',b_chasseur:'Hunter',
b_ender_slayer:'Ender Slayer',b_nether_warrior:'Nether Warrior',b_berserker:'Berserker',
b_pvp_champion:'PvP Champion',b_raid_master:'Raid Master',b_increvable:'Unkillable',
b_kamikaze:'Kamikaze',b_bouclier_humain:'Human Shield',b_punching_bag:'Punching Bag',
b_globe_trotter:'Globe-trotter',b_marathonien:'Marathoner',b_sprinter:'Sprinter',
b_aviateur:'Aviator',b_marin:'Sailor',b_cavalier:'Rider',
b_fermier:'Farmer',b_pecheur:'Angler',b_commercant:'Merchant',
b_recolte:'Harvest',b_artisan:'Artisan',b_enchanteur:'Enchanter',
b_paperasse:'Paperwork',b_forgeron:'Blacksmith',b_rat_de_coffre:'Chest rat',
b_dormeur:'Sleeper',b_kangourou:'Kangaroo',b_no_life:'No-Life',
b_all_rounder:'All-Rounder',b_legende:'Legend',
bd_mineur:'Mine blocks in total',bd_diamantaire:'Mine diamond ore',
bd_nether_mole:'Mine netherrack',bd_ancient_debris:'Mine ancient debris',
bd_bucheron:'Chop logs (all types)',bd_chasseur:'Kill mobs',
bd_ender_slayer:'Kill Endermen',bd_nether_warrior:'Kill Wither Skeletons & Blazes',
bd_berserker:'Deal damage (in hearts)',bd_pvp_champion:'Kill other players',
bd_raid_master:'Kill Pillagers, Vindicators & Ravagers',bd_increvable:'Hours played / deaths ratio',
bd_kamikaze:'Die many times',bd_bouclier_humain:'Get killed by other players',
bd_punching_bag:'Take damage (in hearts)',bd_globe_trotter:'Travel km in total',
bd_marathonien:'Walk in km',bd_sprinter:'Sprint in km',bd_aviateur:'Fly with Elytra in km',
bd_marin:'Sail by boat in km',bd_cavalier:'Ride in km',bd_fermier:'Breed animals',
bd_pecheur:'Catch fish',bd_commercant:'Trade with villagers',
bd_recolte:'Harvest wheat, beetroot, carrots & potatoes',bd_artisan:'Craft items in total',
bd_enchanteur:'Enchant items',bd_paperasse:'Craft paper',
bd_forgeron:'Break tools from use',bd_rat_de_coffre:'Open chests',
bd_dormeur:'Sleep in a bed',bd_kangourou:'Jump',
bd_no_life:'Accumulate play hours',bd_all_rounder:'Bronze in every category',
bd_legende:'Get Gold or better on badges',
ff_endermen:(n,s)=>`Killed ${{n}} Endermen — about ${{s}} stacks of Ender Pearls`,
ff_death_rate:(m)=>`Dies on average every ${{m}} minutes`,
ff_walk:(km,mar)=>`Walked ${{km}} km — that's ${{mar}} marathons`,
ff_jumps:(jph)=>`Jumps ${{jph}} times per hour on average`,
ff_mining:(bpm)=>`Mines ${{bpm}} blocks per minute on average`,
ff_sleep:(n,nph)=>`Slept ${{n}} Minecraft nights — ${{nph}} per hour played`,
ff_chests:(n)=>`Opened ${{n}} chests — a real snoop`,
ff_pvp_target:(n)=>`Killed ${{n}} times by other players — the server's favorite target`,
ff_elytra:(km,n)=>`${{km}} km by Elytra — the equivalent of ${{n}} trips across Paris`,
ff_damage:(h)=>`Dealt ${{h}} hearts of damage in total`,
ff_trades:(n)=>`${{n}} trades with villagers — the server's capitalist`,
ff_tools:(n)=>`Broke ${{n}} tools — not very careful`,
ff_mob_kills:(n,kph)=>`${{n}} mobs killed — that's ${{kph}} per hour`,
ff_breeding:(n)=>`Bred ${{n}} animals — farmer at heart`,
ff_fishing:(n)=>`Caught ${{n}} fish — the server's angler`,
ff_total_dist:(km,eq)=>`${{km}} km traveled in total — the equivalent of a ${{eq}}`,
ff_equiv_long:'Paris-Barcelona',ff_equiv_short:'Paris-London'
}}}};
function t(k){{const a=[].slice.call(arguments,1);const v=T[lang]?.[k];return typeof v==='function'?v.apply(null,a):(v||k)}}
function label(k){{const dl=T[lang]?.['d_'+k];if(dl)return dl;return k.replace(/_/g,' ').replace(/\\b\\w/g,c=>c.toUpperCase())}}
function fmt(n){{if(n>=1e6)return(n/1e6).toFixed(1)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'k';return n.toLocaleString(lang==='fr'?'fr-FR':'en-US')}}
function pct(v,m){{return m?Math.round(v/m*100):0}}

// ═══════════════════════════════════════
// ARCHETYPE DETECTION
// ═══════════════════════════════════════
function getArchetype(p){{
  if(p.play_hours<1)return{{name:t('arch_new'),icon:mcIcon('oak_sapling'),color:'var(--text-muted)'}};
  const h=p.play_hours;
  const scores={{
    miner:p.total_mined/h,
    fighter:p.mob_kills/h,
    explorer:p.total_distance_km/h,
    builder:p.total_crafted/h,
    farmer:(p.animals_bred+p.traded_with_villager+p.fish_caught)/h
  }};
  const types={{
    miner:{{name:t('arch_miner'),icon:mcIcon('diamond_pickaxe'),color:'var(--yellow)'}},
    fighter:{{name:t('arch_fighter'),icon:mcIcon('diamond_sword'),color:'var(--red)'}},
    explorer:{{name:t('arch_explorer'),icon:mcIcon('compass'),color:'var(--green)'}},
    builder:{{name:t('arch_builder'),icon:mcIcon('oak_planks'),color:'var(--cyan)'}},
    farmer:{{name:t('arch_farmer'),icon:mcIcon('wheat'),color:'var(--orange)'}}
  }};
  const top=Object.entries(scores).sort((a,b)=>b[1]-a[1])[0][0];
  return types[top];
}}

// ═══════════════════════════════════════
// FUN FACTS GENERATOR
// Scored by impressiveness vs server max
// ═══════════════════════════════════════
const _funFactMaxCache={{}};
function _maxOf(fn){{
  const key=fn.toString();
  if(!_funFactMaxCache[key])_funFactMaxCache[key]=Math.max(...playerNames.map(n=>fn(PLAYERS_DATA[n])||0));
  return _funFactMaxCache[key]||1;
}}

function getFunFacts(name,p){{
  const facts=[];const h=p.play_hours;if(h<0.5)return facts;

  const ek=p.killed_top10?.enderman||0;
  if(ek>50)facts.push({{score:ek/_maxOf(p=>p.killed_top10?.enderman||0),icon:mcIcon('ender_pearl'),text:t('ff_endermen',fmt(ek),Math.floor(ek/64))}});

  if(p.deaths>3&&h>1){{const mpd=Math.round(h*60/p.deaths);const deathRate=p.deaths/h;
    facts.push({{score:deathRate/_maxOf(p=>p.play_hours>1?p.deaths/p.play_hours:0),icon:mcIcon('skeleton_skull'),text:t('ff_death_rate',mpd)}})}}

  const wk=p.distances?.walk||0;
  if(wk>20)facts.push({{score:wk/_maxOf(p=>p.distances?.walk||0),icon:mcIcon('leather_boots'),text:t('ff_walk',wk.toFixed(0),(wk/42.195).toFixed(1))}});

  if(p.jumps>500&&h>1)facts.push({{score:p.jumps/_maxOf(p=>p.jumps||0),icon:mcIcon('rabbit_foot'),text:t('ff_jumps',Math.round(p.jumps/h))}});

  if(p.total_mined>500&&h>1)facts.push({{score:p.total_mined/_maxOf(p=>p.total_mined||0),icon:mcIcon('diamond_pickaxe'),text:t('ff_mining',(p.total_mined/(h*60)).toFixed(1))}});

  if(p.sleep_in_bed>5)facts.push({{score:p.sleep_in_bed/_maxOf(p=>p.sleep_in_bed||0),icon:mcIcon('white_bed'),text:t('ff_sleep',p.sleep_in_bed,(p.sleep_in_bed/h).toFixed(1))}});

  if(p.open_chest>100)facts.push({{score:p.open_chest/_maxOf(p=>p.open_chest||0),icon:mcIcon('chest'),text:t('ff_chests',fmt(p.open_chest))}});

  const pvpD=(p.killed_by?.player)||0;
  if(pvpD>3)facts.push({{score:pvpD/_maxOf(p=>(p.killed_by?.player)||0),icon:mcIcon('bow'),text:t('ff_pvp_target',pvpD)}});

  const ely=p.distances?.aviate||0;
  if(ely>50)facts.push({{score:ely/_maxOf(p=>p.distances?.aviate||0),icon:mcIcon('elytra'),text:t('ff_elytra',ely.toFixed(0),Math.round(ely/6))}});

  if(p.damage_dealt>10000)facts.push({{score:p.damage_dealt/_maxOf(p=>p.damage_dealt||0),icon:mcIcon('netherite_sword'),text:t('ff_damage',fmt(Math.round(p.damage_dealt/20)))}});

  if(p.traded_with_villager>50)facts.push({{score:p.traded_with_villager/_maxOf(p=>p.traded_with_villager||0),icon:mcIcon('emerald'),text:t('ff_trades',fmt(p.traded_with_villager))}});

  const brk=Object.values(p.broken||{{}}).reduce((s,v)=>s+v,0);
  if(brk>5)facts.push({{score:brk/_maxOf(p=>Object.values(p.broken||{{}}).reduce((s,v)=>s+v,0)),icon:mcIcon('anvil'),text:t('ff_tools',brk)}});

  if(p.mob_kills>100)facts.push({{score:p.mob_kills/_maxOf(p=>p.mob_kills||0),icon:mcIcon('diamond_sword'),text:t('ff_mob_kills',fmt(p.mob_kills),Math.round(p.mob_kills/h))}});

  if(p.animals_bred>20)facts.push({{score:p.animals_bred/_maxOf(p=>p.animals_bred||0),icon:mcIcon('egg'),text:t('ff_breeding',p.animals_bred)}});

  if(p.fish_caught>10)facts.push({{score:p.fish_caught/_maxOf(p=>p.fish_caught||0),icon:mcIcon('fishing_rod'),text:t('ff_fishing',p.fish_caught)}});

  const totalDist=p.total_distance_km;
  if(totalDist>100)facts.push({{score:totalDist/_maxOf(p=>p.total_distance_km||0),icon:mcIcon('compass'),text:t('ff_total_dist',totalDist.toFixed(0),totalDist>1000?t('ff_equiv_long'):t('ff_equiv_short'))}});

  facts.sort((a,b)=>b.score-a.score);
  return facts.slice(0,5);
}}

// ═══════════════════════════════════════
// TREEMAP BUILDER
// ═══════════════════════════════════════
function buildTreemapHtml(entries){{
  if(!entries.length)return '<div style="color:var(--text-muted);padding:1rem;font-family:var(--font-mono);font-size:.8rem">'+t('no_blocks')+'</div>';
  const total=entries.reduce((s,[_,v])=>s+v,0);
  const colors=['#7c6aef','#3ecf8e','#ef6a6a','#efaa6a','#6aafef','#6aefd9','#efd96a','#ef6ac0','#a86aef','#5a9e6f','#9e5a5a','#5a6f9e','#9e8b5a','#5a9e9e','#8b8b96'];
  return `<div class="treemap">${{entries.slice(0,15).map(([k,v],i)=>{{
    const p=(v/total*100);const area=Math.max(p,2.5);
    const showLabel=p>4;
    return `<div class="treemap-item" style="flex:${{area}};background:${{colors[i%colors.length]}}" title="${{label(k)}}: ${{fmt(v)}} (${{p.toFixed(1)}}%)">
      <span>${{showLabel?label(k)+'<br><span class=tm-count>'+fmt(v)+'</span>':fmt(v)}}</span></div>`;
  }}).join('')}}</div>`;
}}

// ═══════════════════════════════════════
// BROKEN TOOLS
// ═══════════════════════════════════════
function buildBrokenHtml(broken){{
  const entries=Object.entries(broken||{{}}).sort((a,b)=>b[1]-a[1]);
  if(!entries.length)return '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:.8rem">'+t('no_tools')+'</div>';
  return `<div class="broken-grid">${{entries.map(([k,v])=>
    `<span class="broken-tag">${{label(k)}} <span class="bt-count">×${{v}}</span></span>`
  ).join('')}}</div>`;
}}

// ═══════════════════════════════════════
// TIME ESTIMATION
// ═══════════════════════════════════════
function estimateTime(p){{
  const h=p.play_hours;if(h<1)return null;
  const totalS=h*3600;
  // Minage: ~1s par bloc
  let miningS=p.total_mined;
  // Combat: damage / 10 DPS moyen
  let combatS=p.damage_dealt/10;
  // Déplacement: distance / vitesse
  const speeds={{walk:4.3,sprint:5.6,swim:2.2,fly:10.9,aviate:33,boat:8,horse:9.9,minecart:8,climb:2.4,crouch:1.3,fall:20,walk_on_water:4.3,walk_under_water:2.2}};
  let travelS=0;
  Object.entries(p.distances||{{}}).forEach(([mode,km])=>{{travelS+=(km*1000)/(speeds[mode]||4.3)}});
  // Craft: ~1.5s par opération
  let craftS=p.total_crafted*1.5;
  // Normaliser si dépasse 85% du temps
  const estTotal=miningS+combatS+travelS+craftS;
  if(estTotal>totalS*0.85){{
    const scale=(totalS*0.85)/estTotal;
    miningS*=scale;combatS*=scale;travelS*=scale;craftS*=scale;
  }}
  const otherS=Math.max(0,totalS-(miningS+combatS+travelS+craftS));
  const toH=s=>Math.round(s/3600*10)/10;
  return [
    {{label:t('time_mining'),hours:toH(miningS),color:'#efd96a'}},
    {{label:t('time_combat'),hours:toH(combatS),color:'#ef6a6a'}},
    {{label:t('time_travel'),hours:toH(travelS),color:'#3ecf8e'}},
    {{label:t('time_craft'),hours:toH(craftS),color:'#6aefd9'}},
    {{label:t('time_other'),hours:toH(otherS),color:'#5c5c68'}}
  ];
}}

// ═══════════════════════════════════════
// ANIMATED COUNTERS
// ═══════════════════════════════════════
function animateCounters(){{
  const obs=new IntersectionObserver((entries)=>{{
    entries.forEach(entry=>{{
      if(entry.isIntersecting&&!entry.target.dataset.done){{
        entry.target.dataset.done='1';
        const target=parseFloat(entry.target.dataset.target);
        const suffix=entry.target.dataset.suffix||'';
        const isFloat=String(target).includes('.');
        const duration=1000;const start=performance.now();
        const step=(now)=>{{
          const elapsed=now-start;const progress=Math.min(elapsed/duration,1);
          const ease=1-Math.pow(1-progress,3);
          const current=target*ease;
          entry.target.textContent=(isFloat?current.toFixed(1):fmt(Math.round(current)))+suffix;
          if(progress<1)requestAnimationFrame(step);
        }};
        requestAnimationFrame(step);
      }}
    }});
  }},{{threshold:0.2}});
  document.querySelectorAll('[data-target]').forEach(c=>obs.observe(c));
}}

Chart.defaults.color='#8b8b96';
Chart.defaults.borderColor='rgba(42,42,53,0.5)';
Chart.defaults.font.family="'JetBrains Mono',monospace";
Chart.defaults.font.size=11;
Chart.defaults.plugins.legend.labels.boxWidth=12;
Chart.defaults.plugins.legend.labels.padding=12;

const charts={{}};
function destroyChart(id){{if(charts[id]){{charts[id].destroy();delete charts[id]}}}}

// ═══════════════════════════════════════
// GLOBAL AGGREGATION
// ═══════════════════════════════════════
const totalHours=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].play_hours,0);
const totalMined=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_mined,0);
const totalKills=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].mob_kills,0);
const totalDeaths=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].deaths,0);
const totalDist=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_distance_km,0);
const totalCrafted=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_crafted,0);

function updateGlobalMeta(){{
  document.getElementById('globalMeta').innerHTML=`
  <span><b>${{playerNames.length}}</b> ${{t('players')}}</span>
  <span><b>${{totalHours.toFixed(0)}}</b> ${{t('hours_played')}}</span>
  <span><b>${{fmt(totalMined)}}</b> ${{t('blocks_mined_meta')}}</span>
  <span><b>${{fmt(totalKills)}}</b> ${{t('mobs_killed_meta')}}</span>`;
}}
updateGlobalMeta();

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════
const navEl=document.getElementById('nav');
const contentEl=document.getElementById('content');

function buildNav(){{
  let h=`<button class="active" data-section="overview">${{t('nav_overview')}}</button>`;
  h+=`<button data-section="leaderboards">${{t('nav_leaderboards')}}</button>`;
  playerNames.forEach(name=>{{
    const dot=`<span class="player-dot" style="background:${{PLAYER_COLORS_MAP[name]}}"></span>`;
    h+=`<button data-section="player-${{name}}">${{dot}}${{name}}</button>`;
  }});
  navEl.innerHTML=h;
  navEl.querySelectorAll('button').forEach(btn=>{{
    btn.addEventListener('click',()=>{{
      navEl.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      showSection(btn.dataset.section);
    }});
  }});
}}

function showSection(id){{
  currentSection=id;
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  const el=document.getElementById(id);
  if(el)el.classList.add('active');
  if(id==='overview')renderOverviewCharts();
  if(id==='leaderboards')renderLeaderboardCharts();
  if(id.startsWith('player-'))renderPlayerCharts(id.replace('player-',''));
  setTimeout(animateCounters,50);
}}

function buildAllSections(){{
  let h='';h+=buildOverview();h+=buildLeaderboards();
  playerNames.forEach(name=>{{h+=buildPlayerSection(name)}});
  contentEl.innerHTML=h;
}}

// ═══════════════════════════════════════
// OVERVIEW
// ═══════════════════════════════════════
function buildOverview(){{
  return `
  <div class="section active" id="overview">
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--accent-light)" data-target="${{totalHours.toFixed(0)}}" data-suffix="h">0</div><div class="label">${{t('total_playtime')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--green)" data-target="${{totalMined}}">0</div><div class="label">${{t('blocks_mined')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--red)" data-target="${{totalKills}}">0</div><div class="label">${{t('mobs_killed')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--orange)" data-target="${{totalCrafted}}">0</div><div class="label">${{t('items_crafted')}}</div></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${{mcIcon('clock')}}</span> ${{t('chart_playtime')}}</h3><div class="chart-wrap"><canvas id="chart-playtime"></canvas></div></div>
      <div class="card"><h3><span class="icon">${{mcIcon('filled_map')}}</span> ${{t('chart_distance')}}</h3><div class="chart-wrap"><canvas id="chart-distance"></canvas></div></div>
      <div class="card"><h3><span class="icon">${{mcIcon('diamond_pickaxe')}}</span> ${{t('chart_mined')}}</h3><div class="chart-wrap"><canvas id="chart-mined"></canvas></div></div>
      <div class="card"><h3><span class="icon">${{mcIcon('diamond_sword')}}</span> ${{t('chart_kills')}}</h3><div class="chart-wrap"><canvas id="chart-kills"></canvas></div></div>
    </div>
    <div class="card"><h3><span class="icon">📈</span> ${{t('chart_multi')}}</h3>
      <div class="chart-wrap" style="max-height:420px"><canvas id="chart-radar"></canvas></div>
    </div>
  </div>`;
}}

function renderOverviewCharts(){{
  const barOpts=(lbl)=>({{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
    scales:{{y:{{title:{{display:true,text:lbl}},grid:{{color:'rgba(42,42,53,0.3)'}}}},x:{{grid:{{display:false}}}}}}}});
  const mkBar=(id,data,tooltipSuffix,yLabel)=>{{
    destroyChart(id);
    charts[id]=new Chart(document.getElementById(id),{{type:'bar',data:{{
      labels:playerNames,datasets:[{{data,backgroundColor:playerNames.map(n=>PLAYER_COLORS_MAP[n]+'cc'),
        borderColor:playerNames.map(n=>PLAYER_COLORS_MAP[n]),borderWidth:1,borderRadius:4}}]
    }},options:{{...barOpts(yLabel),plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.parsed.y+(tooltipSuffix||'')}}}}}}}}}});
  }};
  mkBar('chart-playtime',playerNames.map(n=>PLAYERS_DATA[n].play_hours),'h',t('axis_hours'));
  mkBar('chart-distance',playerNames.map(n=>PLAYERS_DATA[n].total_distance_km),' km',t('axis_km'));
  mkBar('chart-mined',playerNames.map(n=>PLAYERS_DATA[n].total_mined),' blocs',t('axis_blocks'));
  mkBar('chart-kills',playerNames.map(n=>PLAYERS_DATA[n].mob_kills),' kills',t('axis_kills'));

  destroyChart('chart-radar');
  const top5=playerNames.slice(0,5);
  const rm=['play_hours','total_mined','mob_kills','total_distance_km','total_crafted','deaths'];
  const rl=[t('radar_playtime'),t('radar_mined'),t('radar_kills'),t('radar_distance'),t('radar_crafted'),t('radar_deaths')];
  const mx=rm.map(m=>Math.max(...playerNames.map(n=>PLAYERS_DATA[n][m]||0)));
  charts['chart-radar']=new Chart(document.getElementById('chart-radar'),{{type:'radar',data:{{
    labels:rl,datasets:top5.map(name=>({{label:name,
      data:rm.map((m,i)=>mx[i]?((PLAYERS_DATA[name][m]||0)/mx[i]*100):0),
      borderColor:PLAYER_COLORS_MAP[name],backgroundColor:PLAYER_COLORS_MAP[name]+'22',
      borderWidth:2,pointRadius:3,pointBackgroundColor:PLAYER_COLORS_MAP[name]}}))
  }},options:{{responsive:true,maintainAspectRatio:false,
    scales:{{r:{{grid:{{color:'rgba(42,42,53,0.4)'}},angleLines:{{color:'rgba(42,42,53,0.3)'}},ticks:{{display:false}},pointLabels:{{font:{{size:12}}}}}}}},
    plugins:{{tooltip:{{callbacks:{{label:ctx=>{{
      const idx=ctx.dataIndex;const name=ctx.dataset.label;const raw=PLAYERS_DATA[name][rm[idx]]||0;
      return `${{name}}: ${{typeof raw==='number'&&raw%1?raw.toFixed(1):fmt(raw)}}`;
    }}}}}}}}}}}});
}}

// ═══════════════════════════════════════
// LEADERBOARDS
// ═══════════════════════════════════════
function buildLeaderboards(){{
  const boards=[
    {{key:'play_hours',tkey:'lb_playtime',suffix:'h',color:'var(--accent-light)'}},
    {{key:'total_mined',tkey:'lb_mined',suffix:'',color:'var(--green)'}},
    {{key:'mob_kills',tkey:'lb_kills',suffix:'',color:'var(--red)'}},
    {{key:'deaths',tkey:'lb_deaths',suffix:'',color:'var(--orange)'}},
    {{key:'total_distance_km',tkey:'lb_distance',suffix:' km',color:'var(--blue)'}},
    {{key:'total_crafted',tkey:'lb_crafted',suffix:'',color:'var(--cyan)'}},
    {{key:'player_kills',tkey:'lb_pvp',suffix:'',color:'var(--pink)'}},
    {{key:'enchant_item',tkey:'lb_enchant',suffix:'',color:'var(--yellow)'}},
    {{key:'fish_caught',tkey:'lb_fish',suffix:'',color:'var(--teal)'}},
    {{key:'traded_with_villager',tkey:'lb_trades',suffix:'',color:'var(--accent-light)'}},
    {{key:'animals_bred',tkey:'lb_breed',suffix:'',color:'var(--pink)'}},
    {{key:'jumps',tkey:'lb_jumps',suffix:'',color:'var(--green)'}},
  ];
  let h=`<div class="section" id="leaderboards"><div class="grid grid-3">`;
  boards.forEach(b=>{{
    const sorted=[...playerNames].sort((a,c)=>(PLAYERS_DATA[c][b.key]||0)-(PLAYERS_DATA[a][b.key]||0));
    const maxVal=PLAYERS_DATA[sorted[0]][b.key]||1;
    h+=`<div class="card"><h3>${{t(b.tkey)}}</h3><ol class="leaderboard">`;
    sorted.forEach((name,i)=>{{
      const val=PLAYERS_DATA[name][b.key]||0;const w=pct(val,maxVal);const isRec=i===0&&val>0;
      h+=`<li><span class="rank">${{i+1}}</span>
        <span class="name"><span class="player-dot" style="background:${{PLAYER_COLORS_MAP[name]}}"></span>${{name}}${{isRec?'<span class="record-badge">RECORD</span>':''}}</span>
        <span class="bar-bg"><span class="bar-fill" style="width:${{w}}%;background:${{b.color}}"></span></span>
        <span class="val">${{typeof val==='number'&&val%1?val.toFixed(1):fmt(val)}}${{b.suffix}}</span></li>`;
    }});
    h+=`</ol></div>`;
  }});
  h+=`</div>
    <div class="grid grid-2" style="margin-top:1rem">
      <div class="card"><h3><span class="icon">${{mcIcon('skeleton_skull')}}</span> ${{t('chart_deathcauses')}}</h3><div class="chart-wrap"><canvas id="chart-deathcauses"></canvas></div></div>
      <div class="card"><h3><span class="icon">${{mcIcon('compass')}}</span> ${{t('chart_dist_type')}}</h3><div class="chart-wrap"><canvas id="chart-dist-stacked"></canvas></div></div>
    </div></div>`;
  return h;
}}

function renderLeaderboardCharts(){{
  destroyChart('chart-deathcauses');
  const da={{}};playerNames.forEach(n=>{{const kb=PLAYERS_DATA[n].killed_by||{{}};Object.entries(kb).forEach(([m,c])=>{{da[m]=(da[m]||0)+c}})}});
  const ds=Object.entries(da).sort((a,b)=>b[1]-a[1]);
  const dc=['#ef6a6a','#efaa6a','#efd96a','#3ecf8e','#6aafef','#7c6aef','#ef6ac0','#6aefd9','#a86aef','#8b8b96'];
  charts['chart-deathcauses']=new Chart(document.getElementById('chart-deathcauses'),{{type:'doughnut',data:{{
    labels:ds.map(d=>label(d[0])),datasets:[{{data:ds.map(d=>d[1]),backgroundColor:ds.map((_,i)=>dc[i%dc.length]+'cc'),borderColor:'#16161a',borderWidth:2}}]
  }},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:10}}}}}}}}}}}});

  destroyChart('chart-dist-stacked');
  const dt=['walk','sprint','fly','aviate','swim','boat','horse','climb','crouch','fall'];
  const dco=['#7c6aef','#3ecf8e','#6aafef','#efd96a','#6aefd9','#efaa6a','#ef6ac0','#a86aef','#8b8b96','#ef6a6a'];
  const fp=playerNames.filter(n=>PLAYERS_DATA[n].total_distance_km>5);
  charts['chart-dist-stacked']=new Chart(document.getElementById('chart-dist-stacked'),{{type:'bar',data:{{
    labels:fp,datasets:dt.map((t,i)=>({{label:label(t),data:fp.map(n=>PLAYERS_DATA[n].distances?.[t]||0),backgroundColor:dco[i]+'aa',borderWidth:0}}))
  }},options:{{responsive:true,maintainAspectRatio:false,
    scales:{{x:{{stacked:true,grid:{{display:false}}}},y:{{stacked:true,title:{{display:true,text:'km'}},grid:{{color:'rgba(42,42,53,0.3)'}}}}}},
    plugins:{{legend:{{position:'bottom',labels:{{font:{{size:9}}}}}}}}}}}});
}}

// ═══════════════════════════════════════
// BADGE / ACHIEVEMENT SYSTEM
// ═══════════════════════════════════════
const TIER_NAMES=['locked','bronze','silver','gold','diamond'];
function tierLabel(i){{return [t('tier_locked'),t('tier_bronze'),t('tier_silver'),t('tier_gold'),t('tier_diamond')][i]}}
const TIER_COLORS=['var(--text-muted)','#cd7f32','#c0c0c0','#ffd700','#b9f2ff'];
const TIER_EMOJIS=[mcIcon('copper_ingot'),mcIcon('iron_ingot'),mcIcon('gold_ingot'),mcIcon('diamond')];
const BADGE_CATEGORIES=[
  {{id:'mining'}},{{id:'combat'}},{{id:'survival'}},{{id:'exploration'}},
  {{id:'farming'}},{{id:'craft'}},{{id:'daily'}},{{id:'prestige'}},
];
const BADGES=[
  {{id:'mineur',name:'Mineur',icon:mcIcon('diamond_pickaxe'),cat:'mining',
   tiers:[1000,10000,50000,100000],val:p=>p.total_mined}},
  {{id:'diamantaire',name:'Diamantaire',icon:mcIcon('diamond'),cat:'mining',
   tiers:[10,50,150,300],val:p=>p.badge_data?.diamond_ore||0}},
  {{id:'nether_mole',name:'Nether Mole',icon:mcIcon('netherrack'),cat:'mining',
   tiers:[1000,10000,20000,50000],val:p=>p.badge_data?.netherrack||0}},
  {{id:'ancient_debris',name:'Débris Anciens',icon:mcIcon('ancient_debris'),cat:'mining',
   tiers:[5,20,50,100],val:p=>p.badge_data?.ancient_debris||0}},
  {{id:'bucheron',name:'Bûcheron',icon:mcIcon('diamond_axe'),cat:'mining',
   tiers:[100,500,2000,5000],val:p=>p.badge_data?.logs||0}},
  {{id:'chasseur',name:'Chasseur',icon:mcIcon('diamond_sword'),cat:'combat',
   tiers:[100,1000,10000,50000],val:p=>p.mob_kills}},
  {{id:'ender_slayer',name:'Ender Slayer',icon:mcIcon('ender_pearl'),cat:'combat',
   tiers:[100,1000,10000,40000],val:p=>p.badge_data?.enderman||0}},
  {{id:'nether_warrior',name:'Nether Warrior',icon:mcIcon('blaze_rod'),cat:'combat',
   tiers:[50,200,500,1000],val:p=>(p.badge_data?.wither_skeleton||0)+(p.badge_data?.blaze||0)}},
  {{id:'berserker',name:'Berserker',icon:mcIcon('netherite_sword'),cat:'combat',
   tiers:[1000,10000,50000,100000],val:p=>Math.round(p.damage_dealt/20)}},
  {{id:'pvp_champion',name:'PvP Champion',icon:mcIcon('iron_sword'),cat:'combat',
   tiers:[1,5,15,30],val:p=>p.player_kills}},
  {{id:'raid_master',name:'Raid Master',icon:mcIcon('crossbow'),cat:'combat',
   tiers:[10,50,100,200],val:p=>(p.badge_data?.pillager||0)+(p.badge_data?.vindicator||0)+(p.badge_data?.ravager||0)}},
  {{id:'increvable',name:'Increvable',icon:mcIcon('shield'),cat:'survival',
   tiers:[2,5,10,20],val:p=>p.deaths>0?Math.round(p.play_hours/p.deaths*10)/10:(p.play_hours>=1?999:0)}},
  {{id:'kamikaze',name:'Kamikaze',icon:mcIcon('skeleton_skull'),cat:'survival',
   tiers:[10,30,75,150],val:p=>p.deaths}},
  {{id:'bouclier_humain',name:'Bouclier Humain',icon:mcIcon('target'),cat:'survival',
   tiers:[5,15,30,50],val:p=>p.killed_by?.player||0}},
  {{id:'punching_bag',name:'Punching Bag',icon:mcIcon('iron_chestplate'),cat:'survival',
   tiers:[500,2000,5000,10000],val:p=>Math.round(p.damage_taken/20)}},
  {{id:'globe_trotter',name:'Globe-trotter',icon:mcIcon('compass'),cat:'exploration',
   tiers:[50,200,500,1500],val:p=>p.total_distance_km}},
  {{id:'marathonien',name:'Marathonien',icon:mcIcon('leather_boots'),cat:'exploration',
   tiers:[42,100,200,500],val:p=>p.distances?.walk||0}},
  {{id:'sprinter',name:'Sprinter',icon:mcIcon('feather'),cat:'exploration',
   tiers:[50,150,300,500],val:p=>p.distances?.sprint||0}},
  {{id:'aviateur',name:'Aviateur',icon:mcIcon('elytra'),cat:'exploration',
   tiers:[50,200,500,1000],val:p=>p.distances?.aviate||0}},
  {{id:'marin',name:'Marin',icon:mcIcon('oak_boat'),cat:'exploration',
   tiers:[1,5,10,20],val:p=>p.distances?.boat||0}},
  {{id:'cavalier',name:'Cavalier',icon:mcIcon('saddle'),cat:'exploration',
   tiers:[1,5,15,30],val:p=>p.distances?.horse||0}},
  {{id:'fermier',name:'Fermier',icon:mcIcon('wheat_seeds'),cat:'farming',
   tiers:[10,50,200,1000],val:p=>p.animals_bred}},
  {{id:'pecheur',name:'Pêcheur',icon:mcIcon('fishing_rod'),cat:'farming',
   tiers:[5,25,75,150],val:p=>p.fish_caught}},
  {{id:'commercant',name:'Commerçant',icon:mcIcon('emerald'),cat:'farming',
   tiers:[50,200,1000,3000],val:p=>p.traded_with_villager}},
  {{id:'recolte',name:'Récolte',icon:mcIcon('wheat'),cat:'farming',
   tiers:[100,500,2000,5000],val:p=>p.badge_data?.crops||0}},
  {{id:'artisan',name:'Artisan',icon:mcIcon('crafting_table'),cat:'craft',
   tiers:[1000,10000,30000,80000],val:p=>p.total_crafted}},
  {{id:'enchanteur',name:'Enchanteur',icon:mcIcon('enchanted_book'),cat:'craft',
   tiers:[10,50,200,500],val:p=>p.enchant_item}},
  {{id:'paperasse',name:'Paperasse',icon:mcIcon('paper'),cat:'craft',
   tiers:[100,1000,5000,15000],val:p=>p.badge_data?.paper||0}},
  {{id:'forgeron',name:'Forgeron',icon:mcIcon('anvil'),cat:'craft',
   tiers:[5,15,30,60],val:p=>p.badge_data?.total_broken||0}},
  {{id:'rat_de_coffre',name:'Rat de coffre',icon:mcIcon('chest'),cat:'daily',
   tiers:[100,1000,3000,5000],val:p=>p.open_chest}},
  {{id:'dormeur',name:'Dormeur',icon:mcIcon('white_bed'),cat:'daily',
   tiers:[10,50,150,300],val:p=>p.sleep_in_bed}},
  {{id:'kangourou',name:'Kangourou',icon:mcIcon('rabbit_foot'),cat:'daily',
   tiers:[5000,20000,50000,80000],val:p=>p.jumps}},
  {{id:'no_life',name:'No-Life',icon:mcIcon('clock'),cat:'prestige',
   tiers:[10,50,100,200],val:p=>p.play_hours}},
];
// Badge descriptions moved to T translations object

function getBadgeTier(value,tiers){{
  for(let i=tiers.length-1;i>=0;i--)if(value>=tiers[i])return i+1;
  return 0;
}}

function computePlayerBadges(p){{
  const results=[];
  BADGES.forEach(b=>{{
    const value=b.val(p);
    const tier=getBadgeTier(value,b.tiers);
    let progress,nextTarget;
    if(tier>=4){{progress=100;nextTarget=b.tiers[3]}}
    else{{
      nextTarget=b.tiers[tier];
      const prev=tier>0?b.tiers[tier-1]:0;
      progress=nextTarget>prev?Math.min(100,Math.max(0,Math.round((value-prev)/(nextTarget-prev)*100))):0;
    }}
    results.push({{id:b.id,name:b.name,icon:b.icon,cat:b.cat,tiers:b.tiers,value,tier,progress,nextTarget}});
  }});
  // All-Rounder: categories where all badges are Bronze+
  const catIds=['mining','combat','survival','exploration','farming','craft','daily'];
  let completeCats=0;
  catIds.forEach(cid=>{{
    const cb=results.filter(r=>r.cat===cid);
    if(cb.length&&cb.every(r=>r.tier>=1))completeCats++;
  }});
  const arT=[1,3,5,7],arTier=getBadgeTier(completeCats,arT);
  let arProg,arNext;
  if(arTier>=4){{arProg=100;arNext=arT[3]}}
  else{{arNext=arT[arTier];const arPrev=arTier>0?arT[arTier-1]:0;arProg=arNext>arPrev?Math.min(100,Math.round((completeCats-arPrev)/(arNext-arPrev)*100)):0}}
  results.push({{id:'all_rounder',name:'All-Rounder',icon:mcIcon('nether_star'),cat:'prestige',tiers:arT,value:completeCats,tier:arTier,progress:arProg,nextTarget:arNext}});
  // Légende: badges with Gold+
  const goldCount=results.filter(r=>r.tier>=3).length;
  const lgT=[3,5,10,15],lgTier=getBadgeTier(goldCount,lgT);
  let lgProg,lgNext;
  if(lgTier>=4){{lgProg=100;lgNext=lgT[3]}}
  else{{lgNext=lgT[lgTier];const lgPrev=lgTier>0?lgT[lgTier-1]:0;lgProg=lgNext>lgPrev?Math.min(100,Math.round((goldCount-lgPrev)/(lgNext-lgPrev)*100)):0}}
  results.push({{id:'legende',name:'Légende',icon:mcIcon('golden_apple'),cat:'prestige',tiers:lgT,value:goldCount,tier:lgTier,progress:lgProg,nextTarget:lgNext}});
  return results;
}}

function buildBadgesHtml(name){{
  const p=PLAYERS_DATA[name];
  const badges=computePlayerBadges(p);
  const unlocked=badges.filter(b=>b.tier>0).length;
  const total=badges.length;
  let h=`<div class="card"><h3><span class="icon">${{mcIcon('nether_star')}}</span> ${{t('badges_title')}}</h3>`;
  h+=`<div class="badges-counter-wrap"><span class="badges-counter"><b>${{unlocked}}</b> / ${{total}} ${{t('badges_unlocked')}}</span></div>`;
  BADGE_CATEGORIES.forEach(cat=>{{
    const cb=badges.filter(b=>b.cat===cat.id);
    if(!cb.length)return;
    h+=`<div class="badges-cat-header">${{t('cat_'+cat.id)}}</div><div class="badges-grid">`;
    cb.forEach(b=>{{
      const tn=TIER_NAMES[b.tier];
      const tl=b.tier>0?tierLabel(b.tier):t('tier_locked');
      const tc=b.tier>0?'tier-'+tn:'locked';
      const pc=TIER_COLORS[Math.max(b.tier,1)];
      const dv=b.id==='increvable'&&b.value>=999?'∞':(typeof b.value==='number'&&b.value%1!==0?b.value.toFixed(1):fmt(Math.round(b.value)));
      const nt=b.tier>=4?'MAX':fmt(b.nextTarget);
      const desc=t('bd_'+b.id);
      const ttTiers=b.tiers.map((th,i)=>{{const cls=i<b.tier?'tt-done':(i===b.tier&&b.tier<4?'tt-next':'');return `<span class="tt-tier ${{cls}}">${{TIER_EMOJIS[i]}} ${{fmt(th)}}</span>`}}).join(' · ');
      h+=`<div class="badge-card ${{tc}}">
        <div class="badge-tooltip"><div class="tt-desc">${{desc}}</div><div class="tt-tiers">${{ttTiers}}</div></div>
        <div class="badge-header">
          <span class="badge-icon">${{b.tier>0?b.icon:'🔒'}}</span>
          <span class="badge-name">${{t('b_'+b.id)}}</span>
          <span class="badge-tier badge-tier-${{tn}}">${{tl}}</span>
        </div>
        <div class="badge-progress-text"><span>${{dv}}</span><span>${{nt}}</span></div>
        <div class="badge-progress"><div class="badge-progress-fill" style="width:${{b.progress}}%;background:${{pc}}"></div></div>
      </div>`;
    }});
    h+=`</div>`;
  }});
  h+=`</div>`;
  return h;
}}

// ═══════════════════════════════════════
// PLAYER SECTION
// ═══════════════════════════════════════
function buildPlayerSection(name){{
  const p=PLAYERS_DATA[name];const color=PLAYER_COLORS_MAP[name];
  const avatarUrl=`https://mc-heads.net/avatar/${{p.uuid}}/64`;

  const records=[];
  ['play_hours','total_mined','mob_kills','total_distance_km','total_crafted','player_kills','enchant_item','fish_caught','traded_with_villager','animals_bred','jumps'].forEach(key=>{{
    const mx=Math.max(...playerNames.map(n=>PLAYERS_DATA[n][key]||0));
    if((p[key]||0)===mx&&mx>0)records.push(key);
  }});
  const recBadges=records.length?`<div style="margin-top:.5rem;display:flex;gap:.3rem;flex-wrap:wrap">${{records.map(r=>`<span class="record-badge">${{label(r).substring(0,20)}}</span>`).join('')}}</div>`:'';

  const killedBy=Object.entries(p.killed_by||{{}}).sort((a,b)=>b[1]-a[1]);
  const kbHtml=killedBy.length?killedBy.map(([m,c])=>`<li><span style="color:var(--text)">${{label(m)}}</span> <span style="color:var(--red);font-weight:600">${{c}}×</span></li>`).join(''):'<li style="color:var(--text-muted)">'+t('no_death')+'</li>';

  const mkList=(entries,color)=>{{
    if(!entries.length)return '<li style="color:var(--text-muted)">—</li>';
    const mx=entries[0]?.[1]||1;
    return entries.map(([k,v])=>{{const w=pct(v,mx);return `<li><span class="name">${{label(k)}}</span><span class="bar-bg"><span class="bar-fill" style="width:${{w}}%;background:${{color}}"></span></span><span class="val">${{fmt(v)}}</span></li>`}}).join('');
  }};

  const kd=p.deaths>0?(p.mob_kills/p.deaths).toFixed(1):'∞';
  const mph=p.play_hours>0?Math.round(p.total_mined/p.play_hours):0;
  const kph=p.play_hours>0?Math.round(p.mob_kills/p.play_hours):0;
  const pvpDeaths=(p.killed_by&&p.killed_by.player)||0;
  const pveDeaths=p.deaths-pvpDeaths;
  const arch=getArchetype(p);
  const funFacts=getFunFacts(name,p);
  const funFactsHtml=funFacts.length?funFacts.map(f=>`<div class="fun-fact">${{f.icon}}<span>${{f.text}}</span></div>`).join(''):'<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:.8rem">'+t('no_data')+'</div>';

  return `
  <div class="section" id="player-${{name}}">
    <div class="profile-header" style="border-left:4px solid ${{color}}">
      <img class="profile-avatar" src="${{avatarUrl}}" alt="${{name}}" onerror="this.style.display='none'">
      <div class="profile-info">
        <h2 style="color:${{color}}">${{name}}</h2>
        <div class="uuid">${{p.uuid}}</div>
        <div class="archetype" style="color:${{arch.color}};border-color:${{arch.color}}">${{arch.icon}} ${{arch.name}}</div>
        ${{recBadges}}
      </div>
      <div class="profile-stats">
        <div class="profile-stat"><div class="pv">${{p.play_hours}}h</div><div class="pl">${{t('playtime')}}</div></div>
        <div class="profile-stat"><div class="pv" style="color:var(--red)">${{kd}}</div><div class="pl">${{t('kd_ratio')}}</div></div>
        <div class="profile-stat"><div class="pv" style="color:var(--green)">${{fmt(p.total_distance_km)}} km</div><div class="pl">${{t('traveled')}}</div></div>
      </div>
    </div>
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--green)" data-target="${{p.total_mined}}">0</div><div class="label">${{t('blocks_mined')}}</div><div class="sub">${{fmt(mph)}}${{t('per_hour')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--red)" data-target="${{p.mob_kills}}">0</div><div class="label">${{t('mobs_killed')}}</div><div class="sub">${{fmt(kph)}}${{t('per_hour')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--orange)" data-target="${{p.deaths}}">0</div><div class="label">${{t('deaths')}}</div><div class="sub">${{mcIcon('iron_sword')}} ${{pvpDeaths}} ${{t('pvp')}} · ${{mcIcon('rotten_flesh')}} ${{pveDeaths}} ${{t('pve')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--cyan)" data-target="${{p.total_crafted}}">0</div><div class="label">${{t('items_crafted')}}</div></div>
    </div>
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--yellow)" data-target="${{p.enchant_item}}">0</div><div class="label">${{t('enchantments')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--blue)" data-target="${{p.open_chest}}">0</div><div class="label">${{t('chests_opened')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--teal)" data-target="${{p.fish_caught}}">0</div><div class="label">${{t('fish_caught')}}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--pink)" data-target="${{p.traded_with_villager}}">0</div><div class="label">${{t('npc_trades')}}</div></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${{mcIcon('clock')}}</span> ${{t('card_time_est')}}</h3><div class="chart-wrap"><canvas id="chart-time-${{name}}"></canvas></div></div>
      <div class="card"><h3><span class="icon">${{mcIcon('leather_boots')}}</span> ${{t('card_distances')}}</h3><div class="chart-wrap"><canvas id="chart-dist-${{name}}"></canvas></div></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${{mcIcon('skeleton_skull')}}</span> ${{t('card_killed_by')}}</h3><ul class="leaderboard" style="font-size:.8rem">${{kbHtml}}</ul></div>
    </div>
    <div class="card desktop-only">
      <h3><span class="icon">${{mcIcon('diamond_pickaxe')}}</span> ${{t('card_treemap')}}</h3>
      ${{buildTreemapHtml(Object.entries(p.mined_top15||{{}}))}}
    </div>
    <div class="card mobile-only">
      <h3><span class="icon">${{mcIcon('diamond_pickaxe')}}</span> ${{t('card_top15_mined')}}</h3>
      <ol class="leaderboard">${{mkList(Object.entries(p.mined_top15||{{}}),color)}}</ol>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${{mcIcon('diamond_sword')}}</span> ${{t('card_top10_killed')}}</h3><ol class="leaderboard">${{mkList(Object.entries(p.killed_top10||{{}}),'var(--red)')}}</ol></div>
      <div class="card"><h3><span class="icon">${{mcIcon('crafting_table')}}</span> ${{t('card_top10_crafted')}}</h3><ol class="leaderboard">${{mkList(Object.entries(p.crafted_top15||{{}}).slice(0,10),'var(--cyan)')}}</ol></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${{mcIcon('anvil')}}</span> ${{t('card_tools_broken')}}</h3>${{buildBrokenHtml(p.broken)}}</div>
      <div class="card"><h3><span class="icon">${{mcIcon('torch')}}</span> ${{t('card_fun_facts')}}</h3><div class="fun-facts">${{funFactsHtml}}</div></div>
    </div>
    ${{buildBadgesHtml(name)}}
  </div>`;
}}

function renderPlayerCharts(name){{
  const p=PLAYERS_DATA[name];

  // Time estimation donut
  const timeId=`chart-time-${{name}}`;
  destroyChart(timeId);
  const timeData=estimateTime(p);
  if(timeData&&document.getElementById(timeId)){{
    charts[timeId]=new Chart(document.getElementById(timeId),{{type:'doughnut',data:{{
      labels:timeData.map(d=>d.label),
      datasets:[{{data:timeData.map(d=>d.hours),backgroundColor:timeData.map(d=>d.color+'cc'),borderColor:'#16161a',borderWidth:2}}]
    }},options:{{responsive:true,maintainAspectRatio:false,cutout:'60%',
      plugins:{{legend:{{position:'bottom',labels:{{font:{{size:10}},padding:8}}}},
        tooltip:{{callbacks:{{label:ctx=>{{const d=timeData[ctx.dataIndex];const total=timeData.reduce((s,x)=>s+x.hours,0);return ` ${{d.hours}}h (${{(d.hours/total*100).toFixed(0)}}%)`}}}}}}}}}}}});
  }}

  // Distance bar
  const distId=`chart-dist-${{name}}`;
  destroyChart(distId);
  const dists=p.distances||{{}};
  const de=Object.entries(dists).filter(([_,v])=>v>0).sort((a,b)=>b[1]-a[1]);
  if(de.length&&document.getElementById(distId)){{
    const dp=['#7c6aef','#3ecf8e','#6aafef','#efd96a','#6aefd9','#efaa6a','#ef6ac0','#a86aef','#ef6a6a','#8b8b96','#5c5c68','#3a3a48','#222230'];
    charts[distId]=new Chart(document.getElementById(distId),{{type:'bar',data:{{
      labels:de.map(d=>label(d[0])),datasets:[{{data:de.map(d=>d[1]),
        backgroundColor:de.map((_,i)=>dp[i%dp.length]+'cc'),borderColor:de.map((_,i)=>dp[i%dp.length]),borderWidth:1,borderRadius:4}}]
    }},options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.parsed.x.toFixed(2)+' km'}}}}}},
      scales:{{x:{{title:{{display:true,text:'km'}},grid:{{color:'rgba(42,42,53,0.3)'}}}},y:{{grid:{{display:false}}}}}}}}}});
  }}
}}

// ═══════════════════════════════════════
// LANGUAGE SWITCH
// ═══════════════════════════════════════
function switchLang(newLang){{
  lang=newLang;
  localStorage.setItem('mc-dash-lang',lang);
  document.getElementById('html-root').lang=lang;
  document.getElementById('subtitle').textContent=t('subtitle');
  document.getElementById('syncDate').textContent=t('sync_prefix')+' : '+(lang==='fr'?SYNC_FR:SYNC_EN);
  document.getElementById('langToggle').textContent=lang==='fr'?'🇬🇧 EN':'🇫🇷 FR';
  updateGlobalMeta();
  buildNav();
  buildAllSections();
  showSection(currentSection);
}}

// ═══════════════════════════════════════
// INIT
// ═══════════════════════════════════════
document.getElementById('html-root').lang=lang;
document.getElementById('subtitle').textContent=t('subtitle');
document.getElementById('syncDate').textContent=t('sync_prefix')+' : '+(lang==='fr'?SYNC_FR:SYNC_EN);
document.getElementById('langToggle').textContent=lang==='fr'?'🇬🇧 EN':'🇫🇷 FR';
document.getElementById('langToggle').addEventListener('click',function(){{switchLang(lang==='fr'?'en':'fr')}});
buildNav();buildAllSections();renderOverviewCharts();animateCounters();
</script>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════
# 4. MAIN
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Génère un dashboard HTML à partir des fichiers de stats Minecraft."
    )
    parser.add_argument(
        "data_dir",
        help="Chemin vers le dossier contenant les fichiers JSON de stats (ex: stats/serveur-2026/data)"
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Titre du serveur affiché dans le dashboard (défaut: nom du dossier parent)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Chemin du fichier HTML de sortie (défaut: <dossier_parent>/index.html)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"[ERR] Le dossier {data_dir} n'existe pas.")
        sys.exit(1)

    # Titre : argument ou nom du dossier parent formaté
    if args.title:
        title = args.title
    else:
        parent_name = data_dir.parent.name
        title = parent_name.replace("-", " ").replace("_", " ").title()

    # Fichier de sortie
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = data_dir.parent / "index.html"

    # Cache des UUIDs (persiste entre les exécutions)
    cache_path = data_dir.parent / ".uuid_cache.json"

    print(f"[MC] Generation du dashboard : {title}")
    print(f"[IN] Dossier data : {data_dir}")
    print(f"[OUT] Sortie : {output_path}")
    print()

    # Trouver les fichiers JSON
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print("[ERR] Aucun fichier JSON trouve dans le dossier.")
        sys.exit(1)

    print(f"[DATA] {len(json_files)} fichier(s) de stats trouve(s)")

    # Extraire les UUIDs
    uuids = [f.stem for f in json_files]

    # Résoudre les pseudos
    print("\n[UUID] Resolution des pseudos Mojang...")
    uuid_to_name = resolve_all_uuids(uuids, cache_path)

    # Traiter les stats
    print("\n[STATS] Traitement des statistiques...")
    players_data = {}
    for json_file in json_files:
        uuid = json_file.stem
        name = uuid_to_name[uuid]
        player = process_player(uuid, name, str(json_file))
        players_data[name] = player
        print(f"  + {name}: {player['play_hours']}h, {player['total_mined']} blocs, {player['mob_kills']} kills")

    # Générer le HTML
    print(f"\n[HTML] Generation du HTML...")
    html = generate_html(players_data, title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Dashboard genere : {output_path} ({len(html):,} octets)")
    print(f"   {len(players_data)} joueurs - {sum(p['play_hours'] for p in players_data.values()):.0f}h de jeu total")


if __name__ == "__main__":
    main()
