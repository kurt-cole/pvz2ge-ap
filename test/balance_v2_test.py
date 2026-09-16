"""The budget zombie roll (pvz2gardendless/zombie_roll.py), replayed over every level.

balance_test.py makes this promise for the v1 tier shuffle. This makes it for
the budget roll: at several seeds, every level it may touch lands inside the
level guard, it is really a randomizer (most spawns change), set pieces are
never touched, terrain and count-field sources stay legal, and the roll is a
pure function of its inputs. The bands are the promise; re-earn them rather
than widening them.
"""
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

from pvz2gardendless import zombie_roll as R  # noqa: E402

SEEDS = [987654321, 1, 2 ** 31, 424242, 7]
P5_MIN, P95_MAX = 850, 1150        # per mille of vanilla HP
MAX_VANILLA_FALLBACK = 0.05        # share of eligible levels
MIN_CHANGED = 0.60                 # mean share of spawns that change
CANNON_LEVELS = ("pirate3", "pirate11", "pirate20", "pirate20_1")

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


t = R.tables()
levels = t.model["levels"]
eligible = sorted(lid for lid, lv in levels.items() if R.eligible(lv))
ok(f"{len(eligible)} of {len(levels)} levels are eligible for the roll")

for lid in CANNON_LEVELS:
    if R.roll_level(SEEDS[0], lid) is not None:
        fail(f"{lid}, a cannon bonus level, was rolled")
skipped = [lid for lid, lv in levels.items() if not R.eligible(lv)
           and R.roll_level(SEEDS[0], lid) is not None]
if skipped:
    fail(f"bespoke or generated levels were rolled: {skipped[:5]}")
else:
    ok("no bespoke or runtime-generated level is ever rolled, cannon levels included")

# Plant food. The count belongs to the wave source, but the carriers are picked
# out of the zombies it actually spawned, and the grave spawner never comes back
# for types that cannot carry. So a group owing plant food has to keep enough
# zombies able to take it, or the level quietly drops less than it was authored
# to. The client asserts the same thing against the shipped vectors.
short, owed = [], 0
for seed in SEEDS[:2]:
    for lid in eligible:
        plan = R.roll_level(seed, lid)
        if plan["vanilla"]:
            continue
        need = {g["id"]: g["pf"] for g in levels[lid]["groups"] if g.get("pf")}
        for g in plan["groups"]:
            n = need.get(g["id"], 0)
            if not n or g["k"] not in R.LIST_KINDS:
                continue
            owed += 1
            carriers = sum(count for c, count in g["z"] if t.carry.get(c, True))
            if carriers < n:
                short.append(f"{lid}/{g['id']}: owes {n}, fields {carriers}")
if short:
    fail(f"{len(short)} of {owed} groups cannot hand out their plant food: {short[:3]}")
else:
    ok(f"all {owed} plant food groups keep enough carriers to hand it out")

# Narrow lawns. The tutorial levels roll their sod out one strip at a time and
# disable the lanes they have not reached, and a chicken thrower or a barrel
# puts bodies into the lanes either side of its own without asking whether they
# are playable. The player cannot answer a zombie in a lane they cannot plant
# in, so the roll may not field one there.
narrow = [lid for lid in eligible if levels[lid].get("lanes", 5) < 5]
wide = [lid for lid in eligible if levels[lid].get("lanes", 5) >= 5]
bad, reached = [], 0
for seed in SEEDS:
    for lid in narrow:
        plan = R.roll_level(seed, lid)
        if plan["vanilla"]:
            continue
        for g in plan["groups"]:
            for c, _ in g["z"]:
                if c in t.multilane_names:
                    bad.append(f"{lid}/{g['id']}: {c} spawns into lanes {lid} has not got")
    reached += sum(1 for lid in wide if any(c in t.multilane_names
                                            for g in (R.roll_level(seed, lid) or {})["groups"]
                                            for c, _ in g["z"]))
if not narrow:
    fail("no level with fewer than five lanes, so nothing was really checked")
elif bad:
    fail(f"{len(bad)} multi-lane spawns on a narrow lawn: {bad[:3]}")
