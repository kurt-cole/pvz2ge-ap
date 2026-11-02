"""The Aerial Fortress ship model: the roll guard (ship_sim.py) and the ship
fight in power_sim.py. Design: POWER_SIM.md, "Ship levels"."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

from pvz2gardendless import power_sim as P  # noqa: E402
from pvz2gardendless import ship_sim as S  # noqa: E402
from pvz2gardendless import zombie_roll as R  # noqa: E402
from pvz2gardendless.level_model import load  # noqa: E402

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


LEVELS = load()["levels"]
SEEDS = [s * 2654435761 % 2 ** 32 for s in range(12)]

# ── the data ─────────────────────────────────────────────────────────────────
bad = [lv for lv in S.SHIPS if not LEVELS[lv]["stage"].startswith("Sky")]
if bad:
    fail(f"ship records on lawns that are not Aerial Fortress: {bad}")
elif len(S.SHIPS) < 20:
    fail(f"only {len(S.SHIPS)} ship levels; sim_data.py predates the ship table?")
else:
    ok(f"{len(S.SHIPS)} ship levels, all on Aerial Fortress lawns")

actors = {c: z["ship"] for c, z in P.ZOMBIES.items() if "ship" in z}
if actors.get("sky_battleplane", [0, 0])[1] <= 0 or actors.get("sky", [0, 0])[0] <= 0:
    fail(f"ship damage missing: sky {actors.get('sky')}, battleplane {actors.get('sky_battleplane')}")
else:
    ok(f"{len(actors)} zombies act on the ship (firing and crashing both present)")

# ── calibration ──────────────────────────────────────────────────────────────
off = []
for lv in sorted(S.SHIPS):
    dps = S.reference_dps(lv)
    if dps <= S._DPS_LO:
        continue                       # a vanilla roster that cannot reach half
    # Crashes land in 1200-2000 chunks, so damage is a step function of dps:
    # the reference is the weakest defence keeping vanilla at or under half.
    goal = S.SHIPS[lv]["hp"] * S.CALIBRATION_PERMILLE / 1000
    if not (S.damage(lv, None, dps) <= goal < S.damage(lv, None, dps * 0.99)):
        off.append(lv)
if off:
    fail(f"reference defence is not the weakest keeping vanilla under half: {off[:4]}")
else:
    ok("every reference defence is the weakest keeping vanilla at or under half the ship")

# ── the guard ────────────────────────────────────────────────────────────────
same_unguarded, rejected, bad_pick, bad_forced, checked = 0, 0, [], [], 0
for lv in sorted(S.SHIPS):
    for seed in SEEDS:
        free = R.roll_level(seed, lv)
        if free is None:
            continue
        checked += 1

        def guard(p, lv=lv):
            return S.accepts(lv, p)
        held = R.roll_level(seed, lv, accept=guard)
        if not held["vanilla"] and not S.accepts(lv, held):
            bad_pick.append((lv, seed))
        if not free["vanilla"] and not S.accepts(lv, free):
            rejected += 1
        elif held == free:
            same_unguarded += 1
        again = R.roll_level(seed, lv, forced=held["attempt"])
        if again != held:
            bad_forced.append((lv, seed))
if bad_pick:
    fail(f"the guarded roll chose a plan its guard rejects: {bad_pick[:4]}")
else:
    ok(f"{checked} guarded rolls all pass the guard ({rejected} unguarded ones did not)")
if bad_forced:
    fail(f"forcing the chosen attempt does not reproduce the plan: {bad_forced[:4]}")
else:
    ok("forcing the chosen attempt reproduces every guarded plan (the client's path)")
if rejected == 0:
    fail("no unguarded roll was rejected: the guard tests nothing")

# A roll the guard leaves alone is the unguarded roll, and a non-ship level is
# never touched: accept=None is the spec.
plain = R.roll_level(SEEDS[0], "egypt8")
if plain != R.roll_level(SEEDS[0], "egypt8", accept=None):
    fail("accept=None changed a roll")
else:
    ok(f"accept=None is the unguarded roll ({same_unguarded} ship rolls unchanged by the guard)")

# ── the ship fight ───────────────────────────────────────────────────────────
# [data, this model] sky1 with five Sunflowers and Skyshooter passes; with no
# producer and Peashooter it lets enough zombies reach the ship to lose it.
if not P.simulate("sky1", "Sunflower", 5, "Skyshooter", None, 1.0):
    fail("sky1: Sunflower x5 + Skyshooter no longer passes")
else:
    ok("sky1: Sunflower x5 + Skyshooter passes the ship fight")
if P.simulate("sky1", None, 0, "Peashooter", None, 1.333):
    fail("sky1: a lone Peashooter at the toughest roll keeps the ship")
else:
    ok("sky1: a lone Peashooter at the toughest roll loses the ship")
if P.level_cap("sky1", "Melon-Pult", 1) != S.SHIPS["sky1"]["deck"] - 1 or \
        P.level_cap("sky1", "Skyshooter", 1) != P.lane_cap(1) or \
        P.level_cap("egypt8", "Melon-Pult", 1) != P.lane_cap(1):
    fail("lane cap: deck-only for grounded attackers on ship levels, as before elsewhere")
else:
    ok("lane cap: deck columns for grounded attackers on a ship, full lane when floating")

print(f"\n{failed} FAILURE(S)" if failed else "\nSHIP SIM OK")
sys.exit(1 if failed else 0)
