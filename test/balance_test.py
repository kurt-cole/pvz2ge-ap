"""Replay the client's own zombie roll over every shipped level.

The tier partition (zombie_tier_test.py) says a swap is fair one zombie at a
time. This says it is fair a LEVEL at a time, which is the thing a player
actually meets: it runs the client's exact roll -- the same FNV-1a hash, the
same mulberry32 stream, the same per-level plan, injective assignment and
budget guard -- over test/data/zombie_balance.json, which holds every shipped
level's roster and every zombie's effective HP.

This is the test that would have caught pirate1. Under the old cost-only
tiers it fielded eighteen 10000 HP shields in place of its basic pirates, a
27x level, and every suite in the repo passed: nothing looked at what a whole
level turned into.

The port is deliberately verbatim rather than clever. If the client's roll
changes, this must change with it, and the numbers below have to be re-earned
rather than relaxed.
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

from pvz2gardendless.zombie_data import ZOMBIE_HP, ZOMBIE_TIERS, ZOMBIE_TIER_OF  # noqa: E402

EXTRACT = os.path.join(HERE, "data", "zombie_balance.json")

# What a shuffled level is allowed to do to itself, as a multiple of the
# effective HP the level shipped with. These are assertions about the option,
# not about this seed: they are checked at every seed below.
P95_BAND = (0.85, 1.20)    # the bulk of levels barely move
WORST_BAND = (0.55, 1.65)  # and none of them may run away
MIN_CHANGED = 0.35         # ...while it still has to be a shuffle

# Seeds to replay. More than one because a single seed passing says nothing
# about the next player's.
SEEDS = [987654321, 1, 2 ** 31, 424242, 7]

# The client's guard, mirrored. See _apPlanFor in build_pvzge_ap.py.
BUDGET_OK = (0.85, 1.15)
BUDGET_HARD = (0.60, 1.60)
BUDGET_TRIES = 6

MASK = 0xFFFFFFFF

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


# ── the client's RNG, ported verbatim ────────────────────────────────────────

def _u(x):
    return x & MASK


def imul(a, b):
    return _u(_u(a) * _u(b))


def ap_hash(text: str) -> int:
    """FNV-1a, as _apHash."""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = imul(h, 16777619)
    return _u(h)


def ap_rng_first(seed: int) -> float:
    """The first draw of _apRng's mulberry32 stream.

    Only the first draw is ever taken: the client makes a fresh stream per
    codename rather than walking one.
    """
    a = _u(_u(seed) + 0x6D2B79F5)
    t = imul(a ^ (a >> 15), 1 | a)
    t = _u(_u(t + imul(t ^ (t >> 7), 61 | t)) ^ t)
    return _u(t ^ (t >> 14)) / 4294967296


# ── the client's plan, ported verbatim ───────────────────────────────────────

def roll_plan(seed: int, level_key: str, roster: dict, salt: int) -> dict:
    """_apRollPlan: one roll of the whole level, injective where it can be."""
    plan, used = {}, set()
    for codename in sorted(roster):
        pool = ZOMBIE_TIERS[ZOMBIE_TIER_OF[codename]]
        if len(pool) < 2:
            plan[codename] = codename
            continue
        key = f"{seed}|{level_key}|{codename}" + (f"|a{salt}" if salt else "")
        pick = pool[int(ap_rng_first(ap_hash(key)) * len(pool))]
        for _ in range(len(pool)):
            if pick not in used:
                break
            pick = pool[(pool.index(pick) + 1) % len(pool)]
        used.add(pick)
        plan[codename] = pick
    return plan


def weigh(roster: dict, plan=None) -> int:
    """_apRosterWeight: what killing this roster costs."""
    return sum(ZOMBIE_HP.get(plan[z] if plan else z, 0) * n
               for z, n in roster.items())


def plan_for(seed: int, level_key: str, roster: dict) -> dict:
    """_apPlanFor: roll, weigh, re-roll, and refuse rather than ship unfair."""
    before = weigh(roster)
    best, best_err = None, math.inf
    for attempt in range(BUDGET_TRIES):
        plan = roll_plan(seed, level_key, roster, attempt)
        if not before:
            return plan
        ratio = weigh(roster, plan) / before
        if BUDGET_OK[0] <= ratio <= BUDGET_OK[1]:
            return plan
        err = abs(math.log(ratio or 1e-6))
        if err < best_err:
            best, best_err = (plan, ratio), err
    if best and BUDGET_HARD[0] <= best[1] <= BUDGET_HARD[1]:
        return best[0]
    return {z: z for z in roster}


# ── the replay ───────────────────────────────────────────────────────────────

with open(EXTRACT, encoding="utf8") as fh:
    extract = json.load(fh)

levels = extract["levels"]
shufflable = {lid: lv for lid, lv in levels.items() if not lv["bespoke"]}
ok(f"{len(levels)} shipped levels in the extract, {len(shufflable)} of them "
   f"shufflable ({len(levels) - len(shufflable)} bespoke)")

worst_overall = None
for seed in SEEDS:
    ratios, changed_fractions, offenders = [], [], []
    for lid, level in sorted(shufflable.items()):
        roster = {z: n for z, n in level["zombies"].items()
                  if z in ZOMBIE_TIER_OF}
        if not roster:
            continue
        before = weigh(roster)
        if not before:
            continue
        plan = plan_for(seed, lid, roster)
        ratio = weigh(roster, plan) / before
        ratios.append(ratio)
        spawns = sum(roster.values())
        if spawns:
            changed_fractions.append(
                sum(n for z, n in roster.items() if plan[z] != z) / spawns)
        if not WORST_BAND[0] <= ratio <= WORST_BAND[1]:
            offenders.append((lid, ratio))

    ratios.sort()
    p5 = ratios[max(int(len(ratios) * 0.05) - 1, 0)]
    p95 = ratios[min(int(len(ratios) * 0.95), len(ratios) - 1)]
    median = statistics.median(ratios)
    changed = statistics.mean(changed_fractions)
    extreme = max(ratios[-1], 1 / max(ratios[0], 1e-9))
    if worst_overall is None or extreme > worst_overall[1]:
        worst_overall = (seed, extreme)

    label = f"seed {seed}"
    if offenders:
        offenders.sort(key=lambda pair: -abs(math.log(pair[1])))
        fail(f"{label}: {len(offenders)} levels outside "
             f"{WORST_BAND[0]}-{WORST_BAND[1]}x their own HP, worst "
             + ", ".join(f"{lid} {r:.2f}x" for lid, r in offenders[:4]))
    elif not P95_BAND[0] <= p5 or not p95 <= P95_BAND[1]:
        fail(f"{label}: the middle of the distribution drifted -- p5 {p5:.2f}, "
             f"p95 {p95:.2f}, outside {P95_BAND[0]}-{P95_BAND[1]}")
    elif changed < MIN_CHANGED:
        fail(f"{label}: only {changed:.0%} of spawns changed -- the tiers have "
             f"tightened to the point that the option does nothing")
    else:
        ok(f"{label}: HP p5 {p5:.2f} median {median:.2f} p95 {p95:.2f}, "
           f"worst {ratios[0]:.2f}-{ratios[-1]:.2f}x, {changed:.0%} of spawns "
           f"changed ({len(ratios)} levels)")

if worst_overall:
    ok(f"worst level across {len(SEEDS)} seeds is {worst_overall[1]:.2f}x its "
       f"own HP (seed {worst_overall[0]})")

# The regression itself, named. pirate1's roster is 18 basic pirates and a
# handful of armoured ones; the old cost-only tiers turned it into a 27x level.
pirate1 = shufflable.get("pirate1")
if pirate1 is None:
    fail("pirate1 is not in the extract -- regenerate it")
else:
    roster = {z: n for z, n in pirate1["zombies"].items() if z in ZOMBIE_TIER_OF}
    worst = max(weigh(roster, plan_for(seed, "pirate1", roster)) / weigh(roster)
                for seed in SEEDS)
    if worst > 1.35:
        fail(f"pirate1 reaches {worst:.2f}x its own HP -- the first level of a "
             f"world cannot be made half again as hard by a shuffle")
    else:
        ok(f"pirate1, the level this test exists for, stays under {worst:.2f}x "
           f"across {len(SEEDS)} seeds")

print(f"\n{failed} FAILURE(S)" if failed else "\nLEVEL BALANCE OK")
sys.exit(1 if failed else 0)
