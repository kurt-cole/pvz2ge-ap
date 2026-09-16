"""The plant-power selection (power_logic.select).

[user] Naming every passing loadout made nearly every plant progression. The
selection keeps a small set of plants, walked in play order, so that:
  - every built level with a table row keeps its passing loadouts, but only
    ones made of selected (or granted) plants;
  - levels past the opening keep power_loadouts_per_level distinct loadouts
    where the table has that many, and the opening levels keep one;
  - every counter group a rule names is cut to selected plants;
  - seeds differ in what they select;
  - plants stay a minority of progression.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401
from apstub import ItemClassification as IC, MultiWorld  # noqa: E402

import pvz2gardendless as W  # noqa: E402
from pvz2gardendless import budget_logic as B  # noqa: E402
from pvz2gardendless import power_logic as PL  # noqa: E402
from pvz2gardendless import zombie_roll as R  # noqa: E402
from pvz2gardendless.items import PLANT_ITEMS  # noqa: E402
from opts import Opts  # noqa: E402

failed = 0
PLANTS = {p.name for p in PLANT_ITEMS}
# [guess] A ceiling, not a target: 23-26% measured on 2026-09-16 at the defaults.
MAX_PLANT_PROGRESSION_SHARE = 0.40


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


def build(seed, **kw):
    mw = MultiWorld()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    w.random = random.Random(seed)
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    return mw, w


if not PL.available():
    print("  skip  no power_table.py in this checkout")
    sys.exit(0)

print("\n=== selection ===")
selections = []
for seed in (1, 2, 3):
    for per in (2, 3):
        mw, w = build(seed, shuffle_zombies=1, power_loadouts_per_level=per)
        sel = w.power_selection
        avail = set(sel) | set(w.starting_plants)
        sets = PL._plant_sets()
        short, foreign = [], []
        for loc in w.active_locations():
            n = loc.name
            if not PL.has_level(n):
                continue
            full = PL.requirement_for(n, PL._ratio(w, n))
            kept = PL.level_requirement(w, n) or frozenset()
            if any(not sets[i] <= avail for i in kept) and kept != full:
                foreign.append(n)
            need = 1 if n in R.OPENING_LEVELS else per
            want = min(need, PL._antichain_count({sets[i] for i in full}))
            if PL._antichain_count({sets[i] for i in kept}) < want:
                short.append(n)
            for g in PL.nullifier_groups(w, n):
                if not set(g) <= avail:
                    foreign.append(n + " (counter)")
        for n in B.slot_level_hazard_groups(w):
            for g in B.slot_level_hazard_groups(w)[n]:
                if not set(g) <= avail:
                    foreign.append(n + " (hazard)")
        pool = mw.itempool
        plants = [i for i in pool if i.name in PLANTS]
        prog = [i for i in plants if i.classification & IC.progression]
        share = len(prog) / max(1, len(plants))
        label = f"seed {seed}, {per} per level"
        if short:
            fail(f"{label}: levels with too few loadouts: {short[:5]}")
        elif foreign:
            fail(f"{label}: rules name unselected plants: {foreign[:5]}")
        elif share > MAX_PLANT_PROGRESSION_SHARE:
            fail(f"{label}: {len(prog)} of {len(plants)} pool plants are progression")
        else:
            ok(f"{label}: {len(sel)} selected, {len(prog)}/{len(plants)} pool plants "
               f"progression ({share:.0%})")
        if per == 2:
            selections.append(sel)

if len(set(selections)) < 2:
    fail("every seed selected the same plants")
else:
    ok(f"seeds differ: {len(set(selections))} distinct selections over 3 seeds")

print(f"\n{failed} FAILURE(S)" if failed else "\nPOWER SELECTION OK")
sys.exit(1 if failed else 0)
