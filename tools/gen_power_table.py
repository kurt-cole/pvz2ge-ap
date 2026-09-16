#!/usr/bin/env python3
"""Generate pvz2gardendless/power_table.py: every loadout's break-even per level.

    python tools/gen_power_table.py [--workers 12] [--levels egypt2,egypt3]

Design: POWER_SIM.md. For every level pvz2gardendless/sim_data.py simulates, and
every loadout (producer type or none, attacker type, utility type or none), the
break-even is the highest HP scaling of the level's vanilla roster the loadout
survives at its best producer count (0-8), as an index into SCALES:

    0            fails even at SCALES[0] (the easiest roll the budget roll accepts)
    k (1..len)   passes at SCALES[k-1], fails at SCALES[k]
    len(SCALES)  passes at the toughest roll the budget roll accepts

Exact pruning only (see POWER_SIM.md): the economy is simulated once per
loadout and count and reused across scales; a utility is tried only where the
attacker alone is not already a pass at the toughest roll; a producer strictly
worse than another on every stat is skipped wherever the better one scores 0.

Per-level results are cached under build/power_cache/ (keyed by the simulator
and data hashes), so an interrupted run resumes.
"""

import argparse
import base64
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_PY = os.path.join(REPO, "pvz2gardendless", "power_table.py")
CACHE = os.path.join(REPO, "build", "power_cache")

# Per mille of the vanilla roster's HP. LEVEL_HARD in zombie_roll.py bounds what
# a roll can accept (750..1333); the steps in between are what generation reads.
SCALES = (750, 800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200, 1250, 1333)


