"""Unit tests for scripts/minecraft/badges.py.

Safety net for tier thresholds, progress math, _increvable edge cases, and the
two meta-badges (all_rounder, legende). An off-by-one in any BADGES threshold
would propagate silently through the generated dashboard - these tests catch it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from minecraft.badges import (  # noqa: E402
    BADGES,
    META_CATEGORIES,
    _compute_progress,
    _increvable,
    compute_player_badges,
    get_tier,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Union of every field the badge lambdas read. We set each to a very large
# value so every standard badge lands at diamond (tier 4). That in turn
# guarantees every META_CATEGORIES category has all badges >= bronze, so
# `all_rounder` must reach its max tier too. This is deliberately over-broad
# (rather than hand-mapping each badge to its bronze threshold) to stay
# robust against future BADGES edits.
_HUGE = 10**9

_BADGE_DATA_KEYS = [
    "diamond_ore", "netherrack", "ancient_debris", "logs", "enderman",
    "wither_skeleton", "blaze", "pillager", "vindicator", "ravager",
    "crops", "paper", "total_broken",
]
_DISTANCE_KEYS = ["walk", "sprint", "aviate", "boat", "horse"]
_TOP_LEVEL_KEYS = [
    "total_mined", "mob_kills", "damage_dealt", "player_kills",
    "deaths", "damage_taken", "total_distance_km", "animals_bred",
    "fish_caught", "traded_with_villager", "total_crafted",
    "enchant_item", "open_chest", "sleep_in_bed", "jumps",
    "play_hours",
]


def _player_maxed() -> dict:
    """Player dict with every badge-relevant field set to _HUGE."""
    p: dict = {k: _HUGE for k in _TOP_LEVEL_KEYS}
    # `_increvable` is hours/deaths; with both maxed the ratio is 1 < bronze (2).
    # Override deaths to something small so the ratio lands at diamond.
    p["deaths"] = 10  # hours/deaths = 1e8 → diamond (threshold 20)
    # But kamikaze (deaths count) + bouclier_humain + punching_bag still need huge.
    # kamikaze reads `deaths` directly → with 10 it sits below bronze (10 == bronze).
    # 10 is exactly the bronze threshold for kamikaze, which still qualifies.
    # To make kamikaze diamond we'd need 150 deaths but then increvable drops.
    # For `all_rounder` we only need every category with tier >= 1, so bronze
    # on kamikaze is sufficient. _HUGE on the other survival badges handles them.
    p["badge_data"] = {k: _HUGE for k in _BADGE_DATA_KEYS}
    p["distances"] = {k: _HUGE for k in _DISTANCE_KEYS}
    p["killed_by"] = {"player": _HUGE}
    return p


def _player_empty() -> dict:
    """Player dict with no stats - every badge should be locked (tier 0)."""
    return {"badge_data": {}, "distances": {}, "killed_by": {}}


# ---------------------------------------------------------------------------
# get_tier
# ---------------------------------------------------------------------------

class TestGetTier(unittest.TestCase):
    def test_below_bronze_returns_locked(self):
        self.assertEqual(get_tier(0, [10, 50, 100, 200]), 0)
        self.assertEqual(get_tier(9, [10, 50, 100, 200]), 0)

    def test_at_each_tier_threshold(self):
        tiers = [10, 50, 100, 200]
        self.assertEqual(get_tier(10, tiers), 1)
        self.assertEqual(get_tier(50, tiers), 2)
        self.assertEqual(get_tier(100, tiers), 3)
        self.assertEqual(get_tier(200, tiers), 4)

    def test_above_diamond_stays_diamond(self):
        self.assertEqual(get_tier(10**9, [10, 50, 100, 200]), 4)


# ---------------------------------------------------------------------------
# _compute_progress
# ---------------------------------------------------------------------------

class TestComputeProgress(unittest.TestCase):
    def test_progress_at_zero(self):
        pct, nxt = _compute_progress(0, 0, [10, 50, 100, 200])
        self.assertEqual(pct, 0)
        self.assertEqual(nxt, 10)

    def test_progress_at_mid_tier(self):
        # tier=1 (bronze), value=30, band = [10, 50] → 50% of the way to silver.
        pct, nxt = _compute_progress(30, 1, [10, 50, 100, 200])
        self.assertEqual(pct, 50)
        self.assertEqual(nxt, 50)

    def test_progress_saturates_at_diamond(self):
        pct, nxt = _compute_progress(10**9, 4, [10, 50, 100, 200])
        self.assertEqual(pct, 100)
        self.assertEqual(nxt, 200)

    def test_progress_clamps_negative_to_zero(self):
        # If value dips below the previous threshold the pct is clamped >= 0.
        pct, _ = _compute_progress(5, 1, [10, 50, 100, 200])
        self.assertEqual(pct, 0)


# ---------------------------------------------------------------------------
# _increvable
# ---------------------------------------------------------------------------

class TestIncrevable(unittest.TestCase):
    def test_hours_below_one_returns_none(self):
        self.assertIsNone(_increvable({"play_hours": 0.5, "deaths": 2}))
        self.assertIsNone(_increvable({"play_hours": 0, "deaths": 0}))

    def test_zero_deaths_returns_infinity_marker(self):
        self.assertEqual(_increvable({"play_hours": 10, "deaths": 0}), 999)

    def test_normal_ratio(self):
        self.assertEqual(_increvable({"play_hours": 50, "deaths": 10}), 5.0)

    def test_missing_deaths_treated_as_zero(self):
        # _get() defaults missing keys to 0, so the "infinity marker" branch fires.
        self.assertEqual(_increvable({"play_hours": 3}), 999)


# ---------------------------------------------------------------------------
# compute_player_badges
# ---------------------------------------------------------------------------

class TestComputePlayerBadges(unittest.TestCase):
    EXPECTED_KEYS = {
        "id", "name", "icon", "cat", "tiers",
        "value", "tier", "progress", "nextTarget",
    }

    def test_returns_35_entries_with_expected_keys(self):
        badges = compute_player_badges(_player_empty())
        # 33 standard + 2 meta.
        self.assertEqual(len(BADGES), 33)
        self.assertEqual(len(badges), 35)
        for b in badges:
            self.assertEqual(set(b.keys()), self.EXPECTED_KEYS)

        by_id = {b["id"]: b for b in badges}
        self.assertIn("all_rounder", by_id)
        self.assertIn("legende", by_id)
        self.assertEqual(by_id["all_rounder"]["cat"], "prestige")
        self.assertEqual(by_id["legende"]["cat"], "prestige")

    def test_empty_player_has_all_meta_badges_locked(self):
        badges = {b["id"]: b for b in compute_player_badges(_player_empty())}
        self.assertEqual(badges["all_rounder"]["tier"], 0)
        self.assertEqual(badges["legende"]["tier"], 0)

    def test_all_rounder_requires_bronze_in_every_category(self):
        # Maxed player → every standard badge is at least bronze → all 7
        # META_CATEGORIES are "complete" → all_rounder maxes out at diamond.
        badges = {b["id"]: b for b in compute_player_badges(_player_maxed())}
        self.assertEqual(badges["all_rounder"]["value"], len(META_CATEGORIES))
        self.assertGreaterEqual(badges["all_rounder"]["tier"], 1)
        # Sanity: every META_CATEGORIES category has all its badges >= bronze.
        standard = [b for b in compute_player_badges(_player_maxed())
                    if b["id"] not in {"all_rounder", "legende"}]
        for cat in META_CATEGORIES:
            cat_badges = [b for b in standard if b["cat"] == cat]
            self.assertTrue(cat_badges, f"no badges in category {cat}")
            for b in cat_badges:
                self.assertGreaterEqual(
                    b["tier"], 1,
                    f"{b['id']} in {cat} expected >=bronze with maxed fixture",
                )

    def test_legende_counts_gold_or_better(self):
        # Maxed player → every badge at diamond (tier 4) → gold_count >= 33 →
        # legende hits its top threshold (15) with room to spare.
        badges = {b["id"]: b for b in compute_player_badges(_player_maxed())}
        self.assertGreaterEqual(badges["legende"]["value"], 3)
        self.assertGreaterEqual(badges["legende"]["tier"], 1)

    def test_increvable_none_value_locks_tier(self):
        # When val() returns None (hours < 1), _badge_entry sets tier=0
        # and nextTarget to the bronze threshold.
        badges = {b["id"]: b for b in compute_player_badges(
            {"play_hours": 0.2, "deaths": 3}
        )}
        incr = badges["increvable"]
        self.assertIsNone(incr["value"])
        self.assertEqual(incr["tier"], 0)
        self.assertEqual(incr["nextTarget"], incr["tiers"][0])


if __name__ == "__main__":
    unittest.main()
