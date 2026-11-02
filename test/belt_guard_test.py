"""The conveyor belt guard (belt_guard.py) and its table (belt_table.py)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

from pvz2gardendless import belt_guard as G  # noqa: E402
from pvz2gardendless import belt_roll as BR  # noqa: E402
from pvz2gardendless import belt_sim as B  # noqa: E402
from pvz2gardendless import level_model  # noqa: E402
from pvz2gardendless.belt_table import BELT_SCORES, INPUT_HASH  # noqa: E402

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


if INPUT_HASH != G.input_hash():
    fail("belt_table.py is stale: the simulator or its data changed. "
         "Run python tools/gen_belt_table.py")
else:
    ok("belt_table.py matches the simulator and its data")

missing = sorted(set(B.BELTS) - set(BELT_SCORES))
if missing:
    fail(f"conveyor levels with no score: {missing[:5]}")
else:
    ok(f"every conveyor level has a score ({sum(v <= 0 for v in BELT_SCORES.values())} at 0)")

# The shipped belt beats the vanilla zombies at its own score.
bad = [lv for lv, v in BELT_SCORES.items() if v > 0 and not B.passes(lv, None, None, v)]
if bad:
    fail(f"vanilla belts failing at their own score: {bad[:5]}")
else:
    ok("each vanilla belt passes at its own score")

SEEDS = (1, 77, 2 ** 31 + 5)
levels = level_model.load()["levels"]
wrong, skipped_ok, counts = [], True, {"a0": 0, "reroll": 0, "vanilla": 0}
for seed in SEEDS:
    for lv in sorted(B.BELTS):
        pick = G.choose(seed, lv)
        if pick != G.choose(seed, lv):
            wrong.append((seed, lv, "not deterministic"))
        if BELT_SCORES.get(lv, 0) <= 0:
            if pick != 0:
                skipped_ok = False
            continue
        counts["vanilla" if pick < 0 else "reroll" if pick else "a0"] += 1
        threats = BR.level_threats(lv, G._fielded(lv, None), levels[lv]["stage"])
        need = BELT_SCORES[lv] / G.BELT_TOLERANCE
        tried = range(G.BELT_ATTEMPTS) if pick < 0 else range(pick + 1)
        for a in tried:
            passed = B.passes(lv, BR.roll(seed, lv, a, threats), None, need)
            if passed != (a == pick):
                wrong.append((seed, lv, a, passed))
                break
if wrong:
    fail(f"the guard's pick is not the first passing attempt: {wrong[:4]}")
else:
    ok(f"the pick is the first attempt that holds, over {len(SEEDS)} seeds {counts}")
if skipped_ok:
    ok("levels scoring 0 are left to attempt 0")
else:
    fail("a level scoring 0 got a guard pick")

print(f"\n{failed} FAILURE(S)" if failed else "\nBELT GUARD OK")
sys.exit(1 if failed else 0)
