"""
badges.py - Dashboard badge definitions and computation.

Each badge = id + name + icon + category + thresholds (bronze/silver/gold/diamond)
           + a `val(player)` function that reads the normalized player dict.

`compute_player_badges(player)` returns the final list (all badges +
the two meta badges `all_rounder` and `legende`), ready to be serialized
into the JSON injected on the client side.

Note: badge `name` values are in French on purpose - they are user-facing
UI labels rendered in the dashboard.
"""

from __future__ import annotations


def _get(player: dict, key: str, default=0):
    return player.get(key, default) or default


def _bd(player: dict, key: str) -> int:
    return (player.get("badge_data") or {}).get(key, 0) or 0


def _dist(player: dict, key: str) -> float:
    return (player.get("distances") or {}).get(key, 0) or 0


def _increvable(player: dict):
    hours = _get(player, "play_hours")
    if hours < 1:
        return None
    deaths = _get(player, "deaths")
    if deaths == 0:
        return 999
    return round(hours / deaths, 1)


BADGES: list[dict] = [
    {"id": "mineur", "name": "Mineur", "icon": "diamond_pickaxe", "cat": "mining",
     "tiers": [1000, 10000, 50000, 100000], "val": lambda p: _get(p, "total_mined")},
    {"id": "diamantaire", "name": "Diamantaire", "icon": "diamond", "cat": "mining",
     "tiers": [10, 50, 150, 300], "val": lambda p: _bd(p, "diamond_ore")},
    {"id": "nether_mole", "name": "Nether Mole", "icon": "netherrack", "cat": "mining",
     "tiers": [1000, 10000, 20000, 50000], "val": lambda p: _bd(p, "netherrack")},
    {"id": "ancient_debris", "name": "Débris Anciens", "icon": "ancient_debris", "cat": "mining",
     "tiers": [5, 20, 50, 100], "val": lambda p: _bd(p, "ancient_debris")},
    {"id": "bucheron", "name": "Bûcheron", "icon": "diamond_axe", "cat": "mining",
     "tiers": [100, 500, 2000, 5000], "val": lambda p: _bd(p, "logs")},
    {"id": "chasseur", "name": "Chasseur", "icon": "diamond_sword", "cat": "combat",
     "tiers": [100, 1000, 10000, 50000], "val": lambda p: _get(p, "mob_kills")},
    {"id": "ender_slayer", "name": "Ender Slayer", "icon": "ender_pearl", "cat": "combat",
     "tiers": [100, 1000, 10000, 40000], "val": lambda p: _bd(p, "enderman")},
    {"id": "nether_warrior", "name": "Nether Warrior", "icon": "blaze_rod", "cat": "combat",
     "tiers": [50, 200, 500, 1000], "val": lambda p: _bd(p, "wither_skeleton") + _bd(p, "blaze")},
    {"id": "berserker", "name": "Berserker", "icon": "netherite_sword", "cat": "combat",
     "tiers": [1000, 10000, 50000, 100000], "val": lambda p: round(_get(p, "damage_dealt") / 20)},
    {"id": "pvp_champion", "name": "PvP Champion", "icon": "iron_sword", "cat": "combat",
     "tiers": [1, 5, 15, 30], "val": lambda p: _get(p, "player_kills")},
    {"id": "raid_master", "name": "Raid Master", "icon": "crossbow", "cat": "combat",
     "tiers": [10, 50, 100, 200], "val": lambda p: _bd(p, "pillager") + _bd(p, "vindicator") + _bd(p, "ravager")},
    {"id": "increvable", "name": "Increvable", "icon": "totem_of_undying", "cat": "survival",
     "tiers": [2, 5, 10, 20], "val": _increvable},
    {"id": "kamikaze", "name": "Kamikaze", "icon": "skeleton_skull", "cat": "survival",
     "tiers": [10, 30, 75, 150], "val": lambda p: _get(p, "deaths")},
    {"id": "bouclier_humain", "name": "Bouclier Humain", "icon": "target", "cat": "survival",
     "tiers": [5, 15, 30, 50], "val": lambda p: (p.get("killed_by") or {}).get("player", 0)},
    {"id": "punching_bag", "name": "Punching Bag", "icon": "iron_chestplate", "cat": "survival",
     "tiers": [500, 2000, 5000, 10000], "val": lambda p: round(_get(p, "damage_taken") / 20)},
    {"id": "globe_trotter", "name": "Globe-trotter", "icon": "compass", "cat": "exploration",
     "tiers": [50, 200, 500, 1500], "val": lambda p: _get(p, "total_distance_km")},
    {"id": "marathonien", "name": "Marathonien", "icon": "diamond_boots", "cat": "exploration",
     "tiers": [42, 100, 200, 500], "val": lambda p: _dist(p, "walk")},
    {"id": "sprinter", "name": "Sprinter", "icon": "feather", "cat": "exploration",
     "tiers": [50, 150, 300, 500], "val": lambda p: _dist(p, "sprint")},
    {"id": "aviateur", "name": "Aviateur", "icon": "elytra", "cat": "exploration",
     "tiers": [50, 200, 500, 1000], "val": lambda p: _dist(p, "aviate")},
    {"id": "marin", "name": "Marin", "icon": "oak_boat", "cat": "exploration",
     "tiers": [1, 5, 10, 20], "val": lambda p: _dist(p, "boat")},
    {"id": "cavalier", "name": "Cavalier", "icon": "saddle", "cat": "exploration",
     "tiers": [1, 5, 15, 30], "val": lambda p: _dist(p, "horse")},
    {"id": "fermier", "name": "Fermier", "icon": "wheat_seeds", "cat": "farming",
     "tiers": [10, 50, 200, 1000], "val": lambda p: _get(p, "animals_bred")},
    {"id": "pecheur", "name": "Pêcheur", "icon": "fishing_rod", "cat": "farming",
     "tiers": [5, 25, 75, 150], "val": lambda p: _get(p, "fish_caught")},
    {"id": "commercant", "name": "Commerçant", "icon": "emerald", "cat": "farming",
     "tiers": [50, 200, 1000, 3000], "val": lambda p: _get(p, "traded_with_villager")},
    {"id": "recolte", "name": "Récolte", "icon": "wheat", "cat": "farming",
     "tiers": [100, 500, 2000, 5000], "val": lambda p: _bd(p, "crops")},
    {"id": "artisan", "name": "Artisan", "icon": "crafting_table", "cat": "craft",
     "tiers": [1000, 10000, 30000, 80000], "val": lambda p: _get(p, "total_crafted")},
    {"id": "enchanteur", "name": "Enchanteur", "icon": "enchanted_book", "cat": "craft",
     "tiers": [10, 50, 200, 500], "val": lambda p: _get(p, "enchant_item")},
    {"id": "paperasse", "name": "Paperasse", "icon": "paper", "cat": "craft",
     "tiers": [100, 1000, 5000, 15000], "val": lambda p: _bd(p, "paper")},
    {"id": "forgeron", "name": "Forgeron", "icon": "anvil", "cat": "craft",
     "tiers": [5, 15, 30, 60], "val": lambda p: _bd(p, "total_broken")},
    {"id": "rat_de_coffre", "name": "Rat de coffre", "icon": "chest", "cat": "daily",
     "tiers": [100, 1000, 3000, 5000], "val": lambda p: _get(p, "open_chest")},
    {"id": "dormeur", "name": "Dormeur", "icon": "white_bed", "cat": "daily",
     "tiers": [10, 50, 150, 300], "val": lambda p: _get(p, "sleep_in_bed")},
    {"id": "kangourou", "name": "Kangourou", "icon": "rabbit_foot", "cat": "daily",
     "tiers": [5000, 20000, 50000, 80000], "val": lambda p: _get(p, "jumps")},
    {"id": "no_life", "name": "No-Life", "icon": "recovery_compass", "cat": "prestige",
     "tiers": [10, 50, 100, 200], "val": lambda p: _get(p, "play_hours")},
]

