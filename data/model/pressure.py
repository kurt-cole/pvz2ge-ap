"""The demand side: how much HP a level throws at you, and how fast.

THE METRIC. A zombie entering the lawn is not a lump of HP, it is a lump of HP
on a clock: you have exactly as long as it takes to walk nine columns. So the
unit everything here is measured in is

    threat rate  r(z) = effective_hp(z) / cross_seconds(z)      [HP/second]

which reads directly as "the damage per second you must land on this zombie to
kill it exactly at the house line". Summed over everything on the lawn at time
t, that is REQUIRED DPS -- the answer to "what damage output does this level
demand", stated in the same unit a plant's dps is stated in, which is what
makes the two comparable at all.

Derived from the required-DPS curve:

    peak            max over the level. What the hardest moment asks for.
    sustained       the 75th percentile. What the level asks for most of the
                    time -- peak alone reads a single flag wave as the level.
    per_lane        peak / usable rows. Five rows of 500 HP/s is a different
                    game from one row of 500, and a level with a water half
                    has fewer rows to work with.
    front_loading   how much of the total arrives in the first third. A level
                    that front-loads is a sun problem; one that back-loads is
                    a scaling problem.
    burst_index     peak / sustained. High means spikes, which burst plants
                    answer and sustained DPS does not.
    index           log2(per_lane / BASELINE), a flat difficulty scale where
                    +1 is "twice the pressure". Anchored on the first level of
                    the game so the number is stable when new content is added.

WHAT THIS IS NOT. It is not a simulation. Plants do not fire, zombies do not
eat, armor is HP rather than a damage filter, and the wave clock is nominal
(see extract/levels.py). It is a COMPARATOR: it ranks levels against each other
on the one axis that matters for logic, and every number it produces should be
quoted as "egypt19-equivalent", never as an absolute.
"""

# Anchor for `index`. Recomputed by calibrate() from the real dataset when one
# is available; this default keeps the scale sane in structure-only mode.
BASELINE_PER_LANE = 12.0

DEFAULT_ROWS = 5

# Levels in the rolling window equivalent_level() uses. Ten is about a quarter
# of a world -- long enough to ignore one outlier, short enough to still track
# a world's own ramp.
EQUIV_WINDOW = 10


def _series(level, zombies, step=1.0):
    """(times, required_dps) sampled every `step` seconds."""
    waves = level.get("waves") or []
    if not waves:
        return [], []
    end = level.get("duration") or (waves[-1]["at"] + 40.0)
    times = [t * step for t in range(int(end / step) + 1)]
    values = [0.0] * len(times)
    for wave in waves:
        for cns, count in wave["zombies"].items():
            z = zombies.get(cns) or {}
            hp = z.get("effective_hp") or 0.0
            cross = z.get("cross_seconds") or 30.0
            if hp <= 0:
                continue
            rate = hp / cross * count
            start, stop = wave["at"], wave["at"] + cross
            for i, t in enumerate(times):
                if start <= t < stop:
                    values[i] += rate
    return times, values


def _pct(sorted_values, q):
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * q))
    return sorted_values[idx]


def measure(level, zombies):
    """Pressure record for one level, or a stub when it has no wave data."""
    waves = level.get("waves") or []
    rows = (level.get("grid") or {}).get("rows") or DEFAULT_ROWS
    water = (level.get("grid") or {}).get("water_rows") or 0
    usable = max(rows - (water if "water" not in level.get("tokens", []) else 0), 1)

    if not waves:
        return {
            "codename": level.get("codename"),
            "measured": False,
            "why": "no wave data -- run the extractor against a game checkout",
            "peak": None, "sustained": None, "per_lane": None,
            "index": None, "total_hp": level.get("total_hp"),
            "curve": [],
        }

    times, values = _series(level, zombies)
    ordered = sorted(values)
    peak = max(values) if values else 0.0
    sustained = _pct(ordered, 0.75)
    per_lane = peak / usable
    third = max(1, len(values) // 3)
    total = sum(values) or 1.0
    import math
    return {
        "codename": level.get("codename"),
        "measured": True,
        "peak": round(peak, 1),
        "sustained": round(sustained, 1),
        "per_lane": round(per_lane, 2),
        "usable_rows": usable,
        "front_loading": round(sum(values[:third]) / total, 3),
        "burst_index": round(peak / sustained, 2) if sustained else None,
        "index": round(math.log2(max(per_lane, 0.01) / BASELINE_PER_LANE), 2),
        "total_hp": level.get("total_hp"),
        "wave_count": len(waves),
        # Downsampled to <=120 points: the site plots it, nothing computes on
        # it, and a full 1s series over 40 levels is megabytes of bundle.
        "curve": [round(v, 1) for v in values[::max(1, len(values) // 120)]],
        "curve_step_s": round((times[-1] if times else 0) / max(1, min(120, len(values))), 2),
    }


def calibrate(pressures, anchor="egypt1"):
    """Re-anchor `index` on a named level, in place. Returns the baseline used."""
    global BASELINE_PER_LANE
    base = (pressures.get(anchor) or {}).get("per_lane")
    if not base:
        measured = [p["per_lane"] for p in pressures.values()
                    if p.get("per_lane")]
        if not measured:
            return BASELINE_PER_LANE
        base = min(measured)
    BASELINE_PER_LANE = base
    import math
    for rec in pressures.values():
        if rec.get("per_lane"):
            rec["index"] = round(math.log2(rec["per_lane"] / base), 2)
    return base


def equivalent_level(index_value, main_path):
    """The point in the main game by which a player has met this much pressure.

    `main_path` must be in PROGRESSION order -- world order, then play order.
    Getting that wrong is not cosmetic: sorted alphabetically, Aerial Fortress
    leads, and every side path in the game reports "plays like sky3".

    A RUNNING MAX, not the first level over the line, so one spiky early level
    does not become the answer for everything after it. The result reads as
    "by here, you have faced this", which is the honest claim -- a path's step 3
    is not "3 levels in", it is "as hard as anything before dark22", and that is
    where it belongs.
    """
    if index_value is None:
        return None
    series = [(cns, idx) for cns, idx in main_path if idx is not None]
    if not series:
        return None
    # Rolling median over the last EQUIV_WINDOW levels, then monotonised. The
    # median is what stops one storm level from answering for the rest of the
    # game: egypt5 is a ground-spawner level at index 2.7 in a world that is
    # otherwise under 1.2, and on a plain running max EVERY side path in the
    # game reported "plays like egypt5". The median asks the better question --
    # where does this much pressure become NORMAL rather than exceptional --
    # and that is the level a gate belongs behind.
    running = None
    for i, (cns, _idx) in enumerate(series):
        window = sorted(v for _c, v in series[max(0, i - EQUIV_WINDOW + 1):i + 1])
        median = window[len(window) // 2]
        running = median if running is None else max(running, median)
        if running >= index_value:
            return cns
    # Nothing in the main game ever gets this heavy. Returning the last level
    # would read as "plays like the final level" and hide the actual finding,
    # which is that this content is off the end of the curve entirely.
    return None