elif not reached:
    fail("multi-lane spawners were kept out of every level, not just narrow ones")
else:
    ok(f"{len(narrow)} narrow levels field no multi-lane spawner; "
       f"the wider lawns take them {reached} times over {len(SEEDS)} seeds")

# The dynamic pool mapping is not filtered, which is only safe while no narrow
# level has a dynamic pool for it to put a multi-lane zombie into.
if any(levels[lid]["dynamic"] for lid in narrow):
    fail("a narrow level grew a dynamic zombie pool, which the roll does not filter")
else:
    ok("no narrow level has a dynamic pool, so the unfiltered mapping cannot reach one")

start = time.time()
for seed in SEEDS:
    ratios, changed, fallback, problems = [], [], 0, []
    for lid in eligible:
        level = levels[lid]
        plan = R.roll_level(seed, lid)
        if plan["vanilla"]:
            fallback += 1
            continue
        ratios.append(plan["ratio"])
        before, after = R.roster({"groups": level["groups"]}), R.roster(plan)
        total = sum(before.values())
        if total:
            changed.append(1 - sum(min(before[c], after[c]) for c in before) / total)
        for g_old, g_new in zip(level["groups"], plan["groups"]):
            if g_old["id"] != g_new["id"] or g_old["w"] != g_new["w"]:
                problems.append(f"{lid}: group order changed")
                break
            old_keys = {t.bucket_key(c) for c, _ in g_old["z"]}
            for c, n in g_new["z"]:
                if t.bucket_key(c) not in old_keys and c not in dict(map(tuple, g_old["z"])):
                    problems.append(f"{lid}/{g_new['id']}: {c} crossed terrain or stage")
            if g_old["k"] in R.FIELD_KINDS and g_new.get("p"):
                if g_new["p"] not in t.field_names[g_old["k"]]:
                    problems.append(f"{lid}/{g_new['id']}: {g_new['p']} never names a {g_old['k']}")
            n_old = sum(n for _, n in g_old["z"])
            n_new = sum(n for _, n in g_new["z"])
            if n_new > max(n_old * R.CAP_MULT, n_old + R.CAP_ADD):
                problems.append(f"{lid}/{g_new['id']}: {n_old} spawns became {n_new}")
    ratios.sort()
    p5 = ratios[int(len(ratios) * 0.05)]
    p95 = ratios[int(len(ratios) * 0.95)]
    worst = (ratios[0], ratios[-1])
    label = f"seed {seed}"
    if problems:
        fail(f"{label}: {len(problems)} illegal rolls, first {problems[:3]}")
    if not R.LEVEL_HARD[0] <= worst[0] or not worst[1] <= R.LEVEL_HARD[1]:
        fail(f"{label}: a shipped level left the hard band: {worst}")
    if p5 < P5_MIN or p95 > P95_MAX:
        fail(f"{label}: p5 {p5} / p95 {p95} outside {P5_MIN}-{P95_MAX}")
    if fallback > MAX_VANILLA_FALLBACK * len(eligible):
        fail(f"{label}: {fallback} levels fell back to vanilla")
    mean_changed = statistics.mean(changed)
    if mean_changed < MIN_CHANGED:
        fail(f"{label}: only {mean_changed:.0%} of spawns change")
    ok(f"{label}: ratio p5 {p5} median {statistics.median(ratios)} p95 {p95}, "
       f"worst {worst[0]}-{worst[1]}, {fallback} vanilla, {mean_changed:.0%} changed")
ok(f"{len(SEEDS) * len(eligible)} rolls in {time.time() - start:.1f}s")

# A pure function: the same inputs give the same plan.
if R.roll_level(SEEDS[1], "dark10") != R.roll_level(SEEDS[1], "dark10"):
    fail("rolling dark10 twice gave two plans")
else:
    ok("the roll is deterministic")

