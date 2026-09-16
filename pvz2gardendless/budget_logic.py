"""
PvZ2 Gardendless: generation logic for the budget zombie roll.

Active whenever shuffle_zombies is on (zombie_budget_roll is deprecated). generate_early calls compute(), which rolls every
built level from zombie_seed exactly as the client will, and records each
level's plan and hazards. Everything else reads those through the helpers here,
so the access rules, the progression promote and the item-pool floor cannot
disagree about what a level asks for.

What changes under budget mode:

  * A level's power requirement is its LEVEL_REQUIRED_DPS scaled by the roll's
    HP ratio, clamped to the same ceiling the table is.
  * The zombie-bound world entry plants (Dark Ages' Jester counter, Far Future's
    Blover, Jurassic Marsh's Perfume-shroom) come off the world entrances and go
    onto each level that actually fields the hazard. World-bound requirements
    (sun, Lily Pad, Frostbite warmth, Grave Buster) are untouched.
  * Hazards per level: Jester -> the slot's drawn counter, plus enough power
    inside the counter class for the Jesters' share of the level's HP; ice-block
    carriers -> a warming plant; Far Future flyers -> Blover; other flyers ->
    Blover or Hurrikale, only past the world's opening stretch; dinos ->
    Perfume-shroom.
  * Levels the roll never touches (bespoke) keep their vanilla hazards.
    Runtime-generated levels (danger rooms and the _1 challenges) have no static
    roster, so they keep their world's old zombie-bound counter.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from . import zombie_roll
from .constants import (EGYPT_SUN_CUT, FIRE_AURA_PLANTS, JESTER_COUNTER_PLANTS,
                        POWER_DRAW_COUNT, SIDE_PATH_CHAIN, SIDE_PATH_REGIONS,
                        SIDE_PATH_UNLOCK, SPHERE_ONE_LEVELS, STARTER_PLANTS,
                        UNREACHABLE_LOCATIONS, WORLD_REGIONS, plants_clearing)
from .locations import ALL_LOCATIONS, world_stretches
from .plant_data import (ANSWER_FLOOR, CONSUMABLE_COPIES, DRAW_RUNGS, LEVEL_REQUIRED_DPS,
                         MAX_COPIES, PLANT_CONSUMABLE, PLANT_DPS, PLANT_LAWN_DPS,
                         PLANT_SUN_COST, SUN_BUDGET)

BLOVER = ["Blover"]
AIR_COUNTERS = ["Blover", "Hurrikale"]
DINO_COUNTERS = ["Perfume-shroom"]

# A runtime-generated level has no static roster to read hazards from, so it
# keeps the counter its world asked for before the budget roll existed.
GENERATED_WORLD_HAZARD = {"dark": "jester", "future": "far_future_flyer", "dino": "dino"}

# The ceiling LEVEL_REQUIRED_DPS is already clamped to (the 12th best plant).
POWER_CEILING = max(LEVEL_REQUIRED_DPS.values())


def enabled(world) -> bool:
    options = world.options
    # [user] The budget roll replaced the tier shuffle: zombie_budget_roll is
    # deprecated and ignored.
    return bool(options.shuffle_zombies)


# ── sun economy (step 3c) ────────────────────────────────────────────────────

# [user] A level's sun budget: SUN_BUDGET by default, these when the level has
# no sky sun or bans sun producers (the lower if both), then clamped to the
# level's MaximumSun challenge cap.
BUDGET_NO_SKY_SUN = 750
BUDGET_NO_PRODUCERS = 500

_CONSUMABLE = frozenset(PLANT_CONSUMABLE)
_CEILING_AT: Dict[int, float] = {}


def level_sun_budget(name: str) -> int:
    level = zombie_roll.tables().model["levels"].get(name)
    budget = int(SUN_BUDGET)
    if not level:
        return budget
    sun = level.get("sun") or {}
    if not sun.get("sky", True):
        budget = min(budget, BUDGET_NO_SKY_SUN)
    if sun.get("no_producers"):
        budget = min(budget, BUDGET_NO_PRODUCERS)
    if sun.get("max_sun"):
        budget = min(budget, sun["max_sun"])
    return budget


def sun_cost(plant: str) -> int:
    return PLANT_SUN_COST.get(plant) or 0


def lawn_at(plant: str, budget: int) -> float:
    """A plant's lawn dps when the level gives `budget` sun.

    At the default budget this IS PLANT_LAWN_DPS. Below it the copy count is
    re-priced the way the generator prices it (min(MAX_COPIES, budget // sun),
    a consumable one copy), and a plant the budget cannot buy once does nothing.
    """
    if plant not in PLANT_LAWN_DPS:
        return 0.0
    if budget >= SUN_BUDGET:
        return PLANT_LAWN_DPS[plant]
    cost = sun_cost(plant) or 25
    if cost > budget:
        return 0.0
    copies = CONSUMABLE_COPIES if plant in _CONSUMABLE else max(1, min(MAX_COPIES, budget // cost))
    return round(PLANT_DPS[plant] * copies, 1)


def plants_clearing_at(required: float, budget: int) -> Tuple[str, ...]:
    """plants_clearing, priced at a level's sun budget."""
    if budget >= SUN_BUDGET:
        return plants_clearing(required)
    return tuple(sorted(p for p in PLANT_LAWN_DPS if lawn_at(p, budget) >= required))


def ceiling_at(budget: int) -> float:
    """The ANSWER_FLOOR-th best lawn dps at this budget: no level asks for more."""
    if budget not in _CEILING_AT:
        ladder = sorted((lawn_at(p, budget) for p in PLANT_LAWN_DPS), reverse=True)
        _CEILING_AT[budget] = ladder[min(ANSWER_FLOOR, len(ladder)) - 1]
    return _CEILING_AT[budget]


def affordable(group, budget: int) -> List[str]:
    """The members one copy of which fits the budget; the whole group if none do."""
    fits = [p for p in group if sun_cost(p) <= budget]
    return fits or list(group)


# ── where a level sits ───────────────────────────────────────────────────────

_OPENING: Optional[Set[str]] = None


def opening_levels() -> Set[str]:
    """Level names before (or at) their world's World Key level.

    Ancient Egypt's opening includes its " Early" checkpoint, which is still
    before egypt8. A side path takes the answer of the level that reveals it
    (following Hot Date's chain); a worldless side path counts as opening.
    """
    global _OPENING
    if _OPENING is not None:
        return _OPENING
    opening: Set[str] = set()
    for world, regions in WORLD_REGIONS.items():
        names = [l.name for l in ALL_LOCATIONS
                 if l.region in regions and l.name not in UNREACHABLE_LOCATIONS]
        parts = world_stretches(names, EGYPT_SUN_CUT if world == "Ancient Egypt" else None)
        opening.update(parts[0])
        if world == "Ancient Egypt":
            opening.update(parts[1])
    for loc in ALL_LOCATIONS:
        if loc.region not in SIDE_PATH_REGIONS:
            continue
        region, seen = loc.region, set()
        while region in SIDE_PATH_CHAIN and region not in seen:
            seen.add(region)
            region = SIDE_PATH_CHAIN[region]
        unlock = SIDE_PATH_UNLOCK.get(region)
        if unlock is None or unlock in opening:
            opening.add(loc.name)
    _OPENING = opening
    return opening


# ── rolling the slot ─────────────────────────────────────────────────────────

def _vanilla_plan(level_id: str) -> Dict[str, Any]:
    level = zombie_roll.tables().model["levels"][level_id]
    return {"level": level_id, "vanilla": True, "ratio": 1000,
            "groups": level["groups"], "dynamic": {}, "dinos": []}


def compute(world) -> None:
    """Roll every built level and record plans and hazards on the world."""
    world.budget_mode = enabled(world)
    world.budget_plans, world.budget_hazards = {}, {}
    if not world.budget_mode:
        return
    levels = zombie_roll.tables().model["levels"]
    goal = world.options.goal_type.value
    dinos = bool(getattr(world.options, "travelling_dinos", 0))
    for loc in world.active_locations():
        level = levels.get(loc.name)
        if level is None:
            continue
        plan = zombie_roll.roll_level(world.zombie_seed, loc.name, dinos, goal)
        if plan is not None:
            hazards = zombie_roll.hazards(plan)
        elif level["generated"]:
            hazard = GENERATED_WORLD_HAZARD.get(level["world"])
            hazards = {hazard} if hazard else set()
        else:
            hazards = zombie_roll.hazards(_vanilla_plan(loc.name))
        world.budget_plans[loc.name] = plan
        world.budget_hazards[loc.name] = hazards


def level_required_dps(world, name: str) -> Optional[float]:
    """The level's power requirement, scaled by its roll under budget mode."""
    base = LEVEL_REQUIRED_DPS.get(name)
    if base is None:
        return None
    plan = getattr(world, "budget_plans", {}).get(name)
    if not plan or plan["vanilla"]:
        return base
    return min(POWER_CEILING, round(base * plan["ratio"] / 1000, 1))


def power_need(world, name: str) -> Optional[Tuple[float, int]]:
    """(required lawn dps, sun budget) for a level's power rule, or None.

    Outside budget mode this is (LEVEL_REQUIRED_DPS, SUN_BUDGET), which prices
    exactly as the rule always has. Under it, the requirement is scaled by the
    roll and clamped to what the level's budget can field.
    """
    required = level_required_dps(world, name)
    if required is None:
        return None
    if not getattr(world, "budget_mode", False):
        return required, int(SUN_BUDGET)
    budget = level_sun_budget(name)
    if budget < SUN_BUDGET:
        required = min(required, ceiling_at(budget))
    return required, budget


def power_rule_plants(world) -> Set[str]:
    """Every plant some power rule this slot built names, for the promote.

    AP only counts advancement items in CollectionState, so a plant the rule
    names but that stays useful never satisfies it: logic (and Universal
    Tracker) would ignore a player holding it. Mirrors rules.py's gate, which
    builds power rules only when the ladder was drawn.
    """
    if not getattr(world, "logic_power_plants", ()):
        return set()
    needs = {power_need(world, loc.name) for loc in world.active_locations()}
    needs.discard(None)
    return {p for need in needs for p in plants_clearing_at(*need)}


def draw_budget_power(world) -> Tuple[Tuple[int, Tuple[str, ...]], ...]:
    """Power plants for the levels priced below SUN_BUDGET, one draw per budget.

    The ladder (draw_power_plants) is priced at the default budget, so a plant
    it drew may not clear a 500-sun level. Each lower budget this slot builds
    gets POWER_DRAW_COUNT plants that clear its hardest level at that budget,
    promoted and floored like a rung. () outside budget mode or with
    plant_power_logic off.
    """
    if not getattr(world, "budget_mode", False) or not world.options.plant_power_logic:
        return ()
    needs: Dict[int, float] = {}
    for loc in world.active_locations():
        need = power_need(world, loc.name)
        if need and need[1] < SUN_BUDGET:
            needs[need[1]] = max(needs.get(need[1], 0.0), need[0])
    out = []
    for budget in sorted(needs, reverse=True):
        candidates = plants_clearing_at(needs[budget], budget)
        if candidates:
            count = min(POWER_DRAW_COUNT, len(candidates))
            out.append((budget, tuple(sorted(world.random.sample(candidates, count)))))
    return tuple(out)


def jester_draw_pool(world) -> List[str]:
    """The Jester counters the slot's one drawn counter may come from.

    Outside budget mode, all of them (the draw is unchanged). Under it, only the
    counters one copy of which fits the cheapest Jester level's budget, so the
    one plant the rule names is always affordable where it is asked for.
    """
    if not getattr(world, "budget_mode", False):
        return JESTER_COUNTER_PLANTS
    budgets = [level_sun_budget(n) for n, hz in world.budget_hazards.items() if "jester" in hz]
    if not budgets:
        return JESTER_COUNTER_PLANTS
    return [p for p in JESTER_COUNTER_PLANTS if sun_cost(p) <= min(budgets)] or JESTER_COUNTER_PLANTS


def jester_need(world, name: str) -> float:
    """Lawn dps the Jester counter class must reach in this level.

    The level's requirement times the Jesters' share of its static HP: one
    Jester among twenty zombies asks almost nothing of the class, a lawn of
    Jesters asks nearly the whole requirement. Clamped to the best counter.
    """
    required = level_required_dps(world, name)
    if not required:
        return 0.0
    plan = world.budget_plans.get(name) or _vanilla_plan(name)
    t = zombie_roll.tables()
    total = jesters = 0
    for codename, count in zombie_roll.roster(plan).items():
        hp = t.hp.get(codename, 0) * count
        total += hp
        if "-jester" in t.tier.get(codename, ""):
            jesters += hp
    if not total or not jesters:
        return 0.0
    budget = level_sun_budget(name)
    best = max(lawn_at(p, budget) for p in JESTER_COUNTER_PLANTS)
    return min(best, round(required * jesters / total, 1))


def _jester_short(world, name: str) -> float:
    """The level's Jester class need when the drawn counter falls short, else 0."""
    need = jester_need(world, name)
    budget = level_sun_budget(name)
    if not need or any(lawn_at(p, budget) >= need for p in world.logic_jesters):
        return 0.0
    return need


def draw_jester_power(world, exclude=()) -> Tuple[str, ...]:
    """Jester counters that cover every level the drawn counter falls short in.

    A greedy cover, each pick the counter clearing the most still-uncovered
    levels at their own sun budgets (ties drawn from world.random), so a 500-sun
    Jester level cannot be left needing a plant it cannot afford. () when the
    drawn counter covers everything. Never a plant in `exclude` (the starter,
    which is granted), for the same reason the drawn counter never is.
    """
    if not getattr(world, "budget_mode", False):
        return ()
    short = [(n, need, level_sun_budget(n)) for n, hz in sorted(world.budget_hazards.items())
             if "jester" in hz for need in [_jester_short(world, n)] if need]
    chosen: List[str] = []
    while short:
        cover = {p: sum(1 for _, need, b in short if lawn_at(p, b) >= need)
                 for p in JESTER_COUNTER_PLANTS if p not in exclude}
        best = max(cover.values(), default=0)
        if not best:
            break
        pick = world.random.choice(sorted(p for p, c in cover.items() if c == best))
        chosen.append(pick)
        short = [s for s in short if lawn_at(pick, s[2]) < s[1]]
    return tuple(sorted(chosen))


# ── what the client needs (phase 4) ──────────────────────────────────────────

def client_tables(world) -> Dict[str, Any]:
    """The zombie_budget slot_data table: what the client's roll is built from.

    The client re-derives each level's model from the live level objects, but
    the per-zombie table and the count-field names come from every level in the
    game, so they are sent (data the client needs is sent, not duplicated).
    Zombies as [hp, cost, tier, excluded, carry, multilane, nullifier]; see the
    client's _apbTables. A client reading a seed rolled before one of the
    trailing flags existed sees a shorter entry and falls back to what that roll
    assumed: every zombie able to carry plant food, none of them multi-lane, and
    none of them kept out of the opening levels as a nullifier.
    """
    t = zombie_roll.tables()
    return {
        "zombies": {c: [z["hp"], z["cost"], z["tier"], z["excluded"] or "",
                        1 if z.get("carry", True) else 0,
                        1 if z.get("multilane") else 0,
                        1 if c in t.nullifier_names else 0]
                    for c, z in sorted(t.zombies.items())},
        "grave_hp": dict(sorted(t.model["grave_hp"].items())),
        "field_names": {k: sorted(v) for k, v in t.field_names.items()},
        "goal": world.options.goal_type.value,
        "dinos": bool(getattr(world.options, "travelling_dinos", 0)),
    }


# ── granted plants and early placement (step 3b) ─────────────────────────────

def hardest_requirement(world) -> float:
    """The highest power requirement among the levels this slot builds."""
    return max((level_required_dps(world, loc.name) for loc in world.active_locations()
                if loc.name in LEVEL_REQUIRED_DPS), default=0.0)


def starter_candidates(world) -> List[str]:
    """STARTER_PLANTS a budget-mode slot may start with.

    [user] The starter must never clear every level: its lawn dps stays below
    the hardest requirement this slot builds. It must still carry Egypt 1-5,
    whose requirements the roll scales, so the floor is re-read from them.
    Falls back rather than emptying the draw, which nothing downstream allows.
    """
    if not getattr(world, "budget_mode", False):
        return STARTER_PLANTS
    floor = max((level_required_dps(world, lv) for lv in SPHERE_ONE_LEVELS
                 if lv in LEVEL_REQUIRED_DPS), default=0.0)
    hardest = hardest_requirement(world)
    capped = [p for p in STARTER_PLANTS if PLANT_LAWN_DPS.get(p, 0.0) < hardest]
    return [p for p in capped if PLANT_LAWN_DPS.get(p, 0.0) >= floor] or capped or STARTER_PLANTS


def clears_every_level(world, plant: str) -> bool:
    """A budget-mode slot may not grant this plant: it clears the hardest level."""
    if not getattr(world, "budget_mode", False):
        return False
    hardest = hardest_requirement(world)
    return bool(hardest) and PLANT_LAWN_DPS.get(plant, 0.0) >= hardest


def strong_plants(world) -> Set[str]:
    """[user] Plants kept out of early regions: those clearing the top draw rung."""
    if not getattr(world, "budget_mode", False):
        return set()
    return set(plants_clearing(DRAW_RUNGS[-1]))


# ── what each level asks ─────────────────────────────────────────────────────

def level_hazard_groups(world, name: str) -> List[Tuple[List[str], bool]]:
    """(plant group, promoted) per requirement this level's hazards add.

    `promoted` is False only for the Jester class-power group, which names every
    counter strong enough while only logic_jester_power is progression (the same
    wide-rule, narrow-promote split the power ladder uses).
    """
    hazards = getattr(world, "budget_hazards", {}).get(name, ())
    budget = level_sun_budget(name)
    groups: List[Tuple[List[str], bool]] = []
    if "jester" in hazards:
        groups.append((sorted(world.logic_jesters), True))
        need = _jester_short(world, name)
        if need:
            groups.append((sorted(p for p in JESTER_COUNTER_PLANTS
                                  if lawn_at(p, budget) >= need), False))
    # [user] A counter only counts if the level's sun budget can buy one.
    if "iceblock" in hazards:
        groups.append((affordable(FIRE_AURA_PLANTS, budget), True))
    if "far_future_flyer" in hazards:
        groups.append((list(BLOVER), True))
    elif "air" in hazards and name not in opening_levels():
        groups.append((affordable(AIR_COUNTERS, budget), True))
    if "dino" in hazards:
        groups.append((list(DINO_COUNTERS), True))
    # [user] Narrowed to the slot's power selection (power_logic.select), like
    # the loadout rules, so a counter group promotes the plants the seed chose
    # rather than every member.
    from . import power_logic
    return [(power_logic.narrow(world, g), promoted) for g, promoted in groups]


def slot_level_hazard_groups(world) -> Dict[str, List[List[str]]]:
    """{level name: [plant group, ...]} for every built level with a hazard rule."""
    out = {}
    for name in sorted(getattr(world, "budget_hazards", {})):
        groups = [g for g, _ in level_hazard_groups(world, name)]
        if groups:
            out[name] = groups
    return out


def slot_hazard_floor_groups(world) -> List[List[str]]:
    """Distinct groups the item-pool floor must cover, one plant each."""
    seen, out = set(), []
    for name in sorted(getattr(world, "budget_hazards", {})):
        for group, promoted in level_hazard_groups(world, name):
            if not promoted:
                continue  # covered by the jester power plants below
            key = tuple(sorted(group))
            if key and key not in seen:
                seen.add(key)
                out.append(sorted(group))
    # Each jester power plant covers levels the others do not, so each is its
    # own group rather than one group the floor could satisfy with any one.
    for plant in (() if getattr(world, "power_selection", None) is not None
                  else getattr(world, "logic_jester_power", ())):
        if (plant,) not in seen:
            seen.add((plant,))
            out.append([plant])
    return out


def slot_hazard_plants(world) -> Set[str]:
    """Plants the hazard rules promote to progression for this slot."""
    plants: Set[str] = set()
    for group in slot_hazard_floor_groups(world):
        plants.update(group)
    if getattr(world, "power_selection", None) is None:
        plants.update(getattr(world, "logic_jester_power", ()))
    # ...and the Jester class-power groups themselves: a rule names every
    # member, so every member has to be progression to count.
    for name in sorted(getattr(world, "budget_hazards", {})):
        for group, promoted in level_hazard_groups(world, name):
            if not promoted:
                plants.update(group)
    return plants