def _load_sim():
    """power_sim without the package __init__ (which needs Archipelago)."""
    import importlib.util
    import types
    pkg = types.ModuleType("pvz2gardendless")
    pkg.__path__ = [os.path.join(REPO, "pvz2gardendless")]
    sys.modules.setdefault("pvz2gardendless", pkg)
    for name in ("sim_data", "level_model", "power_sim"):
        full = f"pvz2gardendless.{name}"
        if full in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            full, os.path.join(REPO, "pvz2gardendless", f"{name}.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        spec.loader.exec_module(mod)
    return sys.modules["pvz2gardendless.power_sim"]


def fingerprint():
    h = hashlib.sha256()
    for name in ("power_sim.py", "sim_data.py", "level_model.py"):
        with open(os.path.join(REPO, "pvz2gardendless", name), "rb") as fh:
            h.update(fh.read())
    h.update(repr(SCALES).encode())
    return h.hexdigest()[:16]


def dominated_by(S, producers):
    """{producer: [producers at least as good on every stat]}."""
    out = {}
    for a in producers:
        pa = S.PLANTS[a]
        better = []
        for b in producers:
            if a == b:
                continue
            pb = S.PLANTS[b]
            if (pb["s"] <= pa["s"] and pb["cd"] <= pa["cd"] and pb["cf"] <= pa["cf"]
                    and pb["pv"] >= pa["pv"] and pb["pi"] <= pa["pi"] and pb["ps"] <= pa["ps"]):
                better.append(b)
        out[a] = better
    return out


def level_table(level_id):
    S = _load_sim()
    producers = S.producers()
    attackers = S.attackers()
    utilities = S.utilities()
    waves, lanes = S.roster(level_id)
    weights = S.lane_weights(waves, lanes)
    horizon = S.horizon_for(level_id, waves)
    top = len(SCALES)
    beats = dominated_by(S, producers)

    def best(producer, attacker, utility):
        counts = [0] if producer is None else range(1, S.PRODUCERS_MAX + 1)
        result = 0
        for count in counts:
            tl = S.economy(level_id, producer, count, attacker, utility, horizon, lanes,
                           weights)

            def ok(k):
                return S.fight(level_id, tl, attacker, utility, waves, SCALES[k] / 1000.0)

            if ok(top - 1):
                return top
            if result >= 1 and not ok(result - 1):
                continue          # cannot beat what an earlier count reached
            if not ok(0):
                continue
            lo, hi = 0, top - 1   # ok(lo) true, ok(hi) false
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if ok(mid):
                    lo = mid
                else:
                    hi = mid
            result = max(result, lo + 1)
        return result

    prod_axis = [None] + producers
    util_axis = [None] + utilities
    table = bytearray(len(prod_axis) * len(attackers) * len(util_axis))
    sims = 0
    for pi, producer in enumerate(prod_axis):
        for ai, attacker in enumerate(attackers):
            base = (pi * len(attackers) + ai) * len(util_axis)
            if producer is not None and any(
                    table[((prod_axis.index(b)) * len(attackers) + ai) * len(util_axis)] == 0
                    and all(table[((prod_axis.index(b)) * len(attackers) + ai) * len(util_axis) + ui] == 0
                            for ui in range(len(util_axis)))
                    for b in beats[producer] if prod_axis.index(b) < pi):
                continue           # a better producer already failed everything
            alone = best(producer, attacker, None)
            sims += 1
            table[base] = alone
            if alone == top:
                for ui in range(1, len(util_axis)):
                    table[base + ui] = top
                continue
            for ui, utility in enumerate(util_axis[1:], start=1):
                table[base + ui] = max(alone, best(producer, attacker, utility))
                sims += 1
    return level_id, bytes(table), sims


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 0))
    ap.add_argument("--levels", default="", help="comma list; default every simulated level")
    ap.add_argument("--no-write", action="store_true", help="fill the cache only")
    ap.add_argument("--partial", action="store_true",
                    help="write the table from the levels already cached, simulate none")
    args = ap.parse_args()

    S = _load_sim()
    levels = sorted(S.LEVELS)
    if args.levels:
        levels = [lv for lv in args.levels.split(",") if lv]
    fp = fingerprint()
    cache_dir = os.path.join(CACHE, fp)
    os.makedirs(cache_dir, exist_ok=True)
    todo = [lv for lv in levels if not os.path.exists(os.path.join(cache_dir, lv + ".bin"))]
    if args.partial:
        levels = [lv for lv in levels if lv not in todo]
        todo = []
    print(f"{len(levels)} levels, {len(todo)} to simulate, {args.workers} workers, cache {fp}")

    start = time.time()
    done = 0
    with mp.Pool(args.workers, maxtasksperchild=8) as pool:
        for level_id, blob, sims in pool.imap_unordered(level_table, todo):
            with open(os.path.join(cache_dir, level_id + ".bin"), "wb") as fh:
                fh.write(blob)
            done += 1
            rate = (time.time() - start) / done
            print(f"  {level_id:28s} {sims:6d} loadout searches  "
                  f"[{done}/{len(todo)}, eta {rate * (len(todo) - done) / 60:.1f} min]",
                  flush=True)

    if args.no_write or (args.levels and not args.partial):
        return 0
    producers, attackers, utilities = S.producers(), S.attackers(), S.utilities()
    packed = {}
    for lv in levels:
        with open(os.path.join(cache_dir, lv + ".bin"), "rb") as fh:
            packed[lv] = base64.b64encode(zlib.compress(fh.read(), 9)).decode("ascii")
    text = ('"""\nPvZ2 Gardendless: break-even of every loadout per level (POWER_SIM.md).\n\n'
            "GENERATED by tools/gen_power_table.py; do not hand edit. TABLE[level] is a\n"
            "zlib-compressed byte per (producer, attacker, utility), row-major over\n"
            "PRODUCER_AXIS, ATTACKERS, UTILITY_AXIS; each byte indexes SCALES as that\n"
            "tool's docstring describes.\n\"\"\"\n\n"
            "from typing import Dict, Optional, Tuple\n\n"
            f"FINGERPRINT = {fp!r}\n"
            f"SCALES: Tuple[int, ...] = {SCALES!r}\n"
            f"PRODUCER_AXIS: Tuple[Optional[str], ...] = {tuple([None] + producers)!r}\n"
            f"ATTACKERS: Tuple[str, ...] = {tuple(attackers)!r}\n"
            f"UTILITY_AXIS: Tuple[Optional[str], ...] = {tuple([None] + utilities)!r}\n\n"
            "TABLE: Dict[str, str] = {\n")
    for lv in levels:
        text += f"    {lv!r}: {packed[lv]!r},\n"
    text += "}\n"
    with open(OUT_PY, "w", encoding="utf8") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT_PY, REPO)} ({len(text) / 1024:.0f} KB), "
          f"{(time.time() - start) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
