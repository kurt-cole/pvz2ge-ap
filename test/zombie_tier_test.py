"""The zombie swap tiers still partition what they claim to partition.

zombie_data.py is generated (tools/gen_zombie_tiers.py) from the game's own
data, so this is not checking arithmetic -- it is checking that the generated
table still HOLDS the properties the option's promises rest on, after any
regeneration against a new game build:

  * a swap never leaves its tier, so every axis of the key is an invariant;
  * a threat mechanic can neither be created nor destroyed, which is what lets
    shuffle_zombies ship without a single new access rule;
  * no tier spans more than one HP band, which is what keeps a level's
    difficulty roughly where the level put it;
  * the exclusions still name the families they were added for.

If one of these fails after a regeneration, the answer is a game-data change
worth understanding, not a looser assertion.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
# Importing the package runs its __init__, which imports Archipelago. apstub is
# what stands in for that offline; every Python suite here starts this way.
import apstub  # noqa: E402,F401

from pvz2gardendless.zombie_data import (  # noqa: E402
    HP_BAND, THREAT_TAGS, ZOMBIE_EXCLUSIONS, ZOMBIE_HP, ZOMBIE_TIERS,
    ZOMBIE_TIER_OF, swap_pool, tier_of,
)

EXTRACT = os.path.join(HERE, "data", "zombie_balance.json")

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


def tags_of(tier):
    return {tag for tag in THREAT_TAGS if f"-{tag}" in tier}


# ── the table is well formed ─────────────────────────────────────────────────

members = [z for zs in ZOMBIE_TIERS.values() for z in zs]
if len(members) != len(set(members)):
    fail("a zombie appears in more than one tier")
else:
    ok(f"{len(members)} zombies over {len(ZOMBIE_TIERS)} tiers, none listed twice")

missing_hp = sorted(z for z in members if z not in ZOMBIE_HP)
if missing_hp:
    fail(f"{len(missing_hp)} tiered zombies have no HP for the client's budget "
         f"guard to weigh, e.g. {missing_hp[:5]}")
else:
    ok(f"every tiered zombie has an effective HP ({len(ZOMBIE_HP)} entries)")

stray_hp = sorted(z for z in ZOMBIE_HP if z not in ZOMBIE_TIER_OF)
if stray_hp:
    fail(f"HP is sent for {len(stray_hp)} zombies that can never be swapped: "
         f"{stray_hp[:5]}")
else:
    ok("the HP table covers the tiered zombies and nobody else")

# A tier of one never swaps, which is fine, but the table should not be mostly
# those -- that would be the option quietly doing nothing.
swappable = sum(len(zs) for zs in ZOMBIE_TIERS.values() if len(zs) > 1)
if swappable * 100 // len(members) < 70:
    fail(f"only {swappable} of {len(members)} zombies have anybody to trade "
         f"with -- the tiers have fragmented")
else:
    ok(f"{swappable} of {len(members)} zombies ({swappable * 100 // len(members)}%) "
       f"have somebody to trade with")

# ── no tier spans more than one HP band ──────────────────────────────────────

worst, worst_tier = 1.0, None
for tier, zs in ZOMBIE_TIERS.items():
    hps = [ZOMBIE_HP[z] for z in zs]
    ratio = max(hps) / max(min(hps), 1)
    if ratio > worst:
        worst, worst_tier = ratio, tier
if worst > HP_BAND:
    fail(f"{worst_tier} spans {worst:.2f}x in HP, wider than the {HP_BAND} band "
         f"the tiers are cut on")
else:
    ok(f"no tier spans more than {worst:.2f}x in HP (band is {HP_BAND})")

# ── a swap never leaves its tier, on any axis ────────────────────────────────

leaks = []
for zombie, tier in ZOMBIE_TIER_OF.items():
    for other in swap_pool(zombie):
        if ZOMBIE_TIER_OF[other] != tier:
            leaks.append(f"{zombie} -> {other}")
if leaks:
    fail(f"{len(leaks)} swaps leave their tier, e.g. {leaks[:3]}")
else:
    ok("every swap a zombie may make stays inside its own tier")

# The whole reason the option needs no new access rule: a mechanic that needs a
# specific plant to answer it can neither appear in a world that had none nor
# vanish from a world whose rule is built on it.
mixed = []
for tier, zs in ZOMBIE_TIERS.items():
    tags = tags_of(tier)
    for zombie in zs:
        for other in swap_pool(zombie):
            if tags_of(ZOMBIE_TIER_OF[other]) != tags:
                mixed.append(f"{zombie}{sorted(tags)} -> {other}")
if mixed:
    fail(f"{len(mixed)} swaps change a threat mechanic, e.g. {mixed[:3]}")
else:
    tagged = sum(len(zs) for tier, zs in ZOMBIE_TIERS.items() if tags_of(tier))
    ok(f"threat mechanics are conserved: {tagged} tagged zombies "
       f"({', '.join(THREAT_TAGS)}) only ever trade with their own kind")

# Water and land are the same argument in a different lane: a land zombie
# dropped in a deep-water lane drowns.
crossed = [f"{z} -> {o}" for z, t in ZOMBIE_TIER_OF.items()
           for o in swap_pool(z)
           if ("water" in t) != ("water" in ZOMBIE_TIER_OF[o])]
if crossed:
    fail(f"{len(crossed)} swaps cross land and water, e.g. {crossed[:3]}")
else:
    ok("land and water zombies never trade with each other")

gargs = [f"{z} -> {o}" for z, t in ZOMBIE_TIER_OF.items()
         for o in swap_pool(z)
         if ("garg" in t) != ("garg" in ZOMBIE_TIER_OF[o])]
if gargs:
    fail(f"{len(gargs)} swaps turn a Gargantuar into something else, e.g. {gargs[:3]}")
else:
    ok("a Gargantuar only ever becomes another Gargantuar")

# ── the exclusions still name what they were added for ───────────────────────

# Each of these was found the hard way. A regeneration that drops one of them
# from the table has to be understood, not accepted: they are why pirate1 no
# longer fields eighteen 10000 HP shields.
for reason, expect in (("camel", "camel_onehump"),
                       ("immobile", "sky_dropship"),
                       ("ignored_in_waves", "egypt_imp"),
                       ("skycity", "sky_arbiterx")):
    names = ZOMBIE_EXCLUSIONS.get(reason, [])
    if expect not in names:
        fail(f"{expect} is no longer excluded as {reason} -- it can now be "
             f"swapped in anywhere")
    elif tier_of(expect):
        fail(f"{expect} is excluded as {reason} but also sits in a tier")
if not failed:
    excluded = sum(len(v) for v in ZOMBIE_EXCLUSIONS.values())
    ok(f"{excluded} codenames stay out of the table "
       f"({', '.join(sorted(ZOMBIE_EXCLUSIONS))})")

overlap = sorted(set(ZOMBIE_TIER_OF) &
                 {z for zs in ZOMBIE_EXCLUSIONS.values() for z in zs})
if overlap:
    fail(f"{len(overlap)} codenames are both tiered and excluded: {overlap[:5]}")
else:
    ok("nothing is both tiered and excluded")

# ── the generated table agrees with the extract the balance test replays ─────

with open(EXTRACT, encoding="utf8") as fh:
    extract = json.load(fh)

if not math.isclose(extract["hp_band"], HP_BAND):
    fail(f"the extract was generated at HP band {extract['hp_band']}, the table "
         f"at {HP_BAND} -- rerun tools/gen_zombie_tiers.py")
else:
    ok(f"the balance extract was generated from the same table (band {HP_BAND})")

mismatch = [z for z, hp in ZOMBIE_HP.items()
            if z in extract["zombies"] and extract["zombies"][z]["hp"] != hp]
if mismatch:
    fail(f"{len(mismatch)} zombies weigh something different in the extract, "
         f"e.g. {mismatch[:3]}")
else:
    ok(f"every tiered zombie weighs the same in both files")

print(f"\n{failed} FAILURE(S)" if failed else "\nZOMBIE TIERS OK")
sys.exit(1 if failed else 0)
