"""Generation logic under the budget zombie roll (pvz2gardendless/budget_logic.py).

The roll itself is balance_v2_test.py's
job; this checks what generation builds from it: the zombie-bound entry plants
leave the world entrances, each level carries the counters its own roll asks
for, every counter a rule names is progression and survives the pool floor, the
seed is completable with its own pool, and Universal Tracker rebuilds the same
rules from slot data.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402
from apstub import CollectionState, ItemClassification as IC, MultiWorld  # noqa: E402

import pvz2gardendless as W  # noqa: E402
from pvz2gardendless import budget_logic as B  # noqa: E402
from pvz2gardendless import constants as C  # noqa: E402
from pvz2gardendless import zombie_roll as R  # noqa: E402
from pvz2gardendless.constants import GAME_NAME  # noqa: E402
from pvz2gardendless.items import ITEM_NAME_GROUPS  # noqa: E402
from pvz2gardendless.plant_data import LEVEL_REQUIRED_DPS, PLANT_LAWN_DPS  # noqa: E402
from opts import Opts  # noqa: E402

BUDGET = dict(shuffle_zombies=1, zombie_budget_roll=1, travelling_dinos=1)
EVERY = dict(world_count=13, enabled_worlds=list(C.SELECTABLE_WORLDS),
             include_levels_past_goal=1)
SEEDS = [1, 2, 3, 4]

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


def build(seed=None, passthrough=None, **kw):
    mw = MultiWorld()
    if passthrough is not None:
        mw.re_gen_passthrough = {GAME_NAME: passthrough}
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    if seed is not None:
        w.random = random.Random(seed)
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    return mw, w, w.fill_slot_data()


def reachable(mw, names):
    state = CollectionState(mw, ITEM_NAME_GROUPS)
    for name in names:
        state.collect(name)
    state.sweep()
    return {l.name for l in state.reachable_locations()}


# ── off ──────────────────────────────────────────────────────────────────────
print("\n=== budget roll off ===")
_, w_off, sd_off = build(seed=1, **EVERY)
_, w_tier, sd_tier = build(seed=1, shuffle_zombies=1, **EVERY)
_, w_lone, _ = build(seed=1, zombie_budget_roll=1, **EVERY)
# [user] The budget roll replaced the tier shuffle: shuffle_zombies alone turns
# it on, and the deprecated zombie_budget_roll does nothing by itself.
if w_off.budget_mode or w_lone.budget_mode or not w_tier.budget_mode:
    fail("budget mode does not follow shuffle_zombies alone")
elif B.slot_level_hazard_groups(w_off):
    fail("hazard rules exist outside budget mode")
elif not sd_tier["zombie_budget_roll"]:
    fail("shuffle_zombies seed does not tell the client to use the budget roll")
elif (sd_off["zombie_budget_roll"], sd_off["travelling_dinos"], sd_off["logic_jester_power"]) != (False, False, []):
    fail("slot data claims budget mode with it off")
else:
    ok("shuffle_zombies alone is the budget roll; off and the deprecated option alone keep today's logic")

# ── on ───────────────────────────────────────────────────────────────────────
print("\n=== budget roll on, every world ===")
levels = R.tables().model["levels"]
for seed in SEEDS:
    mw, w, sd = build(seed=seed, **EVERY, **BUDGET)
    label = f"seed {seed}"
    problems = []

    for world in C.ZOMBIE_BOUND_ENTRY_WORLDS:
        if C.slot_entry_groups(w, world):
            problems.append(f"{world} still has an entrance plant")
    if C.slot_entry_groups(w, "Big Wave Beach") != [["Lily Pad"]]:
        problems.append("Big Wave Beach lost Lily Pad")

    rules = B.slot_level_hazard_groups(w)
    opening = B.opening_levels()
    for name, hazards in w.budget_hazards.items():
        groups = rules.get(name, [])
        if "far_future_flyer" in hazards and ["Blover"] not in groups:
            problems.append(f"{name} fields Far Future flyers without a Blover rule")
        if "dino" in hazards and ["Perfume-shroom"] not in groups:
            problems.append(f"{name} fields dinos without a Perfume-shroom rule")
        if "jester" in hazards and sorted(w.logic_jesters) not in groups:
            problems.append(f"{name} fields a Jester without the drawn counter")
        if ("air" in hazards and "far_future_flyer" not in hazards
                and (name in opening) == (["Blover", "Hurrikale"] in groups)):
            problems.append(f"{name}: air rule {'in' if name in opening else 'missing past'} the opening")
        plan = w.budget_plans[name]
        level = levels[name]
        if plan is None and level["generated"] and level["world"] == "dino" and "dino" not in hazards:
            problems.append(f"{name} (generated) lost Jurassic Marsh's dino counter")
        if plan and not level["own_plants"]:
            vanilla = R.hazards({"level": name, "groups": level["groups"], "dynamic": {}, "dinos": []})
            if not hazards <= vanilla:
                problems.append(f"{name} hands the player plants but gained {hazards - vanilla}")
        base = LEVEL_REQUIRED_DPS.get(name)
        if plan and base is not None and not plan["vanilla"]:
            want = min(B.POWER_CEILING, round(base * plan["ratio"] / 1000, 1))
            if B.level_required_dps(w, name) != want:
                problems.append(f"{name} requirement not scaled by its roll")
        need = B.jester_need(w, name) if "jester" in hazards else 0
        if need and not any(PLANT_LAWN_DPS.get(p, 0) >= need for p in w.logic_jesters):
            if not set(w.logic_jester_power) & set(groups[1] if len(groups) > 1 else []):
                problems.append(f"{name} needs Jester class power the draw does not cover")

    progression = {i.name for i in mw.itempool if i.classification == IC.progression}
    progression |= {i.name for i in mw.precollected}
    for plant in B.slot_hazard_plants(w):
        if w.create_item(plant).classification != IC.progression:
            problems.append(f"{plant} is named by a hazard rule but not progression")

    everything = [i.name for i in mw.itempool if i.classification == IC.progression]
    everything += [i.name for i in mw.precollected]
    reach = reachable(mw, everything)
    placed = [l.name for r in mw.regions for l in r.locations]
    stuck = [n for n in placed if n not in reach]
    if stuck:
        problems.append(f"{len(stuck)} locations unreachable with the full pool: {stuck[:5]}")
    sphere1 = len(reachable(mw, [i.name for i in mw.precollected]))

    if len(w.active_locations()) - len(w.goal_locations()) != len(mw.itempool):
        problems.append("the pool does not fill the fillable locations")

    if problems:
        fail(f"{label}: {len(problems)} problems, first {problems[:4]}")
    else:
        ok(f"{label}: {len(rules)} levels carry hazard rules, all reachable with the "
           f"pool, sphere 1 {sphere1}, jester power {list(w.logic_jester_power)}")

# A small seed: the pool floor has to fit every counter Egypt's own rolls ask for.
print("\n=== budget roll on, Ancient Egypt only ===")
for seed in SEEDS:
    mw, w, _ = build(seed=seed, world_count=1, worlds_required=1, **BUDGET)
    everything = [i.name for i in mw.itempool if i.classification == IC.progression]
    everything += [i.name for i in mw.precollected]
    reach = reachable(mw, everything)
    stuck = [l.name for r in mw.regions for l in r.locations if l.name not in reach]
    if stuck:
        fail(f"seed {seed}: Egypt-only budget seed strands {stuck[:5]} "
             f"(floor groups {B.slot_hazard_floor_groups(w)})")
    else:
        ok(f"seed {seed}: Egypt-only budget seed completable, "
           f"{len(mw.itempool)} items, hazard floor {B.slot_hazard_floor_groups(w)}")

# ── travelling dinos off ─────────────────────────────────────────────────────
_, w_nodino, sd_nodino = build(seed=1, **EVERY, shuffle_zombies=1, zombie_budget_roll=1)
if any(plan and plan["dinos"] for plan in w_nodino.budget_plans.values()):
    fail("travelling_dinos off, but a level gained dinos")
elif sd_nodino["travelling_dinos"]:
    fail("slot data says travelling dinos with the option off")
else:
    ok("travelling_dinos off adds no dinos")

# ── granted plants and early placement (step 3b) ─────────────────────────────
print("\n=== granted plants and early placement ===")
from pvz2gardendless.constants import power_draw_groups  # noqa: E402
from pvz2gardendless.items import _pool_floor_groups  # noqa: E402

for seed in SEEDS:
    mw, w, _ = build(seed=seed, starting_plants=10, **EVERY, **BUDGET)
    problems = []
    hardest = B.hardest_requirement(w)
    too_strong = [p for p in w.starting_plants if PLANT_LAWN_DPS.get(p, 0) >= hardest]
    if too_strong:
        problems.append(f"granted plants clear the hardest level ({hardest}): {too_strong}")
    floor = max(B.level_required_dps(w, lv) for lv in C.SPHERE_ONE_LEVELS
                if lv in LEVEL_REQUIRED_DPS)
    if not any(p in C.STARTER_PLANTS and PLANT_LAWN_DPS.get(p, 0) >= floor
               for p in w.starting_plants):
        problems.append(f"no granted starter carries Egypt 1-5 at {floor}")
    power = power_draw_groups(w)
    if power and _pool_floor_groups(w)[-1] != list(power[-1]):
        problems.append("the pool floor still lets a granted plant stand in for power")

    strong = sorted(B.strong_plants(w))
    item = w.create_item(strong[0])
    open_early = [l.name for r in mw.regions
                  if C.is_early_region(r.name) and r.name not in C.SIDE_PATH_REGIONS
                  and r.name != C.SHOP_REGION
                  for l in r.locations
                  if l.item is None and l.name not in C.DANGER_ROOM_LOCATIONS
                  and l.item_rule(item)]
    open_late = [l.name for r in mw.regions if r.name.endswith(" Late")
                 for l in r.locations if l.item is None and l.item_rule(item)]
    if open_early:
        problems.append(f"{strong[0]} may still land early: {open_early[:4]}")
    if not open_late:
        problems.append(f"{strong[0]} has nowhere late to go")
    if problems:
        fail(f"seed {seed}: {problems[:3]}")
    else:
        ok(f"seed {seed}: 10 granted plants all under {hardest} dps, starter carries "
           f"Egypt 1-5 ({floor}), {len(strong)} strong plants kept out of early regions")

# No late region at all: the restriction must stand down rather than strand them.
mw, w, _ = build(seed=1, world_count=1, worlds_required=1, **BUDGET)
item = w.create_item(sorted(B.strong_plants(w))[0])
if not any(l.item is None and l.item_rule(item) for r in mw.regions for l in r.locations):
    fail("Egypt-only world_key budget seed leaves strong plants nowhere to go")
else:
    ok("an Egypt-only world_key budget seed skips the early-region restriction")

# ── sun economy (step 3c) ────────────────────────────────────────────────────
print("\n=== sun economy ===")
from pvz2gardendless.plant_data import SUN_BUDGET  # noqa: E402

drift = [p for p in PLANT_LAWN_DPS if B.lawn_at(p, int(SUN_BUDGET)) != PLANT_LAWN_DPS[p]]
budgets = {n: B.level_sun_budget(n) for n in ("egypt3", "cowboy11", "dark1")}
if drift:
    fail(f"lawn_at at the default budget disagrees with PLANT_LAWN_DPS: {drift[:4]}")
elif budgets != {"egypt3": 1000, "cowboy11": 500, "dark1": 750}:
    fail(f"level sun budgets read wrong: {budgets}")
else:
    ok("default budget prices exactly as PLANT_LAWN_DPS; egypt3 1000, cowboy11 500 "
       "(MaximumSun), dark1 750 (no sky sun)")

for seed in SEEDS:
    mw, w, sd = build(seed=seed, **EVERY, **BUDGET)
    problems = []
    drawn = {b: set(g) for b, g in w.logic_budget_power}
    for loc in w.active_locations():
        need = B.power_need(w, loc.name)
        if not need:
            continue
        required, budget = need
        clearing = set(B.plants_clearing_at(required, budget))
        if not clearing:
            problems.append(f"{loc.name}: nothing clears {required} at {budget} sun")
        elif budget < SUN_BUDGET and not clearing & drawn.get(budget, set()):
            problems.append(f"{loc.name}: no drawn power plant clears it at {budget} sun")
        for group, promoted in B.level_hazard_groups(w, loc.name):
            if promoted and group != sorted(w.logic_jesters) and all(
                    B.sun_cost(p) > budget for p in group):
                problems.append(f"{loc.name}: no counter in {group} fits {budget} sun")
        if B._jester_short(w, loc.name) and not any(
                B.lawn_at(p, budget) >= B.jester_need(w, loc.name) for p in w.logic_jester_power):
            problems.append(f"{loc.name}: Jester class need not covered by the power draw")
    for plant in {p for _, g in w.logic_budget_power for p in g}:
        if w.create_item(plant).classification != IC.progression:
            problems.append(f"budget power plant {plant} is not progression")
    if problems:
        fail(f"seed {seed}: {len(problems)} problems, first {problems[:3]}")
    else:
        ok(f"seed {seed}: budget power draws {[(b, list(g)) for b, g in w.logic_budget_power]}, "
           f"every reduced-budget level covered, counters affordable")

# ── Universal Tracker ────────────────────────────────────────────────────────
print("\n=== Universal Tracker ===")
_, server, sd = build(seed=11, **EVERY, **BUDGET)
_, tracked, _ = build(seed=12, passthrough=sd, **EVERY)
if not tracked.budget_mode:
    fail("the tracker, run without the YAML, did not enter budget mode from slot data")
elif tracked.budget_hazards != server.budget_hazards:
    fail("the tracker rolled different hazards")
elif B.slot_level_hazard_groups(tracked) != B.slot_level_hazard_groups(server):
    fail("the tracker built different hazard rules")
elif tracked.logic_jester_power != server.logic_jester_power:
    fail("the tracker drew a different Jester power plant")
elif tracked.logic_budget_power != server.logic_budget_power:
    fail("the tracker drew different per-budget power plants")
else:
    ok("the tracker rebuilds the seed's hazards and rules from slot data alone")

print(f"\n{failed} FAILURE(S)" if failed else "\nBUDGET LOGIC OK")
sys.exit(1 if failed else 0)