# Travelling dinos: off adds none; on adds some, only where allowed, and a level
# that gains none rolls exactly as it does with the option off.
gained, same, bad = 0, True, []
for lid in eligible:
    off = R.roll_level(SEEDS[0], lid)
    on = R.roll_level(SEEDS[0], lid, dinos=True)
    if off["dinos"]:
        bad.append(f"{lid} gained dinos with the option off")
    if on["dinos"]:
        gained += 1
        if not R.dinos_allowed(levels[lid]):
            bad.append(f"{lid} gained dinos but is not allowed them")
        if "dino" not in R.hazards(on):
            bad.append(f"{lid} gained dinos but no dino hazard")
    elif on != off:
        same = False
if bad:
    fail(f"dinos: {bad[:3]}")
elif not gained:
    fail("travelling dinos never added a dino anywhere")
elif not same:
    fail("a level that gained no dinos rolled differently with the option on")
else:
    ok(f"travelling dinos reach {gained} levels, only where allowed")

# The Jurassic Marsh curve constants still describe the data.
derived = R.derive_dino_bands(t)
if derived != R.DINO_BANDS:
    fail(f"DINO_BANDS no longer match Jurassic Marsh: derived {derived}")
else:
    ok("DINO_BANDS match the Jurassic Marsh levels they were measured from")

from pvz2gardendless.constants import EGYPT_SUN_CUT, WORLD_REGIONS  # noqa: E402
from pvz2gardendless.locations import LOC_NAME_TO_DATA, world_stretches  # noqa: E402

chances = []
for keep in (1, 2, 3):          # stretches kept by world key, zomboss, completion
    jm = other = 0
    for world in WORLD_REGIONS:
        names = [n for n, d in LOC_NAME_TO_DATA.items()
                 if d.region.startswith(world) and n in levels]
        stretches = world_stretches(names, EGYPT_SUN_CUT if world == "Ancient Egypt" else None)
        if world == "Ancient Egypt":
            stretches = [stretches[0] + stretches[1], stretches[2], stretches[3]]
        kept = [lid for s in stretches[:keep] for lid in s]
        if world == "Jurassic Marsh":
            jm += len(kept)
        else:
            # Only levels that can take dinos: the expected number of dino
            # levels then matches Jurassic Marsh's count.
            other += sum(1 for lid in kept if R.dinos_allowed(levels[lid]))
    chances.append(jm * 1000 // other)
if tuple(chances) != R.DINO_LEVEL_PERMILLE_BY_GOAL:
    fail(f"DINO_LEVEL_PERMILLE_BY_GOAL is stale: derived {tuple(chances)}")
else:
    ok(f"dino chance per goal {tuple(chances)} per mille matches Jurassic Marsh's share")

# Per goal: every added event set sits inside its band's limits. The chances
# are not in goal order (each cut has its own dino-valid denominator), so the
# goals' dino levels do not nest and are not asserted to.
by_goal, band_bad = [], []
for goal in (0, 1, 2):
    got = set()
    for lid in eligible:
        plan = R.roll_level(SEEDS[2], lid, dinos=True, goal_type=goal)
        if not plan["dinos"]:
            continue
        got.add(lid)
        level = levels[lid]
        per_wave = R.level_budget(t, level) // level["waves"]
        ceiling, lo, hi, first, _ = next(b for b in R.DINO_BANDS if per_wave <= b[0])
        n = len(plan["dinos"])
        if not max(1, level["waves"] * lo // 1000) <= n <= max(1, level["waves"] * hi // 1000):
            band_bad.append(f"{lid}: {n} events outside {lo}-{hi} per mille of {level['waves']} waves")
        if any(w < min(first, level["waves"]) or w > level["waves"] for w, _, _ in plan["dinos"]):
            band_bad.append(f"{lid}: an event before wave {first} or past the last wave")
    by_goal.append(got)
if band_bad:
    fail(f"dino events broke their band: {band_bad[:3]}")
else:
    ok(f"dino levels per goal (world key, zomboss, completion): "
       f"{[len(g) for g in by_goal]} of {len(eligible)}, inside their bands")

print(f"\n{failed} FAILURE(S)" if failed else "\nBUDGET ROLL OK")
sys.exit(1 if failed else 0)
