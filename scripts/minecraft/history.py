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
    max_days: int = 30,
    today: date | None = None,
) -> Path | None:
    """Return the snapshot directory closest to `target_days` ago.

    Only directories named `YYYY-MM-DD` whose age (in days) falls in
    `[min_days, max_days]` are considered — too-recent snapshots would
    produce noisy "weekly" deltas, and too-old ones would be misleading
    after a long pause (e.g. 2-week hiatus). Returns None if no snapshot
    qualifies. The actual window may differ from `target_days`; callers
    should display it via the snapshot directory name.
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
        if age_days < min_days or age_days > max_days:
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


def _load_play_hours(snapshot_dir: Path) -> dict[str, float]:
    """Map UUID → play_hours for every readable JSON in this snapshot."""
    out: dict[str, float] = {}
    for json_file in snapshot_dir.glob("*.json"):
        try:
            out[json_file.stem] = _extract_metrics(json_file)["play_hours"]
        except (json.JSONDecodeError, OSError, ValueError, KeyError):
            continue
    return out


def compute_daily_play_hours(snapshots_root: Path) -> dict[str, dict[str, float]]:
    """Map UUID → {YYYY-MM-DD: hours_played_that_day} from consecutive snapshots.

    Only days where snapshot D and snapshot D-1 both exist contribute an entry —
    the delta is attributed to date D. Gap days are omitted entirely (no faked
    zeros), so the heatmap renders them as empty cells. Negative deltas (world
    reset, data corruption) are filtered out.
    """
    if not snapshots_root.exists() or not snapshots_root.is_dir():
        return {}
    snaps: list[tuple[date, Path]] = []
    for d in snapshots_root.iterdir():
        if not d.is_dir():
            continue
        try:
            snaps.append((date.fromisoformat(d.name), d))
        except ValueError:
            continue
    snaps.sort()
    if len(snaps) < 2:
        return {}
    result: dict[str, dict[str, float]] = {}
    prev_date, prev_dir = snaps[0]
    prev_hours = _load_play_hours(prev_dir)
    for cur_date, cur_dir in snaps[1:]:
        cur_hours = _load_play_hours(cur_dir)
        if (cur_date - prev_date).days == 1:
            iso = cur_date.isoformat()
            for uuid, h in cur_hours.items():
                delta = round(h - prev_hours.get(uuid, 0), 2)
                if delta > 0:
                    result.setdefault(uuid, {})[iso] = delta
        prev_date, prev_dir, prev_hours = cur_date, cur_dir, cur_hours
    return result


def compute_rank_changes(
    current_players: dict[str, dict],
    baseline_metrics: dict[str, dict],
    uuid_to_name: dict[str, str],
    keys: tuple[str, ...] = DELTA_KEYS,
) -> list[dict]:
    """Return the list of significant rank changes between baseline and now.

    For each tracked metric we rank players by descending value at baseline
    and today, then emit an entry whenever a player's rank improved (delta
    > 0) AND a specific "overtaken" player can be identified — namely the
    player now just behind them who was ahead of them at baseline.

    Returned list is sorted by `delta_rank` desc then `current_value` desc
    and capped at 10 entries. No "loss" narrative is ever emitted — only
    improvements, so the feature stays feel-good on a public dashboard.
    """
    if not current_players or not baseline_metrics:
        return []
    name_to_uuid = {v: k for k, v in uuid_to_name.items()}
    out: list[dict] = []
    for metric in keys:
        ranked_cur = sorted(
            [
                (name, p.get(metric, 0) or 0)
                for name, p in current_players.items()
                if name_to_uuid.get(name) in baseline_metrics
            ],
            key=lambda x: -x[1],
        )
        ranked_base = sorted(
            [
                (uuid_to_name[uuid], m.get(metric, 0) or 0)
                for uuid, m in baseline_metrics.items()
                if uuid in uuid_to_name
            ],
            key=lambda x: -x[1],
        )
        cur_rank = {name: i for i, (name, _) in enumerate(ranked_cur)}
        base_rank = {name: i for i, (name, _) in enumerate(ranked_base)}
        cur_value = dict(ranked_cur)
        base_value = dict(ranked_base)
        for name, _ in ranked_cur:
            if name not in base_rank:
                continue
            delta = base_rank[name] - cur_rank[name]
            if delta <= 0:
                continue
            my_cur = cur_rank[name]
            my_base = base_rank[name]
            overtaken = next(
                (
                    n
                    for n, r in cur_rank.items()
                    if r == my_cur + 1 and base_rank.get(n, 10**9) < my_base
                ),
                None,
            )
            if not overtaken:
                continue
            out.append({
                "metric": metric,
                "player": name,
                "overtaken": overtaken,
                "delta_rank": delta,
                "current_value": cur_value[name],
                "baseline_value": base_value.get(name, 0),
            })
    out.sort(key=lambda x: (-x["delta_rank"], -x["current_value"]))
    return out[:10]


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
