"""
history.py — Time-based deltas from snapshot archive.

Reads the closest snapshot to N days back (default 7) under
`stats/<server>/snapshots/YYYY-MM-DD/` and exposes per-player
deltas for a small set of headline metrics consumed by the dashboard
stat-tiles.

If no snapshot is old enough (or the snapshots dir is missing),
helpers return None / empty dicts so callers can degrade gracefully.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


DELTA_KEYS: tuple[str, ...] = ("play_hours", "total_mined", "mob_kills", "total_crafted")


def _extract_metrics(stats_path: Path) -> dict:
    """Extract the four delta-tracked metrics from a single stats JSON file.

    Mirrors the same conversions as `process_player()` for the keys used here
    (ticks → hours; sums for mined/crafted; raw mob_kills counter).
    """
    with open(stats_path) as f:
        data = json.load(f)
    stats = data.get("stats", {})
    custom = stats.get("minecraft:custom", {})
    play_ticks = custom.get(
        "minecraft:play_time",
        custom.get("minecraft:play_one_minute", 0),
    )
    return {
        "play_hours": round(play_ticks / 20 / 3600, 1),
        "total_mined": sum(stats.get("minecraft:mined", {}).values()),
        "mob_kills": custom.get("minecraft:mob_kills", 0),
        "total_crafted": sum(stats.get("minecraft:crafted", {}).values()),
    }


def find_baseline_snapshot(
    snapshots_root: Path,
    target_days: int = 7,
    min_days: int = 6,
    today: date | None = None,
) -> Path | None:
    """Return the snapshot directory closest to `target_days` ago.

    Only directories named `YYYY-MM-DD` and at least `min_days` old are
    considered — too-recent snapshots would produce misleading "weekly"
    deltas. Returns None if no snapshot qualifies.
    """
    if not snapshots_root.exists() or not snapshots_root.is_dir():
        return None
    today = today or date.today()
    target_date = today - timedelta(days=target_days)
    candidates: list[tuple[int, Path]] = []
    for d in snapshots_root.iterdir():
        if not d.is_dir():
            continue
        try:
            snap_date = date.fromisoformat(d.name)
        except ValueError:
            continue
        age_days = (today - snap_date).days
        if age_days < min_days:
            continue
        candidates.append((abs((snap_date - target_date).days), d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def load_baseline_metrics(snapshot_dir: Path) -> dict[str, dict]:
    """Map UUID → metrics dict for every readable JSON file in the snapshot."""
    out: dict[str, dict] = {}
    if snapshot_dir is None or not snapshot_dir.exists():
        return out
    for json_file in snapshot_dir.glob("*.json"):
        try:
            out[json_file.stem] = _extract_metrics(json_file)
        except (json.JSONDecodeError, OSError, ValueError):
            continue
    return out


def compute_deltas(current: dict, baseline: dict | None) -> dict | None:
    """Return `{key: current - baseline}` for `DELTA_KEYS`, or None.

    None signals "no usable baseline" so the client can hide the delta
    entirely instead of showing a misleading +0.
    """
    if not baseline:
        return None
    deltas = {}
    for k in DELTA_KEYS:
        cur = current.get(k, 0) or 0
        base = baseline.get(k, 0) or 0
        deltas[k] = round(cur - base, 1)
    return deltas
