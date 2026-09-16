#!/usr/bin/env python3
"""Write the parity vectors that hold the JS budget roll to the Python one.

    python tools/gen_roll_vectors.py --game-root ~/pvzge_ap_build/PVZGE-Electron

Writes test/data/zombie_roll_vectors.json:

    tables     the zombie_budget slot_data table (budget_logic.client_tables,
               minus goal and dinos, which vary per case)
    fixtures   raw level objects for a handful of levels, one per spawn source
               and edge case, with the Python model the client must extract
               from them and Python plans at several seeds, goals and dino
               settings
    rolls      model entries and plans for a spread of further levels, so the
               roll is checked well beyond the fixtures without shipping their
               raw objects

test/client/budget_test.js replays both through the client's own functions;
test/roll_vectors_test.py re-rolls them in Python so the vectors cannot go
stale. Rerun this after any change to zombie_roll.py or the level model.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "test"))
sys.path.insert(0, REPO)

OUT = os.path.join(REPO, "test", "data", "zombie_roll_vectors.json")

# One level per source kind and per edge case the client has to get right.
FIXTURES = [
    "egypt1",       # packed level, plain jittered waves
    "egypt5",       # ground spawner
    "dino8",        # vanilla dino events (never gains more)
    "pirate8",      # raiding party with the default ZombieType
    "beach12",      # bespoke: never rolled
    "dark10",       # graves, grave spawner, dynamic pool
    "future14",     # spider rain
    "sky11",        # dropship (fixed), Sky City stage-bound zombies
    "iceage10",     # storm spawner
    "aloe1",        # parachute rain
    "appease2_0",   # one object referenced from several waves
    "conceal5",     # WaveSchedulerProps events
    "kongfu35",     # qigong strikes (fixed)
    "egypt20_1",    # runtime-generated waves: never rolled
    "cowboy11",     # MaximumSun level, preset plants or not
    "tutorial3",    # three lanes: no multi-lane spawner may be rolled into it
]
FIXTURE_CASES = [(1, False, 2), (2 ** 31 + 5, True, 0), (424242, True, 2)]
ROLL_STEP = 9               # every ninth eligible level, sorted
ROLL_CASES = [(987654321, True, 1)]

MODEL_KEYS = ("waves", "stage", "bespoke", "generated", "own_plants", "planks",
              "lanes", "dynamic", "dinos", "graves")
GROUP_KEYS = ("k", "id", "w", "z", "f", "p", "rep", "bring", "pf")
PLAN_KEYS = ("attempt", "vanilla", "budget", "ratio", "dynamic", "dinos")


def client_model(level):
    out = {k: level[k] for k in MODEL_KEYS}
    out["groups"] = [{k: g[k] for k in GROUP_KEYS if k in g} for g in level["groups"]]
    return out


def client_plan(plan):
    if plan is None:
        return None
    out = {k: plan[k] for k in PLAN_KEYS}
    out["groups"] = [{k: g[k] for k in GROUP_KEYS if k in g} for g in plan["groups"]]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-root", required=True)
    args = ap.parse_args()

    import logging
    logging.disable(logging.CRITICAL)
    import apstub  # noqa: F401
    from gen_level_model import Bundle, PackedLevels, level_objects
    from pvz2gardendless import zombie_roll as R

    root = os.path.expanduser(args.game_root)
    if not os.path.isdir(os.path.join(root, "import")):
        root = os.path.join(root, "pvzge_web", "docs", "assets", "resources")
    bundle, packed = Bundle(root), PackedLevels(root)
    t = R.tables()
    levels = t.model["levels"]

    tables = {
        "zombies": {c: [z["hp"], z["cost"], z["tier"], z["excluded"] or "",
                        1 if z.get("carry", True) else 0,
                        1 if z.get("multilane") else 0,
                        1 if c in t.nullifier_names else 0]
                    for c, z in sorted(t.zombies.items())},
        "grave_hp": dict(sorted(t.model["grave_hp"].items())),
        "field_names": {k: sorted(v) for k, v in t.field_names.items()},
    }

    fixtures = []
    for lid in FIXTURES:
        objects = level_objects(bundle, packed, lid)
        if not objects or lid not in levels:
            raise SystemExit(f"fixture {lid} is not in the game data or the level model")
        fixtures.append({
            "level": lid, "objects": objects, "model": client_model(levels[lid]),
            "plans": [{"seed": s, "dinos": d, "goal": g,
                       "plan": client_plan(R.roll_level(s, lid, d, g))}
                      for s, d, g in FIXTURE_CASES],
        })

    eligible = sorted(lid for lid, lv in levels.items()
                      if R.eligible(lv) and lid not in FIXTURES)
    rolls = []
    for lid in eligible[::ROLL_STEP]:
        rolls.append({
            "level": lid, "model": client_model(levels[lid]),
            "plans": [{"seed": s, "dinos": d, "goal": g,
                       "plan": client_plan(R.roll_level(s, lid, d, g))}
                      for s, d, g in ROLL_CASES],
        })

    blob = {"note": "Generated by tools/gen_roll_vectors.py. Replayed by "
                    "test/client/budget_test.js and test/roll_vectors_test.py.",
            "tables": tables, "fixtures": fixtures, "rolls": rolls}
    with open(OUT, "w", encoding="utf8") as fh:
        json.dump(blob, fh, sort_keys=True, separators=(",", ":"))
    dinos = sum(1 for c in fixtures + rolls for p in c["plans"] if p["plan"] and p["plan"]["dinos"])
    print(f"wrote {os.path.relpath(OUT, REPO)}: {len(fixtures)} fixtures, {len(rolls)} rolls, "
          f"{dinos} plans with dino events, {os.path.getsize(OUT) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
