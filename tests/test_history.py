"""Unit tests for scripts/minecraft/history.py.

Black-box tests - we don't touch history.py, only exercise its public API
through temporary snapshot directories built on the fly.

Run with:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Make `scripts/` importable without requiring a package __init__.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from minecraft.history import (  # noqa: E402
    DELTA_KEYS,
    compute_daily_play_hours,
    compute_deltas,
    find_baseline_snapshot,
    load_baseline_metrics,
)


TICKS_PER_HOUR = 72_000


def _make_snapshot(root: Path, iso_date: str, players: dict[str, dict]) -> Path:
    """Create ``root/<iso_date>/<uuid>.json`` for each player.

    ``players`` is ``{uuid: {"play_hours": float, "mined": {name: n}, "mob_kills": n,
    "crafted": {name: n}}}``. Any field may be omitted - defaults apply.
    """
    snap_dir = root / iso_date
    snap_dir.mkdir(parents=True, exist_ok=True)
    for uuid, p in players.items():
        play_hours = p.get("play_hours", 0.0)
        mined = p.get("mined", {})
        crafted = p.get("crafted", {})
        mob_kills = p.get("mob_kills", 0)
        payload = {
            "stats": {
                "minecraft:custom": {
                    "minecraft:play_time": int(round(play_hours * TICKS_PER_HOUR)),
                    "minecraft:mob_kills": mob_kills,
                },
                "minecraft:mined": {f"minecraft:{k}": v for k, v in mined.items()},
                "minecraft:crafted": {f"minecraft:{k}": v for k, v in crafted.items()},
            }
        }
        (snap_dir / f"{uuid}.json").write_text(json.dumps(payload))
    return snap_dir


class TestFindBaselineSnapshot(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.today = date(2026, 4, 19)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _mk(self, age_days: int) -> str:
        iso = (self.today - timedelta(days=age_days)).isoformat()
        _make_snapshot(self.root, iso, {})
        return iso

    def test_empty_snapshots_dir_returns_none(self) -> None:
        # root exists but contains no dated subdirs
        self.assertIsNone(find_baseline_snapshot(self.root, today=self.today))

    def test_missing_snapshots_dir_returns_none(self) -> None:
        missing = self.root / "does-not-exist"
        self.assertIsNone(find_baseline_snapshot(missing, today=self.today))

    def test_all_snapshots_too_recent_returns_none(self) -> None:
        for age in (1, 3, 5):  # all below default min_days=6
            self._mk(age)
        self.assertIsNone(find_baseline_snapshot(self.root, today=self.today))

    def test_all_snapshots_too_old_returns_none(self) -> None:
        for age in (40, 60):  # all above default max_days=30
            self._mk(age)
        self.assertIsNone(find_baseline_snapshot(self.root, today=self.today))

    def test_picks_closest_to_target_days(self) -> None:
        # Unambiguous case: ages 6, 10, 14 with target=7 → age-6 wins (|6-7|=1 < |10-7|=3)
        iso6 = self._mk(6)
        self._mk(10)
        self._mk(14)
        result = find_baseline_snapshot(self.root, today=self.today)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, iso6)

    def test_ignores_non_date_directories(self) -> None:
        # A stray directory whose name isn't an ISO date shouldn't crash/be picked.
        (self.root / "not-a-date").mkdir()
        iso = self._mk(7)
        result = find_baseline_snapshot(self.root, today=self.today)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, iso)


class TestLoadBaselineMetrics(unittest.TestCase):
    def test_reads_all_valid_files_and_skips_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snap = _make_snapshot(
                root,
                "2026-04-12",
                {
                    "uuid-a": {
                        "play_hours": 10.0,
                        "mined": {"stone": 100, "dirt": 50},
                        "mob_kills": 7,
                        "crafted": {"oak_planks": 20},
                    }
                },
            )
            # Add a malformed JSON file - should be silently skipped.
            (snap / "uuid-broken.json").write_text("{not valid json")
            metrics = load_baseline_metrics(snap)
            self.assertIn("uuid-a", metrics)
            self.assertNotIn("uuid-broken", metrics)
            self.assertEqual(metrics["uuid-a"]["play_hours"], 10.0)
            self.assertEqual(metrics["uuid-a"]["total_mined"], 150)
            self.assertEqual(metrics["uuid-a"]["mob_kills"], 7)
            self.assertEqual(metrics["uuid-a"]["total_crafted"], 20)

    def test_missing_directory_returns_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ghost = Path(tmp) / "not-there"
            self.assertEqual(load_baseline_metrics(ghost), {})


class TestComputeDailyPlayHours(unittest.TestCase):
    def test_non_consecutive_dates_are_skipped(self) -> None:
        # D0, D2, D3 - gap between D0 and D2 → only D2→D3 produces an entry
        # for date D3. No entry for D2 (D1 missing) and no entry for D0 (first snap).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            uuid = "uuid-a"
            _make_snapshot(root, "2026-04-10", {uuid: {"play_hours": 1.0}})
            _make_snapshot(root, "2026-04-12", {uuid: {"play_hours": 5.0}})
            _make_snapshot(root, "2026-04-13", {uuid: {"play_hours": 7.5}})
            result = compute_daily_play_hours(root)
            self.assertIn(uuid, result)
            self.assertEqual(list(result[uuid].keys()), ["2026-04-13"])
            self.assertAlmostEqual(result[uuid]["2026-04-13"], 2.5, places=2)

    def test_negative_delta_is_filtered(self) -> None:
        # Consecutive snapshots where play_hours drops (world reset) → no entry.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            uuid = "uuid-a"
            _make_snapshot(root, "2026-04-10", {uuid: {"play_hours": 50.0}})
            _make_snapshot(root, "2026-04-11", {uuid: {"play_hours": 5.0}})
            _make_snapshot(root, "2026-04-12", {uuid: {"play_hours": 8.0}})
            result = compute_daily_play_hours(root)
            # D10→D11 is negative and must be skipped; D11→D12 is +3.0.
            self.assertEqual(list(result[uuid].keys()), ["2026-04-12"])
            self.assertAlmostEqual(result[uuid]["2026-04-12"], 3.0, places=2)


class TestComputeDeltas(unittest.TestCase):
    def test_none_baseline_returns_none(self) -> None:
        current = {"play_hours": 10, "total_mined": 500, "mob_kills": 50, "total_crafted": 200}
        self.assertIsNone(compute_deltas(current, None))

    def test_empty_baseline_returns_none(self) -> None:
        # `not baseline` catches both None and {} per the implementation contract.
        current = {"play_hours": 10, "total_mined": 500, "mob_kills": 50, "total_crafted": 200}
        self.assertIsNone(compute_deltas(current, {}))

    def test_delta_subtracts_per_key(self) -> None:
        current = {"play_hours": 10.0, "total_mined": 500, "mob_kills": 50, "total_crafted": 200}
        baseline = {"play_hours": 5.0, "total_mined": 250, "mob_kills": 25, "total_crafted": 100}
        deltas = compute_deltas(current, baseline)
        self.assertIsNotNone(deltas)
        # Every tracked key is present with exact subtraction.
        self.assertEqual(set(deltas.keys()), set(DELTA_KEYS))
        self.assertAlmostEqual(deltas["play_hours"], 5.0, places=1)
        self.assertEqual(deltas["total_mined"], 250)
        self.assertEqual(deltas["mob_kills"], 25)
        self.assertEqual(deltas["total_crafted"], 100)


if __name__ == "__main__":
    unittest.main()