META_CATEGORIES = ["mining", "combat", "survival", "exploration", "farming", "craft", "daily"]


def get_tier(value, tiers: list) -> int:
    """Return 0 (locked) to 4 (diamond) based on value and the 4 thresholds."""
    for i in range(len(tiers) - 1, -1, -1):
        if value >= tiers[i]:
            return i + 1
    return 0


def _compute_progress(value, tier: int, tiers: list) -> tuple[int, float]:
    """Return (progress%, nextTarget) based on the current value."""
    if tier >= 4:
        return 100, tiers[3]
    next_target = tiers[tier]
    prev = tiers[tier - 1] if tier > 0 else 0
    if next_target <= prev:
        return 0, next_target
    pct = round((value - prev) / (next_target - prev) * 100)
    return max(0, min(100, pct)), next_target


def _badge_entry(defn: dict, player: dict) -> dict:
    value = defn["val"](player)
    if value is None:
        tier, progress, next_target = 0, 0, defn["tiers"][0]
    else:
        tier = get_tier(value, defn["tiers"])
        progress, next_target = _compute_progress(value, tier, defn["tiers"])
    return {
        "id": defn["id"],
        "name": defn["name"],
        "icon": defn["icon"],
        "cat": defn["cat"],
        "tiers": defn["tiers"],
        "value": value,
        "tier": tier,
        "progress": progress,
        "nextTarget": next_target,
    }


def compute_player_badges(player: dict) -> list[dict]:
    """Compute all badges (standard + meta) for a player."""
    results = [_badge_entry(b, player) for b in BADGES]

    # All-Rounder: categories where every badge has tier >= bronze
    complete_cats = 0
    for cid in META_CATEGORIES:
        cat_badges = [r for r in results if r["cat"] == cid]
        if cat_badges and all(r["tier"] >= 1 for r in cat_badges):
            complete_cats += 1
    ar_tiers = [1, 3, 5, 7]
    ar_tier = get_tier(complete_cats, ar_tiers)
    ar_prog, ar_next = _compute_progress(complete_cats, ar_tier, ar_tiers)
    results.append({
        "id": "all_rounder", "name": "All-Rounder", "icon": "nether_star",
        "cat": "prestige", "tiers": ar_tiers, "value": complete_cats,
        "tier": ar_tier, "progress": ar_prog, "nextTarget": ar_next,
    })

    # Légende: number of badges at tier >= gold
    gold_count = sum(1 for r in results if r["tier"] >= 3)
    lg_tiers = [3, 5, 10, 15]
    lg_tier = get_tier(gold_count, lg_tiers)
    lg_prog, lg_next = _compute_progress(gold_count, lg_tier, lg_tiers)
    results.append({
        "id": "legende", "name": "Légende", "icon": "golden_apple",
        "cat": "prestige", "tiers": lg_tiers, "value": gold_count,
        "tier": lg_tier, "progress": lg_prog, "nextTarget": lg_next,
    })

    return results
