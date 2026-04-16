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

from minecraft.badges import compute_player_badges


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
</script>
<script src="../assets/app.js"></script>
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
