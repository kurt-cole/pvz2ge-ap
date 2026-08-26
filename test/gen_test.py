import sys, os, collections

# This directory (for apstub) and the repo root (for the pvz2gardendless
# package), resolved off __file__ so the suite runs from any working dir.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))
import apstub
from apstub import MultiWorld

import pvz2gardendless as W
from pvz2gardendless import constants as C
from pvz2gardendless.options import (
    WorldCount, EnabledWorlds, GoalType, WorldsRequired, ModernDayVictory,
    SkipTutorial, Shopsanity, TrapPercentage, ShuffleUpgrades,
    RandomizeConveyorPlants, EarlyWorldKeys, ShuffleZombies, IncludeSidePaths,
    IncludeDangerRooms,
    StartingPlants,
    TrapWeightLawnMower, TrapWeightCostumeShuffle, TrapWeightCoins,
    TrapWeightGems, IncludeLevelsPastGoal,
)
from apstub import DeathLink


# The options object itself now lives in opts.py, so tracker_test.py can build
# seeds without importing this suite (and running it) to reach it.
from opts import Opts



# The default seed is ELEVEN worlds (Kongfu Temple and Aerial Fortress are out
# by default), so a test that means "every world" has to say so. Both keys
# are needed: world_count is a hard cap and enabled_worlds is what fills it.
# "the whole game": every world AND every level. include_levels_past_goal is
# part of it as of 2026-08-25 -- the default goal trims each world at its World
# Key level, so a test that walks all 31 side paths or all 34 shop cards has to
# ask for the untrimmed game explicitly.
_EVERY_WORLD = {"world_count": 13, "enabled_worlds": list(C.SELECTABLE_WORLDS)}
ALL_WORLDS = dict(_EVERY_WORLD, include_levels_past_goal=1)


def run(label, **kw):
    mw = MultiWorld()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    sd = w.fill_slot_data()

    locs = w.active_locations()
    from pvz2gardendless.items import PLANT_ITEMS as _PLANTS_ALL
    keys = [i.name for i in mw.itempool if i.name.endswith(" Key")]
    unlocks = [i.name for i in mw.itempool if i.name.startswith("Progressive ")
               and i.name[len("Progressive "):] in C.WORLD_REGIONS]
    built = {r.name for r in mw.regions}
    dead = {r for r in C.ALL_WORLD_REGIONS if r not in w.enabled_regions}

    print(f"\n=== {label} ===")
    print(f"  worlds({len(w.enabled_worlds)}): {sorted(w.enabled_worlds)}")
    print(f"  locations={len(locs)}  itempool={len(mw.itempool)}  "
          f"keys={len(keys)}  unlocks={len(unlocks)}")
    print(f"  goal_type={sd['goal_type']} worlds_required={sd['worlds_required']}"
          f" goal_locations={len(sd['goal_locations'])}")
    # Every goal level carries a locked McGuffin, so those locations are not
    # fillable and the pool must be exactly that much shorter. A pool sized to
    # the raw location count would hand fill more items than places.
    goal_locs = sd["goal_locations"]
    assert len(locs) - len(goal_locs) == len(mw.itempool),         (f"pool must exactly fill the fillable locations: {len(locs)} locations "
         f"- {len(goal_locs)} goal levels != {len(mw.itempool)} items")
    # ...and one McGuffin per goal level actually got there, all of them the
    # single name this goal type ships.
    placed = [l for r in mw.regions for l in r.locations
              if l.item and l.item.name == sd["goal_item"]]
    assert len(placed) == len(goal_locs),         f"{len(placed)} {sd['goal_item']}s placed for {len(goal_locs)} goal levels"
    assert {l.name for l in placed} == set(goal_locs),         "McGuffins are not on the goal levels"
    assert sd["worlds_required"] <= len(goal_locs),         "more McGuffins required than the seed contains"
    assert not (built & dead), f"built a disabled region: {built & dead}"
    # every location built lands in a region that exists
    for loc in locs:
        assert loc.region in built, f"{loc.name} -> missing region {loc.region}"
    # World Keys are gone from the pool entirely: the first of a world's
    # progressive unlocks is what opens it now. The item definitions stay so
    # item IDs do not move, which is why this checks the POOL and not the
    # tables.
    assert not keys, f"World Key items are still being placed: {keys}"

    # Three unlocks per world, or two for Ancient Egypt, which needs none to
    # enter. Counted per world rather than in total, so a world shipping the
    # wrong number cannot be hidden by another shipping one too many.
    from collections import Counter
    _by_world = Counter(u[len("Progressive "):] for u in unlocks)
    _gt = w.options.goal_type.value
    _pg = bool(w.options.include_levels_past_goal)
    # A world whose count is 0 ships nothing and so does not appear at all.
    # Ancient Egypt under the world_key goal is exactly that: its opening and
    # its egypt6 checkpoint both need no unlock, so a seed ending at egypt8
    # ships none for it.
    _want_worlds = {_wn for _wn in w.enabled_worlds
                    if C.progressive_count(_wn, _gt, _pg)}
    assert set(_by_world) == _want_worlds, (
        f"unlocks for worlds not in the seed: {sorted(set(_by_world) - _want_worlds)}, "
        f"missing: {sorted(_want_worlds - set(_by_world))}")
    for _wn, _n in _by_world.items():
        assert _n == C.progressive_count(_wn, _gt, _pg), (
            f"{_wn} ships {_n} unlocks, "
            f"expected {C.progressive_count(_wn, _gt, _pg)}")
    # The untrimmed shape, pinned as literals: two for Ancient Egypt because it
    # needs none to enter, three for a keyed world.
    if _pg or _gt == C.GOAL_COMPLETION:
        assert _by_world["Ancient Egypt"] == 2, "Ancient Egypt needs no unlock to enter"
        if "Wild West" in w.enabled_worlds:
            assert _by_world["Wild West"] == 3, "a keyed world ships three unlocks"
    # goal locations all exist and are reachable-by-name
    for name in sd["goal_locations"]:
        mw.get_location(name, 1)
    # the free starting plant must be able to hold a lane: no single-use
    # instants, no non-damaging support
    from pvz2gardendless.constants import (STARTER_PLANTS, SINGLE_USE_PLANTS,
                                           NON_DAMAGING_PLANTS,
                                           SUN_PRODUCER_PLANTS)
    # As many starting plants as the option asked for, and exactly one of them
    # is the lane-holding cheap attacker the guarantee is about. The others are
    # extras and are checked in the starting_plants block further down.
    assert len(mw.precollected) == w.options.starting_plants.value, \
        f"{len(mw.precollected)} starting plants, expected {w.options.starting_plants.value}"
    _starters = [i.name for i in mw.precollected if i.name in set(STARTER_PLANTS)]
    assert _starters, "no lane-holding starting plant was granted"
    starter = w.starting_plants[0] if len(mw.precollected) == 1 else _starters[0]
    # The sun producer is guaranteed STRUCTURALLY, not requested. Nothing is
    # nudged into sphere 1 any more: the Egypt gate starts at egypt3, so a sun
    # producer is the only way out of sphere 1 and fill has to place one there
    # for the seed to open at all. An early_items entry here would mean the old
    # nudge came back, which fill was free to ignore.
    assert not mw.early_items[1], \
        f"nothing should be requested early any more, got {dict(mw.early_items[1])}"
    # ...and no sun producer may be granted outright, or every sun requirement
    # in the seed is satisfied before it is ever asked and the gates go vacuous.
    assert not (set(SUN_PRODUCER_PLANTS) & {i.name for i in mw.precollected}), \
        "a sun producer was granted outright, defeating the Egypt gate"
    # At least one sun producer has to be in the pool, or Egypt's egypt6 gate is
    # a wall. Normally every one of them is; a seed with fewer locations than
    # progression plants trims down to a floor of one per group, which is what
    # lets an Egypt-only seed generate at all.
    _pool_names = {i.name for i in mw.itempool}
    _suns = set(SUN_PRODUCER_PLANTS) & _pool_names
    assert _suns, "no sun producer in the pool, so the egypt6 gate is a wall"
    # ...or in the player's hand. A granted plant is deliberately not shipped
    # again, so the gate can legitimately be satisfied by the grant rather than
    # by anything in the pool.
    _attackers = (set(C.CHEAP_ATTACKER_PLANTS)
                  & (_pool_names | {i.name for i in mw.precollected}))
    assert _attackers, "no cheap attacker in the pool or in hand: the egypt6 gate is a wall"
    # "Untrimmed" has to allow for the granted plants being held back, or a seed
    # with starting_plants raised reads as trimmed when it is merely short by
    # what the player already holds.
    _held = {i.name for i in mw.precollected}
    _want_all = len(_PLANTS_ALL) - len(_held & {p.name for p in _PLANTS_ALL})
    _trimmed = len([i for i in mw.itempool
                    if i.name in {p.name for p in _PLANTS_ALL}]) < _want_all
    if not _trimmed:
        assert set(SUN_PRODUCER_PLANTS) <= _pool_names, \
            f"sun producers missing from an untrimmed pool: {sorted(set(SUN_PRODUCER_PLANTS) - _pool_names)}"
    assert starter in STARTER_PLANTS, f"starter {starter} not in STARTER_PLANTS"
    assert starter not in SINGLE_USE_PLANTS, f"starter {starter} is single-use"
    assert starter not in NON_DAMAGING_PLANTS, f"starter {starter} deals no damage"
    # Named regressions. Each of these reached the starter pool at some point
    # because CHEAP_ATTACKER_PLANTS is derived from SunCost + Family, and
    # Family is a theme tag rather than a damage flag -- the entire "Magic"
    # family is utility. Intensive Carrot was actually handed out in a seed.
    for _bad in ("Intensive Carrot", "Explode-O-Nut", "Moonflower",
                 "Shrinking Violet", "Hypno-shroom", "Potato Mine",
                 "Chili Bean", "E.M. Peach", "Squash", "Magnifying Grass"):
        assert _bad not in STARTER_PLANTS, f"{_bad} is back in the starter pool"
    # Chomper has no almanac `damage` stat but does have ChewDamage 200, so a
    # naive "no damage stat" filter would wrongly drop it. It must stay.
    assert "Chomper" in STARTER_PLANTS, "Chomper wrongly dropped from starters"
    # CHEAP_ATTACKER_PLANTS gates every Ancient Egypt stretch, so nothing that
    # deals no damage may be in it -- holding only Sunflower + Moonflower used
    # to read as a survivable lawn.
    from pvz2gardendless.constants import CHEAP_ATTACKER_PLANTS, STARTER_PLANTS
    _overlap = set(NON_DAMAGING_PLANTS) & set(CHEAP_ATTACKER_PLANTS)
    assert not _overlap, f"non-damaging plants count as attackers: {_overlap}"
    # Water-only plants cannot be placed on Ancient Egypt's terrain.
    for _wet in ("Tangle Kelp", "Lily Pad"):
        assert _wet not in CHEAP_ATTACKER_PLANTS, f"{_wet} is water-only"
    # Real attackers the old Family heuristic wrongly dropped.
    for _good in ("Puff-shroom", "Pea-nut", "Endurian"):
        assert _good in CHEAP_ATTACKER_PLANTS, f"{_good} should be an attacker"
    # Chard Guard is NOT one, and used to be listed above as though it were.
    # Its only damage signal is an Action carrying Damage 60, which is knockback
    # force: no projectile, no `damage` PlantStat, no ChewDamage/ContactDamage/
    # StabDamage, and ChardGuard.ts never calls dealDamage. It punts.
    assert "Chard Guard" not in CHEAP_ATTACKER_PLANTS,         "Chard Guard is a blocker; an Action damage number alone does not "         "make an attacker"
    assert "Chard Guard" not in STARTER_PLANTS,         "Chard Guard cannot be the sole guaranteed plant -- it cannot kill"
    # Sheetless plants are attackers by inspection, not omissions.
    for _ns in ("Scaredy-shroom", "Vamporcini", "Skyshooter"):
        assert _ns in CHEAP_ATTACKER_PLANTS, f"{_ns} dropped for having no sheet"
    assert sd["worlds_required"] <= len(sd["goal_locations"])
    assert sd["worlds_required"] >= 1, "goal must stay satisfiable"
    # The goal count is an access rule on the Victory LOCATION now, and a
    # location rule needs no indirect conditions -- the advancement sweep
    # re-runs until it stops collecting. When this was an entrance rule on
    # "Enter Modern Day" there was one registration per goal, and the sweep
    # read the entrance as locked without them.
    assert not mw.indirect, f"unexpected indirect conditions: {mw.indirect}"
    # Victory hangs off Tutorial, not off any one world: no single world is on
    # the path to winning any more.
    _vic = mw.get_location("Victory", 1)
    assert _vic.parent_region.name == "Tutorial",         f"Victory is in {_vic.parent_region.name}, not Tutorial"
    # The win flips exactly at worlds_required McGuffins and not one earlier.
    # Stated as a ladder over the count rather than as one true/false pair: a
    # rule that ignored its state entirely -- "always winnable" -- would satisfy
    # any single positive check, and that is the mutation that matters, since it
    # would let a seed be finished the moment it started.
    class _McgState:
        """Holds n copies of the goal McGuffin and nothing else."""
        def __init__(self, n, name):
            self.n, self.name = n, name
            # Nothing is reachable, so the rule's reachability half contributes
            # nothing and this measures the ITEM half on its own.
            self._reachable = set()

        def has(self, name, player, count=1):
            return name == self.name and self.n >= count

    _req = sd["worlds_required"]
    for _n in range(0, _req + 2):
        _want = _n >= _req
        _got = bool(_vic.access_rule(_McgState(_n, sd["goal_item"])))
        assert _got == _want, (
            f"Victory {'open' if _got else 'shut'} holding {_n}/{_req} "
            f"{sd['goal_item']}s")
    # ...and it is THIS seed's McGuffin that opens it, not any goal item.
    _other = next(n for n in ("Time Key", "Trophy", "Gold Medal")
                  if n != sd["goal_item"])
    assert not _vic.access_rule(_McgState(_req + 5, _other)),         f"another goal type's McGuffin opens a {sd['goal_item']} seed"
    from pvz2gardendless.items import UPGRADE_ITEMS
    from pvz2gardendless.constants import UPGRADE_GROUPS, UPGRADE_ITEM_COUNT
    upnames = {u.name for u in UPGRADE_ITEMS}
    ups = [i.name for i in mw.itempool if i.name in upnames]
    # All 14 whenever they fit. A seed smaller than its mandatory block trims
    # them -- upgrades gate nothing, so they give before a progression plant
    # does -- which the goal trim made reachable: Egypt alone under the
    # world_key goal is 12 locations against 14 upgrades.
    want = UPGRADE_ITEM_COUNT if w.options.shuffle_upgrades else 0
    if want and len(ups) < want:
        # Full means "the pool filled every FILLABLE location" -- the goal
        # levels hold locked McGuffins and were never the pool's to fill.
        assert len(mw.itempool) == (len(w.active_locations())
                                    - len(w.goal_locations())),             "upgrades were trimmed in a seed that was not full"
        assert len(ups) == len(mw.itempool) - sum(
            1 for i in mw.itempool if i.name not in upnames), None
    else:
        assert len(ups) == want, f"upgrade copies in pool {len(ups)} != {want}"
    if w.options.shuffle_upgrades and len(ups) == want:
        got = collections.Counter(ups)
        for name, cns in UPGRADE_GROUPS:
            assert got[name] == len(cns), f"{name}: {got[name]} copies != {len(cns)}"
    assert sd["shuffle_upgrades"] is bool(w.options.shuffle_upgrades)
    assert len(sd["upgrade_items"]) == len(UPGRADE_GROUPS)
    dupes = [n for n, c in collections.Counter(l.name for l in locs).items() if c > 1]
    assert not dupes, dupes
    return w, sd


run("default (all worlds)")
run("3 worlds, want 4 keys", world_count=3, worlds_required=4)
run("1 world (Egypt only)", world_count=1, worlds_required=11, include_side_paths=1)
run("explicit list only", world_count=1, include_side_paths=1,
    enabled_worlds=["Pirate Seas", "Wild West"], worlds_required=11)
run("whitelist under count", world_count=5, enabled_worlds=["Big Wave Beach"])
run("zomboss, 3 worlds", world_count=3,
    goal_type=GoalType.option_zomboss, worlds_required=11)
run("completions, 2 worlds", world_count=2,
    goal_type=GoalType.option_completion, worlds_required=11,
    include_side_paths=1)
run("3 worlds + shopsanity", world_count=3, shopsanity=1, worlds_required=11)
run("all worlds + shopsanity + traps", shopsanity=1, trap_percentage=50)

# world_count beats a longer explicit list. This reversed on 2026-08-24: naming
# a world used to guarantee it, on the reasoning that an explicit choice
# outranks a target. That became untenable when enabled_worlds gained a default
# naming eleven worlds -- every count from 1 to 11 was already satisfied, so
# world_count did nothing at all below 12 and `world_count: 1` built eleven
# worlds. The count is a hard cap now.
_named4 = ["Pirate Seas", "Wild West", "Far Future", "Dark Ages"]
w, _ = run("explicit 4 vs count 2", world_count=2, enabled_worlds=_named4)
assert len(w.enabled_worlds) == 2, sorted(w.enabled_worlds)

# Ancient Egypt survives the trim whatever else goes: it is the only world
# playable with no items, so a seed without it opens on nothing at all.
assert "Ancient Egypt" in w.enabled_worlds, sorted(w.enabled_worlds)

# The trim only ever DROPS from what was asked for -- it must never substitute
# a world nobody named. Egypt is forced in and so is exempt.
_stray = w.enabled_worlds - set(_named4) - {"Ancient Egypt"}
assert not _stray, f"the trim invented worlds nobody named: {sorted(_stray)}"

# Trimming is seeded, not incidental: the same slot seed must build the same
# worlds twice. This does NOT prove the candidate list is list-ordered --
# set iteration is stable for the same strings within one process, so sampling
# out of a set passes here and only diverges across processes. The list
# comprehension in _choose_worlds is what actually guarantees that.
_wA, _ = run("trim determinism A", world_count=2, enabled_worlds=_named4)
_wB, _ = run("trim determinism B", world_count=2, enabled_worlds=_named4)
assert _wA.enabled_worlds == _wB.enabled_worlds,     (sorted(_wA.enabled_worlds), sorted(_wB.enabled_worlds))

# The cap holds at the extreme: every world named, one world asked for.
_w1, _ = run("all named vs count 1", world_count=1,
             enabled_worlds=list(C.SELECTABLE_WORLDS))
assert _w1.enabled_worlds == {"Ancient Egypt"}, sorted(_w1.enabled_worlds)

# world_count is the WHOLE number of worlds, Ancient Egypt and Modern Day
# included. Modern Day was forced in on top of the count until 2026-08-23,
# which made "1" produce two worlds -- caught in a real seed whose spoiler said
# World Count 1 and then built 103 locations across Egypt and Modern Day.
w, _ = run("count semantics", world_count=3)
assert len(w.enabled_worlds) == 3, w.enabled_worlds

# ...and 1 really is Ancient Egypt on its own, which is the case that was
# broken. It is also the smallest seed the pool can fill, so it doubles as the
# floor test for the progression-plant trim.
w1, _ = run("one world means Egypt alone", world_count=1)
assert w1.enabled_worlds == {"Ancient Egypt"}, w1.enabled_worlds

# Modern Day is an ordinary selectable world now: naming it gets it, and a
# count that cannot fit it leaves it out.
wmd, _ = run("Modern Day by name", world_count=2, enabled_worlds=["Modern Day"])
assert wmd.enabled_worlds == {"Ancient Egypt", "Modern Day"}, wmd.enabled_worlds

# The range has to reach every world, or the option cannot ask for all of them.
assert WorldCount.range_end == len(C.WORLD_REGIONS) == 13, WorldCount.range_end

# The default is 11, not 13: Kongfu Temple and Aerial Fortress are out of a
# default seed. Literals, because the point is to catch the two defaults
# drifting apart -- reading either from the other would agree with anything.
assert WorldCount.default == 11,     f"world_count default is {WorldCount.default}, want 11"
assert set(EnabledWorlds.default) == set(C.SELECTABLE_WORLDS) - {
    "Kongfu Temple", "Aerial Fortress"}, sorted(EnabledWorlds.default)

# The two MUST agree, in the one direction that still bites: a world_count
# BELOW the eleven named worlds drops one of them at random, so a "default"
# seed would be missing a world it asked for. A count ABOVE eleven is harmless
# now that enabled_worlds is a whitelist -- there is nothing outside it to top
# up from -- but keeping them equal is what makes the default self-describing.
assert WorldCount.default == len(EnabledWorlds.default),     (f"world_count default {WorldCount.default} against "
     f"{len(EnabledWorlds.default)} default enabled worlds -- a default seed "
     "would drop one at random")
_wdef, _ = run("default worlds")
assert _wdef.enabled_worlds == set(EnabledWorlds.default), sorted(_wdef.enabled_worlds)
wall, _ = run("every world", **_EVERY_WORLD)
assert wall.enabled_worlds == set(C.WORLD_REGIONS), sorted(wall.enabled_worlds)

# -- enabled_worlds is a whitelist: a world is in the seed IFF it is named ----
#
# world_count used to top the selection up from worlds the yaml had NOT named,
# so a short list against a high count handed you worlds you never asked for.
# Reversed 2026-08-26: the list decides membership outright and the count can
# only trim. Ancient Egypt sits outside the whitelist and is always in.
_wl = ["Pirate Seas", "Wild West"]
_ww, _wsd = run("whitelist beats a higher count", world_count=13,
                enabled_worlds=_wl, worlds_required=12)
assert _ww.enabled_worlds == set(_wl) | set(C.ALWAYS_ENABLED_WORLDS),     sorted(_ww.enabled_worlds)
assert "Ancient Egypt" in _ww.enabled_worlds

# ...and worlds_required comes down with it, rather than demanding McGuffins
# the seed never built. Three: the two named plus Ancient Egypt.
assert _wsd["worlds_required"] == len(_wsd["goal_locations"]) == 3,     (_wsd["worlds_required"], _wsd["goal_locations"])

# A one-world whitelist against the highest count is still that world plus
# Egypt -- the top-up branch must not fire at all when a whitelist is present.
_w1, _ = run("whitelist of one vs count 13", world_count=13,
             enabled_worlds=["Dark Ages"])
assert _w1.enabled_worlds == {"Dark Ages"} | set(C.ALWAYS_ENABLED_WORLDS),     sorted(_w1.enabled_worlds)

# The count still wins downward: a whitelist longer than the count is trimmed
# to it, and Ancient Egypt is not what gets trimmed.
_wnarrow, _ = run("count trims the whitelist", world_count=2,
                  enabled_worlds=["Pirate Seas", "Wild West", "Dark Ages"])
assert len(_wnarrow.enabled_worlds) == 2, sorted(_wnarrow.enabled_worlds)
assert "Ancient Egypt" in _wnarrow.enabled_worlds
assert _wnarrow.enabled_worlds <= ({"Pirate Seas", "Wild West", "Dark Ages"}
                                   | set(C.ALWAYS_ENABLED_WORLDS))

# An EMPTY list is not a whitelist of nothing -- it waives the whitelist and
# world_count draws at random, which is what it has always meant and what the
# option text promises. A yaml written for the old behaviour still generates.
_wempty, _ = run("empty list waives the whitelist", world_count=4,
                 enabled_worlds=[])
assert len(_wempty.enabled_worlds) == 4, sorted(_wempty.enabled_worlds)
assert "Ancient Egypt" in _wempty.enabled_worlds

# Requiring FEWER worlds than the seed holds is left alone: only the cap
# direction is enforced.
_wfew, _sdfew = run("require fewer than enabled", world_count=5,
                    worlds_required=2)
assert _sdfew["worlds_required"] == 2
assert len(_sdfew["goal_locations"]) == 5

# determinism for a given slot seed
a, _ = run("determinism A", world_count=4)
b, _ = run("determinism B", world_count=4)
assert a.enabled_worlds == b.enabled_worlds

# Frostbite Caves entry-plant rule only when the world is in.
# world_count 2, not 1: Ancient Egypt is forced in and takes a slot, so a
# one-world seed drops the named world however explicitly it was asked for.
w, _ = run("BWB forced in", world_count=2, enabled_worlds=["Big Wave Beach"],
           include_side_paths=1)
assert "Big Wave Beach" in w.enabled_worlds

run("upgrades off", shuffle_upgrades=0)
run("upgrades off, 3 worlds", shuffle_upgrades=0, world_count=3)
run("upgrades on, 1 world", world_count=1, include_side_paths=1)
run("upgrades on + shopsanity", shopsanity=1)

# conveyor randomization: pure client behaviour, so all generation has to do is
# carry the flag and a per-slot seed. It must not disturb the pool or locations.
_a, _sd_off = run("conveyor off", randomize_conveyor_plants=0)
_b, _sd_on  = run("conveyor on",  randomize_conveyor_plants=1)
assert _sd_off["randomize_conveyor"] is False and _sd_on["randomize_conveyor"] is True
assert isinstance(_sd_on["conveyor_seed"], int) and 0 <= _sd_on["conveyor_seed"] < 2**32
assert _sd_off["goal_locations"] == _sd_on["goal_locations"], "conveyor changed logic"

# ── shuffle_zombies ─────────────────────────────────────────────────────────
# Also pure client behaviour: generation carries the flag, a per-slot seed and
# the tier table, and must leave the pool, the locations and the logic alone.
from pvz2gardendless.zombie_data import (ZOMBIE_TIERS, ZOMBIE_TIER_OF,
                                         THREAT_TAGS, swap_pool, tier_of)

_z_off_w, _z_off = run("zombies off", shuffle_zombies=0)
_z_on_w,  _z_on  = run("zombies on",  shuffle_zombies=1)
assert _z_off["shuffle_zombies"] is False and _z_on["shuffle_zombies"] is True
assert isinstance(_z_on["zombie_seed"], int) and 0 <= _z_on["zombie_seed"] < 2**32
assert _z_off["goal_locations"] == _z_on["goal_locations"], "zombie shuffle changed logic"
assert len(_z_off_w.active_locations()) == len(_z_on_w.active_locations())
assert sorted(i.name for i in _z_off_w.multiworld.itempool) == \
       sorted(i.name for i in _z_on_w.multiworld.itempool), "zombie shuffle changed the pool"

# The tiers are only worth sending when the client will use them: ~6KB in
# every Connected packet otherwise.
assert _z_off["zombie_tiers"] == {}, "tiers sent with the option off"
assert _z_on["zombie_tiers"] == ZOMBIE_TIERS

# slot_data is append-only: an older client reads only the keys it knows, so
# removing or renaming one silently breaks every build already out there. The
# three zombie keys are additive, and a seed predating them sends none of the
# three -- which the client reads as off.
_SLOT_DATA_BEFORE_ZOMBIES = {
    "conveyor_seed", "death_link", "enabled_worlds", "game_version",
    "goal_locations", "goal_type", "modern_day_victory", "randomize_conveyor",
    "shopsanity", "shuffle_upgrades", "skip_tutorial", "upgrade_items",
    "victory_locations", "worlds_required",
}
assert _SLOT_DATA_BEFORE_ZOMBIES <= set(_z_on), \
    f"slot_data lost keys: {sorted(_SLOT_DATA_BEFORE_ZOMBIES - set(_z_on))}"
assert set(_z_on) - _SLOT_DATA_BEFORE_ZOMBIES == \
    {"shuffle_zombies", "zombie_tiers", "zombie_seed", "modern_day_keyed",
     "world_gates", "goal_item", "goal_item_plural",
     # Added 2026-08-26 for Universal Tracker: everything generation ROLLED or
     # decided from an option the client never needed. The client ignores all
     # six; a seed that predates them leaves UT on its own local roll.
     "granted_plants", "logic_attackers", "logic_jesters",
     "include_side_paths", "include_danger_rooms", "include_levels_past_goal"}, \
    f"unexpected new slot_data keys: {sorted(set(_z_on) - _SLOT_DATA_BEFORE_ZOMBIES)}"

# modern_day_keyed is additive for the same reason, and modern_day_victory
# stays even though generation no longer uses it: a client built before
# 2026-08-23 gates Modern Day on the goal count and ends the run on that one
# level, so removing either key would strand every build already out there.
assert _z_on["modern_day_keyed"] is True
# The McGuffin keys are additive too: a client that does not know goal_item
# falls back to counting goal LOCATIONS, which is what those builds did.
assert _z_on["goal_item"] in {"Time Key", "Trophy", "Gold Medal"}
assert _z_on["goal_item_plural"]
assert _z_on["modern_day_victory"], "old clients still need a victory location"

# Every tier must be non-empty and every zombie in exactly one tier, or the
# client's inverted index disagrees with this side about what may swap.
assert all(ZOMBIE_TIERS.values()), "an empty tier would make its zombies unswappable"
assert sum(len(v) for v in ZOMBIE_TIERS.values()) == len(ZOMBIE_TIER_OF), \
    "a zombie appears in more than one tier"

# THE load-bearing invariant, and the reason this option needs no new access
# rule: a zombie that needs a specific plant to answer it can only ever become
# another zombie needing the same plant. Dark Ages keeps its Jester and
# Frostbite Caves keeps its ice blocks, so the requirements in
# WORLD_ENTRY_PLANTS stay exactly as true as they were. Let a threat roam and
# nearly every world ends up gated on the Jester counter, flattening the
# sphere layering this world works to protect.
#
# Note "the swap pool of a threat zombie contains only threat zombies" is NOT
# worth asserting -- tiers partition the zombies and swap_pool() hands back
# the whole tier, so it is true by construction and can never fail. What can
# actually go wrong is MEMBERSHIP: a regenerated table that tags the wrong
# zombie, or stops tagging one at all. So the membership is pinned by name,
# and each set is exactly what its game property yields (see zombie_data).
THREAT_MEMBERS = {
    # MoveSpeedMultiplierWhileJuggling -- returns your own projectiles
    "jester": {"birthday_juggler", "dark_juggler", "foodfight_chefster"},
    # NumberOfIceblocksToSpawnWith -- arrives carrying ice blocks
    "iceblock": {"birthday_troglobite", "birthday_troglobite_1block",
                 "birthday_troglobite_2block", "iceage_troglobite",
                 "iceage_troglobite_1block", "iceage_troglobite_2block",
                 "iceage_troglobite_veteran"},
}
for _tag, _expected in THREAT_MEMBERS.items():
    _tiers = [t for t in ZOMBIE_TIERS if t.endswith("-" + _tag)]
    assert _tiers, f"no tier carries the {_tag} tag any more"
    _members = {z for t in _tiers for z in ZOMBIE_TIERS[t]}
    assert _members == _expected, (
        f"{_tag} membership drifted: "
        f"gained {sorted(_members - _expected)}, lost {sorted(_expected - _members)}")

# air and blocker have no counter-plant list to gate on, so they are pinned by
# size only -- they are partitioned to stop them spreading, not to gate on.
for _tag in THREAT_TAGS:
    assert any(t.endswith("-" + _tag) for t in ZOMBIE_TIERS), \
        f"no tier carries the {_tag} tag any more"
print(f"zombie tiers: {len(ZOMBIE_TIERS)} tiers over {len(ZOMBIE_TIER_OF)} zombies, "
      f"{len(THREAT_TAGS)} threat classes partitioned")

# Named regressions on the derivation, so a regenerated table cannot quietly
# drop a partition. Each of these was picked because getting it wrong breaks
# something specific rather than just looking odd.
assert tier_of("zomboss_egypt") == "" and swap_pool("zomboss_egypt") == [], \
    "a Zomboss became swappable -- boss fights would stop being the built fight"
# Camels are a chain driven by CamelMinigameProperties, and in egypt7, egypt16
# and egypt23 you win by MATCHING them on hump count. Shuffling them left those
# three levels literally unbeatable -- found in play testing, not by this
# suite, which is why the whole family is named here rather than spot-checked.
_CAMELS = [
    "camel_onehump", "camel_twohump", "camel_threehump", "camel_manyhump",
    "camel_onehump_touch", "camel_twohump_touch", "camel_threehump_touch",
    "camel_manyhump_touch",
    "easter_camel_onehump", "easter_camel_twohump", "easter_camel_manyhump",
    "feastivus_camel_onehump", "feastivus_camel_twohump",
    "feastivus_camel_manyhump",
    "lunar_camel_onehump", "lunar_camel_twohump", "lunar_camel_manyhump",
]
_swappable_camels = [c for c in _CAMELS if tier_of(c)]
assert not _swappable_camels, (
    f"camels are shuffled again, which makes egypt7/16/23 unwinnable: "
    f"{_swappable_camels}")
# ...and nothing may turn INTO a camel either, or the same levels get camels
# they cannot match plus a lawn full of strangers.
_camel_targets = sorted(z for z in ZOMBIE_TIER_OF if "camel" in z)
assert not _camel_targets, f"a camel is reachable as a swap target: {_camel_targets}"
assert tier_of("lawn") == "", "the lawn placeholder must resolve, not swap"
assert "dark_juggler" in swap_pool("dark_juggler"), "the Jester left its own pool"
assert set(swap_pool("dark_juggler")) == \
       {"dark_juggler", "foodfight_chefster", "birthday_juggler"}, \
    "the Jester pool changed -- check MoveSpeedMultiplierWhileJuggling"
assert all("garg" in tier_of(z) for z in swap_pool("dark_gargantuar")), \
    "a Gargantuar can become something that is not a Gargantuar"
assert all("water" in tier_of(z) for z in swap_pool("beach_snorkel")), \
    "a water zombie can become a land zombie, which drowns it"
assert all("land" in tier_of(z) for z in swap_pool("mummy")), \
    "a land zombie can become a water zombie"
# Mummy is the plainest sphere-1 zombie in the game; if its band ever collapses
# to itself the option silently stops doing anything in Ancient Egypt.
assert len(swap_pool("mummy")) > 20, "the basic zombie band has collapsed"
print("zombie tier regressions hold")

from pvz2gardendless.items import (UPGRADE_ITEMS, ALL_ITEMS, UPGRADE_ITEM_TO_CNS,
                                   COSTUME_ITEMS, FILLER_POOL, FILLER_CYCLE)
from pvz2gardendless.constants import UPGRADE_GROUPS, UPGRADE_ITEM_COUNT

# item IDs are append-only, block by block: every block sits entirely above
# every block added before it. Declared in the order blocks were introduced,
# so adding a new one only means appending it here.
from pvz2gardendless.items import (PLANT_ITEMS, KEY_ITEMS, FILLER_ITEMS,
                                   TRAP_ITEMS, COSTUME_TRAP_ITEMS,
                                   CURRENCY_TRAP_ITEMS, TRAP_POOL,
                                   COIN_TRAP, GEM_TRAP,
                                   PROGRESSIVE_WORLD_ITEMS,
                                   GEM_GRANT, GEM_GRANT_COUNT, GEM_GRANT_ITEMS,
                                   GOAL_ITEMS)
BLOCKS = [
    ("plants+keys+filler+traps", PLANT_ITEMS + KEY_ITEMS + FILLER_ITEMS + TRAP_ITEMS),
    ("upgrades", UPGRADE_ITEMS),
    ("costume filler", COSTUME_ITEMS),
    ("costume trap", COSTUME_TRAP_ITEMS),
    ("currency traps", CURRENCY_TRAP_ITEMS),
    ("progressive world unlocks", PROGRESSIVE_WORLD_ITEMS),
    ("guaranteed gem grants", GEM_GRANT_ITEMS),
    ("goal mcguffins", GOAL_ITEMS),
]
for bi in range(1, len(BLOCKS)):
    name, block = BLOCKS[bi]
    earlier = [i.code for _, b in BLOCKS[:bi] for i in b]
    assert min(i.code for i in block) > max(earlier),         f"{name} block overlaps an earlier block"
assert sum(len(b) for _, b in BLOCKS) == len(ALL_ITEMS), "a block is unaccounted for"
# the costume filler must be reachable from both the cycle and get_filler_item_name
assert set(FILLER_CYCLE) == {f.name for f in FILLER_POOL}
assert any(i.name == "Random Plant Costume" for i in COSTUME_ITEMS)
assert len({i.code for i in ALL_ITEMS}) == len(ALL_ITEMS), "duplicate item IDs"

# ── unreachable levels are never built ──────────────────────────────────────
# Levels defined in the game data but attached to no map node, so nothing can
# launch them and their checks can never fire. They were reachable in LOGIC, so
# fill could bury a world key on one. Two families: the eleven random_* levels,
# and two Danger Rooms (kongfu_dangerroom4, mixed_dangerroom2) that additionally
# have no level awarding the trophy that would unlock them.
#
# Checked across every option combination, because the point is that no
# setting brings them back.
for _label, _kw in (("default", {}),
                    ("side paths + danger rooms", dict(include_side_paths=1,
                                                       include_danger_rooms=1)),
                    ("shopsanity", dict(shopsanity=1)),
                    ("one world", dict(world_count=1, worlds_required=11))):
    _uw, _ = run(f"unreachable: {_label}", **_kw)
    _built = {l.name for l in _uw.active_locations()}
    _leak = sorted(C.UNREACHABLE_LOCATIONS & _built)
    assert not _leak, f"{_label}: unreachable locations built: {_leak}"
    # ...and nothing else went with them.
    assert len(_built) == len({l.name for l in _uw.active_locations()})
print(f"none of the {len(C.UNREACHABLE_LOCATIONS)} unreachable levels is ever built")

# They must still exist in the static table: AP requires location_name_to_id to
# be constant, and the IDs after them would renumber if one were deleted.
from pvz2gardendless.locations import ALL_LOCATIONS as _ALL_L, LOC_NAME_TO_ID
for _n in C.UNREACHABLE_LOCATIONS:
    assert _n in LOC_NAME_TO_ID, f"{_n} was deleted from the table, renumbering IDs"
# Four families, and nothing else may be swept in. Named explicitly rather than
# derived by any rule: each was established by checking the game's map scenes
# for a node that can launch the level, which this suite cannot read (it runs
# with no game source). A rule loose enough to catch them from the names alone
# would also catch the real levels sitting next to them -- every OTHER
# dangerroom location is live, and every OTHER side path is reachable.
_rand = {l.name for l in _ALL_L if l.name.startswith("random_")}
_orphan_rooms = {"kongfu_dangerroom4", "mixed_dangerroom2"}
# The eight side paths with no map node anywhere. Whole regions, so this is
# expressed as "every location in them" -- if one gains a location later it is
# dropped too, which is right: nothing in these can be launched.
_ORPHAN_PATH_REGIONS = {
    "Bank Sidepath", "Epic Beghouled Sidepath", "Floawerpot Sidepath",
    "Mixed Sidepath", "Reinforcemint Unused Sidepath", "Rhythm Sidepath",
    "Sandbox Sidepath", "Shootingstarfruit Sidepath",
}
_orphan_paths = {l.name for l in _ALL_L if l.region in _ORPHAN_PATH_REGIONS}
# Shop cards the game no longer sells. The store table swapped three
# commodities upstream: the build sells witchhazel, slingpea and chillypepper
# where the older snapshot had mirrornut, wasabiwhip and pyrevine. A card that
# is not in StoreCommodityFeatures is never drawn, so its check can never fire.
# Named from the constant so the two cannot drift, but pinned by count here.
_absent_shop = {C.shop_location_name(c) for c in C.SHOP_ABSENT_COMMODITIES}
assert len(_absent_shop) == 3, f"expected 3 absent shop cards, got {sorted(_absent_shop)}"
_expected = _rand | _orphan_rooms | _orphan_paths | {"iceage24_B"} | _absent_shop
assert _expected == set(C.UNREACHABLE_LOCATIONS),     f"UNREACHABLE_LOCATIONS disagrees: {_expected ^ set(C.UNREACHABLE_LOCATIONS)}"
# Those eight regions must end up completely empty, under every option combo --
# include_side_paths on is the case that used to build them.
for _sp in (0, 1):
    _ow, _ = run(f"orphan side paths: side_paths={_sp}", include_side_paths=_sp)
    _obuilt = {l.region for l in _ow.active_locations()}
    _leak = _ORPHAN_PATH_REGIONS & _obuilt
    assert not _leak, f"unreachable side path built locations: {sorted(_leak)}"
# Every side path is accounted for: it either branches off a world level, is
# chained behind another path, or is one of the eight with no map node at all.
# A path missing from all three would silently keep hanging off its world's
# opening, which is the bug SIDE_PATH_UNLOCK exists to fix.
_covered = set(C.SIDE_PATH_UNLOCK) | set(C.SIDE_PATH_CHAIN) | _ORPHAN_PATH_REGIONS
assert _covered == set(C.SIDE_PATH_REGIONS),     f"side paths with no gate: {sorted(set(C.SIDE_PATH_REGIONS) - _covered)}, "     f"unknown: {sorted(_covered - set(C.SIDE_PATH_REGIONS))}"
# Each of the three tables says something different, and they have to agree:
# the unlock level must be a real location, in the world SIDE_PATH_WORLD claims
# the path branches from, and a chain target must itself be a gated side path.
_lnames = {l.name: l.region for l in _ALL_L}
for _sp, _lvl in C.SIDE_PATH_UNLOCK.items():
    assert _lvl in _lnames, f"{_sp} unlocks at {_lvl}, which is not a location"
    assert _lvl not in C.UNREACHABLE_LOCATIONS, f"{_sp} unlocks at unreachable {_lvl}"
    _owner = C.SIDE_PATH_WORLD[_sp]
    assert _lnames[_lvl] in C.WORLD_REGIONS[_owner],         f"{_sp} is a {_owner} path but unlocks at {_lvl} in {_lnames[_lvl]}"
for _sp, _target in C.SIDE_PATH_CHAIN.items():
    assert _target in C.SIDE_PATH_UNLOCK, f"{_sp} chains off ungated {_target}"

# The gate is a region connection, so check the graph rather than the table:
# every side path must hang off the region holding the level that reveals it.
# Ancient Egypt is the case that matters -- its opening is ungated, so a path
# left on the world region is in sphere 1, which is how two world keys ended up
# in Appease-mint. Danger rooms on so the stretch cut sees its real location
# counts, side paths on so the regions exist at all.
# Every world, explicitly: this walks all 31 side paths, and the default seed
# is 11 worlds, so Kongfu Temple and Aerial Fortress would have no regions
# for their paths to hang off.
_pw, _ = run("side path parents",
             include_side_paths=1, include_danger_rooms=1, **ALL_WORLDS)
_pmw = _pw.multiworld
_ploc_region = {l.name: r.name for r in _pmw.regions for l in r.locations}
_pregions = {r.name: r for r in _pmw.regions}
_bad = []
for _sp in C.SIDE_PATH_REGIONS:
    try:
        _parent = _pmw.get_entrance(f"Enter {_sp}", 1).parent_region.name
    except KeyError:
        continue
    if _sp in C.SIDE_PATH_CHAIN:
        _want = C.SIDE_PATH_CHAIN[_sp]
    elif _sp in C.SIDE_PATH_UNLOCK:
        _want = _ploc_region[C.SIDE_PATH_UNLOCK[_sp]]
    else:
        # No map node anywhere, so there is no level to gate it on. Where it
        # hangs does not matter as long as it stays empty, which the orphan
        # check above already proves; Rhythm keeps a SIDE_PATH_WORLD entry and
        # so lands on Frostbite Caves rather than Tutorial.
        assert not _pregions[_sp].locations,             f"{_sp} has no map node but was given locations"
        continue
    if _parent != _want:
        _bad.append(f"{_sp}: hangs off {_parent}, want {_want}")
assert not _bad, f"side paths on the wrong region: {_bad}"
# ...and the fix is load-bearing. Two pins, both literal and both sourced from
# the world-map scenes rather than from this code: Egypt's map labels the Squash
# branch "6-1" and the Appease-mint branch "29-1".
#
# Egypt's opening runs to egypt8, its World Key level, and is cut again at
# egypt6 -- the level the game expects a sun producer by. So Squash lands in
# " Early": no unlock needed, but a sun producer and an attacker are, which
# keeps it out of sphere 1. Appease-mint at egypt29 lands in the last stretch,
# two progressive unlocks deep.
for _sp, _want_region in (("Squash Sidepath", "Ancient Egypt Early"),
                          ("Appease-mint Sidepath", "Ancient Egypt Late")):
    _got = _pmw.get_entrance(f"Enter {_sp}", 1).parent_region.name
    assert _got == _want_region, f"{_sp} hangs off {_got}, want {_want_region}"
# 22 of the 30 land past their world's opening stretch. The other 8 branch
# early enough that the opening really is where the game puts them: beach7,
# lostcity8, dark4, dark9, modern10, iceage12, neon14, beach14 -- all at or
# before their world's World Key level, which is where every world's opening
# ends. A different number here means the stretch cut moved, not that the
# gating got better or worse.
#
# It was 19 until 2026-08-23, when the cuts became each world's own milestones
# rather than even thirds; two paths moved deeper (kongfu12 and future13 are
# past those worlds' key levels). Squash is the 22nd and is a different case:
# egypt6 is inside Egypt's opening, but the opening is cut again there for the
# sun expectation, so it hangs off "Ancient Egypt Early" rather than the world
# region. Appease-mint 2 is in there too: iceage25 is deep in Frostbite Caves,
# which is the whole reason it was split off the Egypt half.
_deep = [_sp for _sp in C.SIDE_PATH_UNLOCK
         if _pmw.get_entrance(f"Enter {_sp}", 1).parent_region.name
         not in C.ALL_WORLD_REGIONS]
assert len(_deep) == 22, f"{len(_deep)} side paths are gated past a world opening, want 22"
print(f"all {len(C.SIDE_PATH_UNLOCK)} branch side paths hang off their unlock level's "
      f"region ({len(_deep)} past the world opening), Hot Date chains off Sweet Potato")

# Shop cards: the gate table has to agree with the commodity list and with the
# locations, or a card is either ungated or gated on something that is not there.
_shop_names = {C.shop_location_name(c) for c in C.SHOP_CHECK_COMMODITIES}
assert set(C.SHOP_UNLOCK) <= set(C.SHOP_COMMODITIES),     f"SHOP_UNLOCK names commodities that are not sold: "     f"{sorted(set(C.SHOP_UNLOCK) - set(C.SHOP_COMMODITIES))}"
# The ten with no UnlockLevel in the game's store data. Pinned as literals from
# `StoreCommodityFeatures` rather than derived, so a card losing its gate by
# accident shows up here instead of quietly becoming an egypt6 check.
assert set(C.SHOP_COMMODITIES) - set(C.SHOP_UNLOCK) == {
    "jalapeno", "cranjelly", "chillypepper",
    # Still listed, still ungated, but no longer sold -- see SHOP_ABSENT_COMMODITIES.
    "mirrornut", "wasabiwhip", "pyrevine",
    "upgrade_sunshovel_lvl3", "upgrade_8_slots", "upgrade_pf_slots_lvl2",
    "upgrade_starting_sun_lvl2", "upgrade_manual_mowers_2",
}, "the set of shop cards with no UnlockLevel changed"
for _c, _lvl in C.SHOP_UNLOCK.items():
    assert _lvl in _lnames, f"{_c} unlocks at {_lvl}, which is not a location"
    assert _lvl not in C.UNREACHABLE_LOCATIONS, f"{_c} unlocks at unreachable {_lvl}"
    assert _lnames[_lvl] in C.ALL_WORLD_REGIONS,         f"{_c} unlocks at {_lvl}, which is not in a world region"

# A card whose unlock level is in a world this seed left out can never be
# bought, so it must not be built. Egypt-only is the sharp case: the game sells
# 39 cards, but only the ten ungated ones plus the two Egypt ones can ever
# appear. Counted rather than named, so adding a card does not break the test.
# include_levels_past_goal, because this is about which WORLD a card belongs to.
# The default goal also trims Egypt at egypt8, which drops the two cards stocked
# later in the world -- correct, and tested separately below.
_e1w, _ = run("shop cards drop with their world", world_count=1, shopsanity=1,
              worlds_required=11, include_levels_past_goal=1)
_e1shop = {l.name for l in _e1w.active_locations() if l.is_shop}
_egypt_cards = {C.shop_location_name(_c) for _c, _l in C.SHOP_UNLOCK.items()
                if _lnames[_l] in C.WORLD_REGIONS["Ancient Egypt"]}
_modern_cards = {C.shop_location_name(_c) for _c, _l in C.SHOP_UNLOCK.items()
                 if _lnames[_l] in C.WORLD_REGIONS["Modern Day"]}
# Upgrades are the only ungated cards that are checks; the ungated PLANTS are
# out entirely, since every upstream store change has landed in that set.
_upgrade_cards = {C.shop_location_name(_c) for _c in C.SHOP_UPGRADE_COMMODITIES}
# No Modern Day cards: world_count 1 is Ancient Egypt alone as of 2026-08-23.
# Their absence is the assertion -- Modern Day used to ride along in every seed
# and its two cards came with it.
_want_1w = _upgrade_cards | _egypt_cards
assert _modern_cards and not (_modern_cards & _want_1w),     "Modern Day cards are still expected in a one-world seed"
assert _e1shop == _want_1w,     f"one-world shop checks wrong: missing {sorted(_want_1w - _e1shop)}, "     f"extra {sorted(_e1shop - _want_1w)}"
# ...and every world back in restores all 39, so the filter is not just deleting.
_eall, _ = run("shop cards with every world", shopsanity=1, **ALL_WORLDS)
_all_shop = {l.name for l in _eall.active_locations() if l.is_shop}
assert _all_shop == {C.shop_location_name(_c) for _c in C.SHOP_CHECK_COMMODITIES},     f"all-worlds shop set wrong: {_all_shop ^ {C.shop_location_name(_c) for _c in C.SHOP_CHECK_COMMODITIES}}"
# Every check is gated on a level or is an upgrade -- no ungated plant survives.
_upg = set(C.SHOP_UPGRADE_COMMODITIES)
for _n in _all_shop:
    _c = _n[len("Shop: "):]
    assert _c in C.SHOP_UNLOCK or _c in _upg,         f"{_n} is a check but is gated on nothing"
# ...and the ungated plants really are gone, including the ones the store no
# longer stocks. This is the whole point of the policy.
assert not (_all_shop & {C.shop_location_name(_c) for _c in
                         ("jalapeno", "cranjelly", "chillypepper",
                          "mirrornut", "wasabiwhip", "pyrevine")}),     "an ungated plant card is still being built"
print(f"shop: {len(C.SHOP_UNLOCK)} of {len(C.SHOP_COMMODITIES)} cards gated on their "
      f"UnlockLevel, {len(_e1shop)} survive an Egypt-only seed")

# Hint buckets. The point is that "!hint World Unlocks" answers where all of
# them are in one command, so the group has to hold every unlock -- and the
# singular has to resolve to the same set, since AP matches a group name
# exactly and a player types whichever reads naturally.
from pvz2gardendless.items import (ITEM_NAME_GROUPS, ALL_ITEMS, KEY_ITEMS,
                                   PROGRESSIVE_WORLD_ITEMS)
_keynames = {i.name for i in KEY_ITEMS}
_unlocknames = {i.name for i in PROGRESSIVE_WORLD_ITEMS}
assert ITEM_NAME_GROUPS["World Unlocks"] == _unlocknames,     f"World Unlocks group is not the unlock items: {ITEM_NAME_GROUPS['World Unlocks'] ^ _unlocknames}"
# "World Keys" still answers, and answers with the unlocks: they ARE the keys
# now, and a player who learned that hint should not get an empty result. The
# Key items are in there too because they are still defined and a group may
# not name a non-item.
assert ITEM_NAME_GROUPS["World Keys"] == _unlocknames | _keynames,     f"World Keys group is not the unlocks plus the old keys: {ITEM_NAME_GROUPS['World Keys'] ^ (_unlocknames | _keynames)}"
assert ITEM_NAME_GROUPS["World Key"] == ITEM_NAME_GROUPS["World Keys"],     "the singular alias does not match the plural"
assert ITEM_NAME_GROUPS["World Unlock"] == ITEM_NAME_GROUPS["World Unlocks"],     "the singular alias does not match the plural"
for _p, _sg in (("Plants", "Plant"), ("Traps", "Trap"), ("Upgrades", "Upgrade"),
                ("Costumes", "Costume"), ("Coins", "Coin"), ("Gems", "Gem")):
    assert ITEM_NAME_GROUPS[_sg] == ITEM_NAME_GROUPS[_p], f"{_sg} does not match {_p}"
# "Progressive" is every Progressive <something> -- the world unlocks AND the
# progressive upgrades -- because that is what the word means to someone typing
# it. The narrower phrasings mean the unlocks alone.
for _pa in ("Progressive Unlock", "Progressive Unlocks", "Unlock", "Unlocks"):
    assert ITEM_NAME_GROUPS[_pa] == ITEM_NAME_GROUPS["World Unlocks"],         f"{_pa} does not resolve to the unlocks"
assert ITEM_NAME_GROUPS["Progressive"] == ITEM_NAME_GROUPS["Progressives"]
assert ITEM_NAME_GROUPS["World Unlocks"] <= ITEM_NAME_GROUPS["Progressive"],     "the Progressive group does not contain every world unlock"
assert ITEM_NAME_GROUPS["Progressive"] > ITEM_NAME_GROUPS["World Unlocks"],     "the Progressive group is only the unlocks; the progressive upgrades are "     "named Progressive too and a player typing it means those as well"
assert ITEM_NAME_GROUPS["Progressive"] - ITEM_NAME_GROUPS["World Unlocks"]     <= ITEM_NAME_GROUPS["Upgrades"],     "the Progressive group picked up something that is neither an unlock nor an upgrade"

# Every item hintable as part of something. The currencies and the costume were
# in no group at all, so there was no way to ask about them as a set.
_allnames = {i.name for i in ALL_ITEMS}
_ungrouped = _allnames - set().union(*ITEM_NAME_GROUPS.values())
assert not _ungrouped, f"items in no hint group: {sorted(_ungrouped)}"
# A NAME THIS APWORLD INVENTS AS A PREFIX MUST ALSO BE A GROUP NAME.
#
# AP resolves a hint by fuzzy match and refuses outright when the top two
# candidates score within 5 of each other: "Too many close matches for
# 'Progressive', did you mean 'Progressive Ancient Egypt'?" -- and hints
# nothing. Thirteen items sharing a "Progressive " prefix guaranteed exactly
# that for the single most natural thing to type, which is how the unlocks
# became unhintable by name. A group name is an exact match and never reaches
# the fuzzy path.
#
# Scoped to the prefixes THIS apworld chose. Plant names come from the game and
# share first words too (Fire, Primal, Pea), but those are real distinct items a
# player names in full, not categories, and they cannot be renamed anyway.
_OUR_PREFIXES = ("Progressive",)
for _pre in _OUR_PREFIXES:
    _members = {n for n in _allnames if n.startswith(_pre + " ")}
    assert len(_members) > 1, f"{_pre} is no longer a shared prefix; drop this check"
    assert _pre in ITEM_NAME_GROUPS, (
        f"{len(_members)} items start with '{_pre} ' but '{_pre}' names no "
        f"group, so !hint {_pre} refuses as 'too many close matches'")
    assert _members <= ITEM_NAME_GROUPS[_pre], (
        f"'{_pre}' group misses {sorted(_members - ITEM_NAME_GROUPS[_pre])}")

# A group naming something that is not an item would hint nothing.
for _g, _members in ITEM_NAME_GROUPS.items():
    assert _members, f"hint group {_g} is empty"
    _ghost = _members - _allnames
    assert not _ghost, f"group {_g} names non-items: {sorted(_ghost)}"
# Negative currency stays out of Coins/Gems: those are traps, and answering
# "where are my coins" with the places that take them away is worse than
# answering nothing.
assert not (ITEM_NAME_GROUPS["Currency"] & ITEM_NAME_GROUPS["Traps"]),     "a currency trap leaked into the Currency group"
# ...and a real seed's unlocks are all in the group, not just the static table.
_hw, _ = run("hint groups", shopsanity=1)
_pool_unlocks = {i.name for i in _hw.multiworld.itempool
                 if i.name in _unlocknames}
assert _pool_unlocks <= ITEM_NAME_GROUPS["World Unlocks"],     f"unlocks in the pool but not the group: {sorted(_pool_unlocks - ITEM_NAME_GROUPS['World Unlocks'])}"
assert not {i.name for i in _hw.multiworld.itempool if i.name.endswith(" Key")},     "a World Key reached a real seed's pool"

# THE SUN PLANTS GROUP. A sun producer is the one plant every seed needs and the
# one plant never handed over -- starting_plants refuses to grant one, and
# Ancient Egypt expects one from level 6 -- so it is worth asking about on its
# own rather than through !hint Plants, which answers with any of 135.
#
# Pinned as the five names, sourced from SUN_PRODUCER_PLANTS in constants, so
# the group cannot silently drift from the list the egypt6 gate actually reads.
# Solar Tomato was dropped from that list once already.
assert ITEM_NAME_GROUPS["Sun Plants"] == set(C.SUN_PRODUCER_PLANTS), \
    f"Sun Plants is {sorted(ITEM_NAME_GROUPS['Sun Plants'])}, not the gate's list"
assert len(ITEM_NAME_GROUPS["Sun Plants"]) == 5, \
    f"{len(ITEM_NAME_GROUPS['Sun Plants'])} sun plants, expected 5"

# ...and it is strictly narrower than Plants, or it answers nothing new.
assert ITEM_NAME_GROUPS["Sun Plants"] < ITEM_NAME_GROUPS["Plants"], \
    "Sun Plants is not a subset of Plants"

# Every spelling a player is likely to type resolves to the same group. AP
# matches a group name EXACTLY; a near miss falls through to fuzzy-matching a
# single item and hints one plant instead of the group, which looks like it
# worked.
for _alias in ("Sun Plant", "Sun", "Sun Producers", "Sun Producer", "Sunflowers"):
    assert ITEM_NAME_GROUPS.get(_alias) == ITEM_NAME_GROUPS["Sun Plants"], \
        f"!hint {_alias} does not resolve to the Sun Plants group"

# ...and every one of them is in a real seed's pool, or the hint has nothing to
# point at. The floor keeps at least one in even the smallest seed; a default
# seed keeps all five.
_sw, _ = run("hint groups: sun", shopsanity=1)
_sun_pool = ITEM_NAME_GROUPS["Sun Plants"] & {i.name for i in _sw.multiworld.itempool}
assert _sun_pool == ITEM_NAME_GROUPS["Sun Plants"], \
    f"sun plants missing from a default seed's pool: {sorted(ITEM_NAME_GROUPS['Sun Plants'] - _sun_pool)}"
_sw1, _ = run("hint groups: sun, one world", world_count=1)
assert ITEM_NAME_GROUPS["Sun Plants"] & {i.name for i in _sw1.multiworld.itempool}, \
    "an Egypt-only seed has no sun plant to hint"
print(f"hint groups: {len(ITEM_NAME_GROUPS)} buckets over {len(_allnames)} items, "
      f"World Unlocks covers all {len(_pool_unlocks)} unlocks in the pool")

# No goal or victory condition may depend on one, in any goal mode.
for _gt in (0, 1, 2):
    _gw, _gsd = run(f"unreachable: goal_type={_gt}", goal_type=_gt, worlds_required=11)
    for _g in _gsd["goal_locations"]:
        assert _g not in C.UNREACHABLE_LOCATIONS, f"goal {_g} is unreachable in game"
    assert _gsd["modern_day_victory"] not in C.UNREACHABLE_LOCATIONS

# ── currency traps ──────────────────────────────────────────────────────────
# The client reads the amount straight off the item name, so the names have to
# stay parseable by its regex -- one leading minus, a number, then the currency.
import re as _re_ct
from apstub import ItemClassification as _IC_ct
_ct_re = _re_ct.compile(r"^-(\d+) (Coins|Gems)$")
for _t in CURRENCY_TRAP_ITEMS:
    assert _ct_re.match(_t.name), f"client cannot parse trap name {_t.name!r}"
    assert _t.classification == _IC_ct.trap, f"{_t.name} is not classified as a trap"
# ...and must NOT be mistaken for a grant by the client's positive regex.
_grant_re = _re_ct.compile(r"^(\d+) (Coins|Gems)$")
for _t in CURRENCY_TRAP_ITEMS:
    assert not _grant_re.match(_t.name), f"{_t.name} would read as a grant"
# The pool builder only ever hands out TRAP_CYCLE entries, so a trap missing
# from the pool would exist as an item nothing could ever deal.
assert {COIN_TRAP, GEM_TRAP} <= {t.name for t in TRAP_POOL},     "currency traps are not in the trap pool, so nothing would deal them"
# They are traps, not filler -- get_filler_item_name must never return one.
assert not ({COIN_TRAP, GEM_TRAP} & {f.name for f in FILLER_POOL}),     "a currency trap leaked into the filler pool"

# A seed with traps on actually contains them, and one with traps off does not.
# ALL_WORLDS: traps come out of filler, and filler is what is left after the
# plants. The default goal trims each world at its World Key level, which
# leaves a seed too small to have any -- the same reason a 3-world seed has
# never had traps. See the pool-block sizing note.
_wt, _ = run("currency traps at 100%", trap_percentage=100, **ALL_WORLDS)
_names = [i.name for i in _wt.multiworld.itempool]
assert COIN_TRAP in _names and GEM_TRAP in _names, "traps on: no currency traps dealt"
_wn, _ = run("traps off", trap_percentage=0)
_off = {i.name for i in _wn.multiworld.itempool}
assert not ({COIN_TRAP, GEM_TRAP} & _off), "traps off: a currency trap was still dealt"
print("currency traps: dealt when asked for, absent when not")
_allcn = [cn for _, cns in UPGRADE_GROUPS for cn in cns]
assert len(set(_allcn)) == 14 == UPGRADE_ITEM_COUNT, "codenames not 14 distinct"
assert len(UPGRADE_ITEM_TO_CNS) == 8, "expected 8 distinct upgrade item names"
# codenames must match the game's UpgradeEnum exactly
GAME_UPGRADES = {
    "upgrade_starting_sun_lvl1", "upgrade_starting_sun_lvl2",
    "upgrade_pf_slots_lvl1", "upgrade_pf_slots_lvl2", "upgrade_wallnut_firstaid",
    "upgrade_pf_refresh", "upgrade_sunshovel_lvl1", "upgrade_sunshovel_lvl2",
    "upgrade_sunshovel_lvl3", "upgrade_7_slots", "upgrade_8_slots",
    "upgrade_manual_mowers_1", "upgrade_manual_mowers_2", "upgrade_sky_shield",
}
assert set(_allcn) == GAME_UPGRADES, set(_allcn) ^ GAME_UPGRADES
# the 5 shop-only upgrades must still be items
from pvz2gardendless.constants import SHOP_UPGRADE_COMMODITIES
assert set(SHOP_UPGRADE_COMMODITIES) <= set(_allcn)
# a progressive prefix must be a valid partial state: every group's codenames
# are interchangeable in effect, so any prefix length is legal by construction
for _n, _c in UPGRADE_GROUPS:
    assert len(_c) >= 1 and len(set(_c)) == len(_c), _n
print("progressive groups:", {n: len(c) for n, c in UPGRADE_GROUPS})
print("\nupgrade item IDs:", min(i.code for i in UPGRADE_ITEMS),
      "-", max(i.code for i in UPGRADE_ITEMS))

print("\nALL CHECKS PASSED")

# ── early_world_keys ────────────────────────────────────────────────────────
# An ITEM rule, not an access rule: it must change where fill may put the world
# unlocks and nothing else. Locations, pool size and logic all have to come out
# identical.
from pvz2gardendless.constants import is_early_region, KEYED_WORLDS
from apstub import MultiWorld as _MW


def _key_placement(**kw):
    mw = _MW()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    w.generate_early(); w.create_regions(); w.set_rules(); w.create_items()
    # A synthetic unlock rather than one drawn from the pool: a 1-world seed
    # has none for that world at all, and `all()` over an empty set is
    # vacuously true, which would silently pass the whole probe.
    #
    # The unlocks are what the option acts on now -- they replaced the World
    # Key items -- so probing with a Key would test a rule that no longer
    # applies to anything in the pool.
    probe_key = w.create_item("Progressive Pirate Seas")
    allowed = denied = 0
    late_open = []
    for r in mw.regions:
        for loc in r.locations:
            ok = loc.item_rule(probe_key)
            if ok:
                allowed += 1
                if not is_early_region(r.name):
                    late_open.append(f"{r.name}/{loc.name}")
            else:
                denied += 1
    return mw, allowed, denied, late_open


# off: nothing is forbidden anywhere
_mw, _allowed, _denied, _late = _key_placement(early_world_keys=0)
assert _denied == 0, f"option off still forbade {_denied} locations"
print(f"\nearly_world_keys off: all {_allowed} locations accept keys")

# on: every late location refuses keys, every early one still takes them
_mw, _allowed, _denied, _late = _key_placement(early_world_keys=1)
assert not _late, f"late locations still accept keys: {_late[:5]}"
assert _denied > 0, "option on forbade nothing"
_unlock_names = {f"Progressive {_w}" for _w in C.WORLD_REGIONS}
_keys_needed = sum(1 for i in _mw.itempool if i.name in _unlock_names)
assert _allowed >= _keys_needed, \
    f"only {_allowed} spots left for {_keys_needed} unlocks -- fill would fail"
print(f"early_world_keys on:  {_allowed} legal spots, {_denied} closed off, "
      f"{_keys_needed} unlocks to place")

# Modern Day is 53 locations of endgame content, so it must refuse them too.
_probe_unlocks = [i for i in _mw.itempool if i.name in _unlock_names]
assert _probe_unlocks, "no unlocks in the pool, so this probe proves nothing"
for _r in _mw.regions:
    if _r.name == "Modern Day":
        for _loc in _r.locations:
            assert not all(_loc.item_rule(i) for i in _probe_unlocks), \
                f"Modern Day location {_loc.name} accepts a world unlock"

# The rule must not touch anything that is not a key.
# Any plant this seed actually shipped. Not a named one: since the attacker
# half of the egypt6 gate went, plants are ordinary useful items and a
# small seed can trim any particular one away.
_plant_names = {p.name for p in PLANT_ITEMS}
_plant = next(i for i in _mw.itempool if i.name in _plant_names)
_blocked = [l for r in _mw.regions for l in r.locations if not l.item_rule(_plant)]
assert not _blocked, f"non-key items were forbidden too: {_blocked[:3]}"

# ...and it must not disturb the seed's shape or its logic.
_a, _sda = run("keys anywhere", early_world_keys=0, world_count=4)
_b, _sdb = run("keys early", early_world_keys=1, world_count=4)
assert _a.enabled_worlds == _b.enabled_worlds
assert _sda["goal_locations"] == _sdb["goal_locations"], "key rule changed logic"
assert len(_a.active_locations()) == len(_b.active_locations())

# Smallest seeds still have somewhere to put their keys, with the side paths in
# or out. A one-world seed without them is only 101 locations, so this is also
# the tightest case for the useful-plant trim in create_item_pool.
for _sp, _counts in ((1, (1, 2, 3)), (0, (1, 2, 3))):
    for _wc in _counts:
        _mw2, _al, _dn, _lt = _key_placement(early_world_keys=1, world_count=_wc,
                                             include_side_paths=_sp)
        _need = sum(1 for i in _mw2.itempool if i.name.endswith(" Key"))
        assert not _lt and _al >= _need, \
            f"side_paths={_sp} world_count={_wc}: {_al} spots for {_need} keys"
print("early_world_keys holds down to the smallest seed each setting allows")

# ── include_danger_rooms ────────────────────────────────────────────────────
# DANGER_ROOM_LOCATIONS is a hand-written set in constants.py, so it can drift
# from what the client actually maps. Pin it to the derivation it claims: every
# location whose LOC_LEVELS codename contains "dangerroom", and nothing else.
# The levels that UNLOCK a room are ordinary numbered levels (egypt12, pirate4,
# beach20) -- naming one of those would delete a real level from the seed. They
# used to be spotted by a "Dangerroom " name prefix; since world locations are
# named for their level id that prefix is gone, so the unlock set now comes
# from DANGER_ROOM_UNLOCK, which is where the pairing actually lives.
import re as _re
from pvz2gardendless.build_pvzge_ap import TMPPATCH_CONTENT as _JS
from pvz2gardendless.locations import ALL_LOCATIONS as _ALL

_blk = _JS.split("const LOC_LEVELS = {", 1)[1].split(chr(10) + "  };", 1)[0]
_lvl = dict(_re.findall(r"'([^']+)':'([^']+)'", _blk))
_derived = {l.name for l in _ALL if "dangerroom" in _lvl.get(l.name, "")}
assert _derived == set(C.DANGER_ROOM_LOCATIONS), (
    "DANGER_ROOM_LOCATIONS drifted from LOC_LEVELS: "
    f"missing {sorted(_derived - set(C.DANGER_ROOM_LOCATIONS))[:5]}, "
    f"extra {sorted(set(C.DANGER_ROOM_LOCATIONS) - _derived)[:5]}")
_unlocks = set(C.DANGER_ROOM_UNLOCK.values())
assert _unlocks and not (_unlocks & set(C.DANGER_ROOM_LOCATIONS)),     "an unlock level was swept into DANGER_ROOM_LOCATIONS"
# Every room that can be built names the level that unlocks it, and that level
# is a real location. A room missing from DANGER_ROOM_UNLOCK gets no rule at
# all, which looks identical to the rule working -- constants.py raises on it,
# this pins the other half: the unlock names have to resolve.
_buildable_rooms = set(C.DANGER_ROOM_LOCATIONS) - set(C.UNREACHABLE_LOCATIONS)
assert set(C.DANGER_ROOM_UNLOCK) == _buildable_rooms, (
    "DANGER_ROOM_UNLOCK does not cover every buildable room: "
    f"{sorted(_buildable_rooms ^ set(C.DANGER_ROOM_UNLOCK))}")
_region_of = {l.name: l.region for l in _ALL}
_world_of = {r: w for w, rs in C.WORLD_REGIONS.items() for r in rs}
for _room, _ul in C.DANGER_ROOM_UNLOCK.items():
    assert _ul in _region_of, f"{_room} unlocks off unknown location {_ul}"
    assert _ul not in C.DANGER_ROOM_LOCATIONS, \
        f"{_room} unlocks off {_ul}, which is itself a Danger Room"
    # Same world, or the rule reaches across a world the seed may have dropped
    # -- and rules.py would raise looking the unlock location up. Not the same
    # REGION: Egypt's rooms sit in Ancient Egypt Late while their unlock levels
    # are in Mid1/Mid2.
    assert _world_of[_region_of[_room]] == _world_of[_region_of[_ul]], \
        f"{_room} and its unlock {_ul} are in different worlds"
print(f"\nDANGER_ROOM_LOCATIONS: {len(_derived)} rooms "
      f"({len(_buildable_rooms)} buildable, all gated on their unlock level), "
      f"{len(_unlocks)} unlock levels correctly left alone")

# Every world: _buildable_rooms is derived over the whole game, and the default
# seed is eleven worlds, so Kongfu Temple's and Aerial Fortress's rooms would
# read as "removed by the option" when the world was never in the seed.
_dr_off, _ = run("danger rooms off", include_danger_rooms=0, **ALL_WORLDS)
_dr_on, _ = run("danger rooms on", include_danger_rooms=1, **ALL_WORLDS)
_off_names = {l.name for l in _dr_off.active_locations()}
_on_names = {l.name for l in _dr_on.active_locations()}
assert _on_names - _off_names == _buildable_rooms,     "the option removed something other than the Danger Rooms"
assert not (_off_names & set(C.DANGER_ROOM_LOCATIONS)), "a Danger Room survived"
assert _unlocks <= _off_names, "an unlock level went with the rooms"
# The two rooms nothing in the game can launch are never built, under any
# combination -- kongfu_dangerroom4 has no map node and no level awards its
# trophy; mixed_dangerroom2 has neither node nor trophy.
for _sp in (0, 1):
    for _drs in (0, 1):
        _u, _ = run(f"orphan rooms: side_paths={_sp} danger_rooms={_drs}",
                    include_side_paths=_sp, include_danger_rooms=_drs)
        _un = {l.name for l in _u.active_locations()}
        assert not (_un & {"kongfu_dangerroom4", "mixed_dangerroom2"}), \
            "an unreachable Danger Room was built"
# The goal must survive: no goal location is a Danger Room, in any goal mode.
for _gt in (0, 1, 2):
    _gw, _gsd = run(f"danger rooms off, goal_type={_gt}",
                    include_danger_rooms=0, goal_type=_gt, worlds_required=11)
    _gnames = {l.name for l in _gw.active_locations()}
    for _g in _gsd["goal_locations"]:
        assert _g in _gnames, f"goal {_g} was removed with the Danger Rooms"
print(f"include_danger_rooms removes exactly the {len(_buildable_rooms)} rooms "
      "and no goal location")

# ── the gate the player meets is the gate fill reasoned about ───────────────
# slot_data.world_gates is what the CLIENT enforces: it refuses to start a
# level whose stretch the player has not unlocked. regions.py puts that same
# level in a region behind the same unlock. If the two ever disagree, a seed is
# either unwinnable (a location fill filled, that the player cannot reach) or
# trivially open (a level the client lets you play that logic thought was
# gated) -- and nothing else in the suite would notice.
#
# Both sides call world_stretches, so this pins that they are called with the
# same input as well: same worlds, same active locations, same order.
# Every world, because the assertions below count gated worlds and gated
# locations against the whole game rather than against this seed.
_gw, _gsd = run("world gates", include_side_paths=1,
                include_danger_rooms=1, **ALL_WORLDS)
_gates = _gsd["world_gates"]
# How many unlocks each stretch needs comes from constants, per world: a keyed
# world's opening wants one (that is the unlock which replaced its World Key),
# while Ancient Egypt's opening and its egypt6 checkpoint want none. That
# checkpoint is the row worth reading here -- logic 0, client 0, for a region
# that is nonetheless gated, because a sun producer is logic only and the
# client must leave those levels startable.
_SUFFIXES = ("", " Early", " Mid", " Late")

_gate_need = {}
for _w, _g in _gates.items():
    for _i, _part in enumerate(_g["stretches"]):
        for _n in _part:
            _gate_need[_n] = _i + 1

_mismatch, _unmapped = [], []
for _r in _gw.multiworld.regions:
    _suffix = _owner = None
    for _world in C.WORLD_REGIONS:
        if _r.name == _world:
            _suffix, _owner = "", _world
        elif _r.name.startswith(_world) and _r.name[len(_world):] in _SUFFIXES:
            _suffix, _owner = _r.name[len(_world):], _world
        if _suffix is not None:
            break
    if _suffix is None:
        continue  # not a world stretch: Tutorial, Shop, a side path
    _want = C.progressive_need(_owner, _suffix)
    for _loc in _r.locations:
        _have = _gate_need.get(_loc.name, 0)
        if _have != _want:
            _mismatch.append((_loc.name, _r.name, f"logic {_want}", f"client {_have}"))

assert not _mismatch, (
    f"{len(_mismatch)} location(s) where the client's gate and the region it "
    f"was built into disagree: {_mismatch[:4]}")

# Every gated name has to resolve to a game level, or the client skips it and
# the level is silently playable. _lvl is LOC_LEVELS, read out of the client.
_unmapped = sorted(n for n in _gate_need if n not in _lvl)
assert not _unmapped, (
    f"{len(_unmapped)} gated location(s) have no LOC_LEVELS entry, so the "
    f"client cannot enforce them: {_unmapped[:5]}")

# ...and the gates have to actually gate something, or all of the above passes
# on an empty table.
# Every level of every keyed world, which is most of the seed but not the side
# paths, the Danger Room entrances' own regions or the tutorial.
assert len(_gate_need) > 500, f"only {len(_gate_need)} gated locations, expected most of the seed"
assert len(_gates) == 13, f"{len(_gates)} worlds have gates, expected 13"
for _w, _g in _gates.items():
    assert _g["item"] == f"Progressive {_w}", f"{_w} gates on {_g['item']}"
    # A keyed world's whole level list is gated, in three bands; Ancient Egypt
    # opens with nothing so it has two.
    _want_bands = C.progressive_count(_w)
    assert len(_g["stretches"]) == _want_bands, \
        f"{_w} has {len(_g['stretches'])} locked stretches, expected {_want_bands}"
    assert all(_g["stretches"]), f"{_w} has an empty stretch"
# Every level of a keyed world is gated -- its opening included, since entering
# the world is itself an unlock now. What the client may start for free is
# exactly: Ancient Egypt, the tutorial, and the side paths (which the game
# gates behind the level that reveals them, so they need no help here).
_placed = {l.name: r.name for r in _gw.multiworld.regions for l in r.locations}
_free = sorted(n for n, r in _placed.items()
               if n in _lvl and n not in _gate_need)
_free_bad = [n for n in _free
             if not (_placed[n].startswith("Ancient Egypt")
                     or _placed[n] == "Tutorial"
                     or _placed[n] in C.SIDE_PATH_REGIONS)]
assert not _free_bad, \
    f"levels in a keyed world are startable with no unlock: {_free_bad[:6]}"
print(f"world_gates agrees with the region graph on all "
      f"{sum(len(l.locations) for l in _gw.multiworld.regions)} placed locations "
      f"({len(_gate_need)} gated across {len(_gates)} worlds)")

# Ancient Egypt's cut is the one stated in the option text and the docs, so it
# is pinned as literals rather than re-derived from the thing under test.
_egypt = _gates["Ancient Egypt"]
assert "egypt9" in _egypt["stretches"][0] and "egypt25" in _egypt["stretches"][0], \
    "Ancient Egypt's middle stretch should run egypt9-25"
assert "egypt26" in _egypt["stretches"][1] and "egypt35" in _egypt["stretches"][1], \
    "Ancient Egypt's last stretch should run egypt26-35"
assert not any(_n in _gate_need for _n in ("egypt1", "egypt5", "egypt6", "egypt8")),     "Ancient Egypt's opening runs to egypt8 and needs no unlock"
print("Ancient Egypt is 1-5 / 6-8 / 9-25 / 26-35: the sun expectation, its "
      "World Key level and its Zomboss")

# ── each world's completion goal is really its last level ───────────────────
# Every world is built the same way: a Zomboss at the mid-world trophy
# (egypt25, dino32, eighties32) and a "2.0" rematch at the final level
# (egypt35, dino42, eighties42). The completion goal has to be the latter.
#
# HARDCODED from the game's own world table (WORLDMAPS[w].LEVELS in
# import/01/01c3025f0.json), not derived from LOC_LEVELS. Deriving it would
# restate whatever the location list happens to hold, which is exactly the bug
# being pinned: Neon Mixtape Tour's completion goal was eighties32 because the
# location list stopped there, so a derived "highest level in this world" test
# would have called it correct. The suite has no game source to read, so the
# expected values live here.
_WORLD_FINAL_LEVEL = {
    "egypt": 35, "pirate": 35, "cowboy": 35, "future": 35, "dark": 30,
    "beach": 42, "iceage": 40, "lostcity": 42, "kongfu": 48, "eighties": 42,
    "dino": 42,
    # Modern Day joined the goal tables on 2026-08-23. Its level order is
    # modern1..modern31, the ten Zomboss rematches, then modern35..modern44 --
    # so 44 is the last level, and there is no modern32/33/34 to confuse it
    # with.
    "modern": 44,
}
from pvz2gardendless.locations import (WORLD_COMPLETION_LOCS as _WC,
                                      WORLD_ZOMBOSS_LOCS as _WT)
_seen = set()
for _n in _WC:
    _lv = _lvl.get(_n)
    assert _lv, f"completion goal {_n} has no LOC_LEVELS entry"
    _m = _re.match(r"^([a-z]+)(\d+)$", _lv)
    assert _m, f"completion goal {_n} maps to {_lv}, which is not a numbered level"
    _w, _num = _m.group(1), int(_m.group(2))
    assert _w in _WORLD_FINAL_LEVEL, f"unknown world {_w} in completion goals"
    assert _num == _WORLD_FINAL_LEVEL[_w], (
        f"{_n} -> {_lv}, but {_w} really ends at {_w}{_WORLD_FINAL_LEVEL[_w]}; "
        "a completion goal short of the world's last level makes that world "
        "cheaper than every other")
    _seen.add(_w)
assert len(_seen) == len(_WC), "two completion goals in the same world"
# ...and completion must be a strictly later ask than the trophy, or the two
# goal types collapse into each other for that world.
_both = set(_WC) & set(_WT)
assert not _both, f"location used as BOTH zomboss and completion goal: {sorted(_both)}"
print(f"all {len(_WC)} completion goals are their world's real final level, "
      "and none doubles as a trophy goal")

# ── world locations are named for their level id ────────────────────────────
# Every location in a world (and the tutorial) is called exactly what the game
# calls the level: egypt2, not "Cabbagepult Unlock". The reward names described
# something the player does not receive under AP -- the client clears the
# game's own plant grants and hands out only what the multiworld sent -- and
# they made the client's Modern Day lookup depend on a list of plant names.
#
# Side paths are deliberately exempt: a quest level's number means nothing on
# its own, so those keep readable names (Goo Peashooter 1, Aloe Unlock).
_wl = [l for l in _ALL if not l.is_shop
       and (l.region in C.ALL_WORLD_REGIONS or l.region == "Tutorial")]
# Neon Mixtape Tour is the one world that does NOT follow this, on purpose:
# the game calls its levels "eighties" and nothing about that word says Neon
# Mixtape Tour, so the AP names are neon1..neon42. Checked explicitly below
# rather than waved through -- the game codename must stay eighties, since
# that is what the client hands to the game.
_misnamed = [(l.name, _lvl[l.name]) for l in _wl
             if _lvl[l.name] != l.name and not l.name.startswith("neon")]
assert not _misnamed, \
    f"world locations not named for their level id: {_misnamed[:5]}"

# Every neon* location points at the eighties* level of the SAME number, and
# nothing in the seed is called eighties any more. A half-finished rename would
# leave a location the client cannot resolve to a level.
_neon = [l for l in _ALL if l.name.startswith("neon")]
_badneon = [(l.name, _lvl[l.name]) for l in _neon
            if _lvl[l.name] != "eighties" + l.name[len("neon"):]]
assert not _badneon, f"neon locations pointing at the wrong level: {_badneon[:5]}"
_stale = [l.name for l in _ALL if l.name.startswith("eighties")]
assert not _stale, f"locations still named eighties: {_stale[:5]}"
assert len(_neon) == 44, f"expected 44 neon locations, got {len(_neon)}"
print(f"Neon Mixtape Tour: {len(_neon)} locations renamed neon*, all still "
      f"pointing at their eighties* level")
# ...and the client's Modern Day set is exactly the 'modern' prefix, which is
# what getRegion() relies on now that the thirteen-prefix list is gone.
_md_region = {l.name for l in _ALL if l.region == "Modern Day"}
_md_prefix = {l.name for l in _ALL if not l.is_shop and l.name.startswith("modern")}
assert _md_region == _md_prefix, \
    f"'modern' prefix no longer matches the Modern Day region: {_md_region ^ _md_prefix}"
print(f"all {len(_wl)} world/tutorial locations are named for their level id, "
      f"and the {len(_md_region)} Modern Day ones are exactly the 'modern' prefix")

# ── side paths are "<Plant> <N>" ────────────────────────────────────────────
# A quest level's number means nothing on its own -- conceal7 says neither what
# the quest is nor what it gives -- so these are named for the plant the levels
# declare in PlantToIntroduce, with N taken off the codename so it matches the
# epic map's own node labels. The four mint quests (Appease, Conceal, Enlighten,
# Reinforce) introduce several plants each and declare none, so they carry the
# mint's name instead.
#
# Checked as a shape rather than a table: the point is that every side-path
# location is "<something> <number>" and every path uses ONE label, which is
# what stops a path drifting back to half codenames and half reward names.
_sp_locs = [l for l in _ALL if l.region in C.SIDE_PATH_REGIONS
            and l.name not in C.UNREACHABLE_LOCATIONS]
_bad_shape = [l.name for l in _sp_locs
              if not _re.fullmatch(r"[A-Z][A-Za-z\- ]*[a-z] \d+(_\d+)?", l.name)]
assert not _bad_shape, f"side-path locations not '<Plant> <N>': {_bad_shape[:5]}"
_labels = collections.defaultdict(set)
for l in _sp_locs:
    _labels[l.region].add(l.name.rsplit(" ", 1)[0])
_split = {r: sorted(v) for r, v in _labels.items() if len(v) != 1}
assert not _split, f"side paths using more than one label: {_split}"
# the number has to be the level's own, or the name lies about which level it is
_off = [(l.name, _lvl[l.name]) for l in _sp_locs
        if not _lvl[l.name].endswith(l.name.rsplit(" ", 1)[1])]
assert not _off, f"side-path number does not match its level id: {_off[:5]}"
print(f"all {len(_sp_locs)} side-path locations are '<Plant> <N>' across "
      f"{len(_labels)} paths, one label each, numbered off their level id")

# Neon Mixtape Tour runs 1-42 with no gaps (it used to stop at 32).
_e = {int(_m.group(1)) for _v in _lvl.values()
      for _m in [_re.match(r"^eighties(\d+)$", _v)] if _m}
assert _e == set(range(1, 43)), \
    f"Neon Mixtape Tour is missing levels: {sorted(set(range(1,43)) - _e)}"
print(f"Neon Mixtape Tour covers eighties1-42 with no gaps")

# ── small seeds trim plants rather than failing ─────────────────────────────
# A one-world seed is 54 locations (63 with shopsanity) against a block that
# wants 55 progression plants alone. Useful plants go first -- no rule names
# them, so shipping fewer costs reachability nothing -- and then the
# progression plants themselves, down to a floor of one per group any rule
# names.
#
# That floor is what makes an Egypt-only seed possible at all. It became safe
# on 2026-08-23, when the last per-world plant requirement went: every
# surviving rule is a has_any() over a group, so one plant from each is all
# logic can ever need. The unlocks and upgrades never give.
from apstub import ItemClassification as _IC
# Which plants are progression is a per-SLOT question since 2026-08-23: the
# static table carries the sun producers and the world entry plants, and each
# slot draws LOGIC_ATTACKER_COUNT cheap attackers of its own on top. Reading
# the static classification here would understate the block by those 10 and
# call a correctly trimmed pool broken.
_unlock_names = {f"Progressive {_w}" for _w in C.WORLD_REGIONS}

for _label, _kw in (("1 world", dict(world_count=1)),
                    ("1 world + shopsanity", dict(world_count=1, shopsanity=1)),
                    ("2 worlds", dict(world_count=2)),
                    ("13 worlds", dict(world_count=13))):
    _w, _ = run(f"trim: {_label}", include_side_paths=0, worlds_required=11, **_kw)
    _mwT = _w.multiworld
    _names = [i.name for i in _mwT.itempool]
    _nameset = set(_names)

    # The floor holds in every seed, however small: each group a rule names
    # keeps at least one member, or that gate is a wall. That is the two Egypt
    # checkpoint groups, plus one group per requirement of each world the seed
    # ENABLED that names entry plants -- Lily Pad if Big Wave Beach is in, and
    # nothing at all for a world left out, whose entrance rule is never built.
    _floor_groups = [(C.SUN_PRODUCER_PLANTS, "sun producers"),
                     (C.CHEAP_ATTACKER_PLANTS, "cheap attackers")]
    for _ew in sorted(_w.enabled_worlds):
        for _grp in C.WORLD_ENTRY_PLANTS.get(_ew, []):
            _floor_groups.append((_grp, f"{_ew} entry plants"))
    for _group, _gname in _floor_groups:
        # A group with a granted member is already satisfied and reserves
        # nothing, so the pool need not carry one. The cheap attackers are
        # always in that case: the starter is drawn from them and precollected.
        if set(_group) & set(_w.starting_plants):
            continue
        assert set(_group) & _nameset, f"{_label}: no {_gname} left in the pool"

    # Unlocks are never trimmed -- but the COUNT is sized to the stretches this
    # slot builds, so a goal trim legitimately ships fewer.
    _gt2 = _w.options.goal_type.value
    _pg2 = bool(_w.options.include_levels_past_goal)
    _want_unlocks = sum(C.progressive_count(_x, _gt2, _pg2)
                        for _x in _w.enabled_worlds)
    _got_unlocks = sum(1 for n in _names if n in _unlock_names)
    assert _got_unlocks == _want_unlocks, (
        f"{_label}: {_got_unlocks} unlocks, expected {_want_unlocks}")
    # Upgrades give ONLY when the seed cannot hold them, which needs the pool to
    # be completely full -- they gate nothing, so they yield before a plant does.
    if _w.options.shuffle_upgrades:
        _ups = {u.name for u in W.items.UPGRADE_ITEMS}
        _n_ups = sum(1 for n in _names if n in _ups)
        if _n_ups != C.UPGRADE_ITEM_COUNT:
            # Fillable locations, not all of them: each goal level already
            # holds its locked McGuffin.
            assert len(_names) == (len(_w.active_locations())
                                   - len(_w.goal_locations())), (
                f"{_label}: upgrades trimmed in a seed with room to spare")

    # A seed with room keeps every progression plant; only a seed short of
    # room may drop any, and then only after every useful plant has gone.
    # Minus what the player was handed: a granted plant is deliberately kept
    # out of the pool rather than shipped twice, so its absence is correct and
    # not a trim. Its rule is satisfied by the grant itself.
    _granted = set(_w.starting_plants)
    _slot_prog = W.items.slot_progression_plants(_w) - _granted
    _all_plants = {p.name for p in W.items.PLANT_ITEMS} - _granted
    _missing = _slot_prog - _nameset
    _useful_left = sum(1 for n in _names
                       if n in _all_plants and n not in _slot_prog)
    if _missing:
        assert not _useful_left, \
            f"{_label}: dropped {len(_missing)} progression plants while still " \
            f"shipping {_useful_left} useful ones"
    # Fillable only: the goal levels hold locked McGuffins.
    _fillable = len(_w.active_locations()) - len(_w.goal_locations())
    assert len(_names) == _fillable, \
        f"{_label}: pool {len(_names)} does not fill {_fillable} fillable locations"

# The default seed must not be trimming anything -- if it is, the pool and the
# location count have drifted and every "every X is in the pool" claim above is
# quietly weaker than it reads.
_wfull, _ = run("trim: default seed", )
assert (W.items.slot_progression_plants(_wfull) - set(_wfull.starting_plants)) \
    <= {i.name for i in _wfull.multiworld.itempool}, \
    "the default seed is trimming progression plants"

print("small seeds trim useful plants, keeping every progression plant and key")

# ── the floor covers a world's entry plants, not only Egypt's two groups ────
# This one calls create_item_pool DIRECTLY with a squeezed pool_size instead of
# going through an option combination, because no option combination reaches it:
# every world past Egypt adds ~40 locations against only 3 unlocks, so a seed
# large enough to contain Big Wave Beach is far too large to trim progression
# plants at all. The floor is defensive, and a defence nothing exercises is a
# defence that rots -- squeezing pool_size is the smallest honest way to run it.
#
# Proved by mutation: delete the WORLD_ENTRY_PLANTS loop from the floor in
# items.py and this fails, while every option-driven test above still passes.
_ENTRY_WORLDS = ["Big Wave Beach", "Far Future", "Jurassic Marsh", "Dark Ages"]
_wE, _ = run("entry-plant floor", world_count=5, enabled_worlds=_ENTRY_WORLDS)
assert set(_ENTRY_WORLDS) <= _wE.enabled_worlds, _wE.enabled_worlds

# Room for the unlocks, the upgrades and a handful of plants: well under the
# progression block, so the trim has to run and the floor is what decides what
# survives. The upgrades have to be counted -- they are added to the pool before
# the plants and are as non-negotiable as the unlocks, so leaving them out of
# the sum makes create_item_pool raise before it ever reaches the floor.
_unlock_room = (sum(C.progressive_count(_x) for _x in _wE.enabled_worlds)
                + (C.UPGRADE_ITEM_COUNT if _wE.options.shuffle_upgrades else 0)
                + (GEM_GRANT_COUNT if _wE.options.shopsanity else 0))
_squeezed = W.items.create_item_pool(_wE, _unlock_room + 12)
_names_E = {i.name for i in _squeezed}
assert len(_squeezed) == _unlock_room + 12, len(_squeezed)

for _plant, _world in (("Lily Pad", "Big Wave Beach"),
                       ("Blover", "Far Future"),
                       ("Perfume-shroom", "Jurassic Marsh")):
    assert _plant in _names_E, \
        f"a squeezed pool dropped {_plant}, so {_world} can never be entered"
# Dark Ages asks for a GROUP rather than one plant, so any member will do.
assert set(C.JESTER_COUNTER_PLANTS) & _names_E, \
    "a squeezed pool dropped every Jester answer, so Dark Ages can never be entered"
assert set(C.SUN_PRODUCER_PLANTS) & _names_E, "squeezed pool has no sun producer"
assert set(C.CHEAP_ATTACKER_PLANTS) & _names_E, "squeezed pool has no attacker"

# ...and a world the seed left out contributes nothing to the floor, or an
# Egypt-only seed would be forced to carry plants no rule can ever ask for --
# which is the whole reason the floor is built from enabled_worlds and not from
# WORLD_ENTRY_PLANTS wholesale.
_wEgypt, _ = run("entry-plant floor: Egypt only", world_count=1)
assert _wEgypt.enabled_worlds == {"Ancient Egypt"}, _wEgypt.enabled_worlds
# Squeezed to ONE slot, which is the whole floor. At that size the mandatory
# blocks are empty -- Egypt under the world_key goal ships no unlock, shopsanity
# is off so there is no gem grant, and the upgrades take 20% of one location,
# which is none -- so whatever plant survives IS what the floor forced.
#
# ONE plant, not two, since 2026-08-25. Egypt's egypt6 checkpoint used to want a
# sun producer AND a cheap attacker, but the attacker half was dropped: the
# precollected starter always satisfied it, and naming it made trackers demand
# an attacker the seed need not contain.
_egypt_pool = {i.name for i in W.items.create_item_pool(_wEgypt, 1)}
_egypt_plants = _egypt_pool & {p.name for p in W.items.PLANT_ITEMS}
assert len(_egypt_plants) == 1, f"floor is {sorted(_egypt_plants)}, expected 1 plant"
assert set(C.SUN_PRODUCER_PLANTS) & _egypt_plants, \
    f"the one forced plant is not a sun producer: {sorted(_egypt_plants)}"
# The attacker half is covered by the precollected starter, not by the pool.
assert set(C.CHEAP_ATTACKER_PLANTS) & set(_wEgypt.starting_plants), \
    "the starter is not a cheap attacker, so a run could begin with nothing placeable"
_forced = {"Lily Pad", "Blover", "Perfume-shroom"} & _egypt_pool
assert not _forced, \
    f"an Egypt-only seed was forced to carry entry plants for absent worlds: {sorted(_forced)}"

print(f"the pool floor keeps an entry plant for each of the "
      f"{len(C.WORLD_ENTRY_PLANTS)} gated worlds a seed enables, "
      f"and none for those it does not")

# ── the per-slot cheap-attacker draw ───────────────────────────────────────
# CHEAP_ATTACKER_PLANTS is the DERIVED list of 47 plants that qualify. A slot
# names only 10 of them in its Egypt 6 rule, and only those 10 are progression.
#
# Naming all 46 forced every one to progression -- items.py promotes anything a
# rule names -- for a rule that needs exactly ONE of them to be findable. In a
# small seed the progression block is what squeezes out the useful plants, the
# filler and the traps, and an Egypt-only seed had room for not one coin or gem.
#
# The count is a literal 10, not LOGIC_ATTACKER_COUNT: an expectation read from
# the constant under test passes whatever that constant says.
assert C.LOGIC_ATTACKER_COUNT == 10, C.LOGIC_ATTACKER_COUNT
# 46, not 47: Chard Guard was removed on 2026-08-25 as a false positive of the
# "Action with Damage >= 20" rule -- its 60 is knockback force.
assert len(C.CHEAP_ATTACKER_PLANTS) == 46, len(C.CHEAP_ATTACKER_PLANTS)

_draws = {}
for _label, _kw in (("default", {}), ("Egypt only", dict(world_count=1)),
                    ("13 worlds", dict(world_count=13))):
    _wD, _ = run(f"attackers: {_label}", **_kw)
    _drawn = set(_wD.logic_attackers)
    assert len(_drawn) == 10, f"{_label}: drew {len(_drawn)} attackers, expected 10"
    assert _drawn <= set(C.CHEAP_ATTACKER_PLANTS), \
        f"{_label}: drew something that is not a cheap attacker: {sorted(_drawn - set(C.CHEAP_ATTACKER_PLANTS))}"

    # The starter is one of them, and that is what keeps the gate's meaning
    # unchanged: the starter is precollected, so it already satisfied has_any
    # over all 46 in every seed. Drawing the 10 independently would leave it
    # outside them most of the time and quietly turn a dead requirement into a
    # live one, per seed.
    _starter = [i.name for i in _wD.multiworld.precollected
                if i.name in set(C.CHEAP_ATTACKER_PLANTS)]
    assert len(_starter) == 1, f"{_label}: {len(_starter)} starter attackers precollected"
    assert _starter[0] in _drawn, \
        f"{_label}: starter {_starter[0]} is not in the draw, so the gate changed meaning"
    # ...and it can hold a lane. A blind draw of 10 can be all Cherry Bomb and
    # Potato Mine, which is why the starter is drawn first and forced in.
    assert _starter[0] in C.STARTER_PLANTS, f"{_label}: starter is not lane-holding"

    # The other 37 are ordinary useful plants, not progression -- EXCEPT where
    # one is also a world entry plant, which is a separate rule naming it for a
    # separate reason. Lava Guava is the only such plant: it is a cheap attacker
    # AND one of the five with a WarmingRadius, so Frostbite Caves names it and
    # it stays progression in any seed containing that world whether the draw
    # picked it or not.
    _slot_prog = W.items.slot_progression_plants(_wD)
    _entry_here = {n for _w2 in _wD.enabled_worlds
                   for _g in C.WORLD_ENTRY_PLANTS.get(_w2, []) for n in _g}
    _leaked = (set(C.CHEAP_ATTACKER_PLANTS) - _drawn - _entry_here) & _slot_prog
    assert not _leaked, \
        f"{_label}: {len(_leaked)} undrawn attackers are still progression: {sorted(_leaked)[:5]}"
    _draws[_label] = _drawn

from apstub import ItemClassification as _IC_j

# NO ATTACKER IS REQUIRED AT ALL. Dropped 2026-08-25.
#
# The attacker half of the egypt6 checkpoint was provably vacuous: the starter
# is drawn from STARTER_PLANTS (a subset of the cheap attackers), forced into
# the slot's drawn ten, and PRECOLLECTED -- so has_any(attackers) was true from
# sphere 0 in every seed ever generated.
#
# It was also actively harmful, which is why it went rather than staying as
# harmless decoration. A precollected item is invisible to anything modelling
# only RECEIVED items, so Universal Tracker read the half as unmet and named an
# attacker to go find -- and in 11 of 40 measured Egypt-only world_key seeds the
# pool contains no cheap attacker at all, so it named an item the seed could not
# contain and never entered GO mode.
_wR, _ = run("attackers: no longer required", world_count=1)
_pre = [i.name for i in _wR.multiworld.precollected]
_entrance = _wR.multiworld.get_entrance("Enter Ancient Egypt Early", _wR.player)
_sun = C.SUN_PRODUCER_PLANTS[0]
# Everything precollected EXCEPT the starter attacker, so the probe cannot pass
# for the old reason.
_bare = [n for n in _pre if n not in set(C.CHEAP_ATTACKER_PLANTS)]

from apstub import CollectionState as _CS


def _opens(extra):
    _st = _CS(_wR.multiworld, W.items.ITEM_NAME_GROUPS)
    for _n in _bare + extra:
        _st.collect(_n)
    _st.sweep()
    return _entrance.access_rule(_st)


assert _opens([_sun]), \
    "egypt6-8 does not open on a sun producer alone, with no attacker held"
# ...and the sun producer is still genuinely required, or the gate is gone
# entirely rather than halved.
assert not _opens([]), "egypt6-8 opens with nothing held; the sun rule is gone"
# No attacker opens it on its own, drawn or otherwise -- the gate is one
# requirement now, not two.
_still = sorted(n for n in C.CHEAP_ATTACKER_PLANTS if _opens([n]))
assert not _still, \
    f"{len(_still)} attacker(s) still open egypt6-8 without a sun producer: {_still[:5]}"

# THE CLASSIFICATION FOLLOWS. Nothing names the attackers, so none of them may
# be progression -- except where another rule names one for its own reason.
# Lava Guava is the live example: it is a cheap attacker AND a Frostbite Caves
# warming plant, so it stays progression in any seed with that world.
for _label2, _kw2 in (("Egypt only", dict(world_count=1)),
                      ("13 worlds", ALL_WORLDS)):
    _wC, _ = run(f"attackers not progression: {_label2}", **_kw2)
    _entry_here2 = {n for _w3 in _wC.enabled_worlds
                    for _g3 in C.WORLD_ENTRY_PLANTS.get(_w3, []) for n in _g3}
    _stretch_here = {n for _w3 in _wC.enabled_worlds
                     for _sfx in C.stretch_suffixes(_w3)
                     for _g3 in C.slot_stretch_groups(_wC, _w3, _sfx) for n in _g3}
    _exempt = (_entry_here2 | _stretch_here | set(C.SUN_PRODUCER_PLANTS)
               | set(_wC.logic_jesters))
    _prog_atk = [n for n in C.CHEAP_ATTACKER_PLANTS if n not in _exempt
                 and _wC.create_item(n).classification == _IC_j.progression]
    assert not _prog_atk, (
        f"{_label2}: {len(_prog_atk)} cheap attacker(s) are still progression "
        f"though no rule names them: {_prog_atk[:5]}")

# The draw itself is KEPT, unread, on purpose: removing it would consume a
# different number of values from the slot RNG and shift every later draw,
# changing the starter and the Jester counter for a given seed.
assert len(_wR.logic_attackers) == 10, sorted(_wR.logic_attackers)
print(f"cheap attackers: 10 of {len(C.CHEAP_ATTACKER_PLANTS)} drawn per slot, "
      f"starter always among them, and only those 10 satisfy the egypt6 gate")

# ── starting_plants ────────────────────────────────────────────────────────
# 1 (the default) is the old guarantee and nothing more: one cheap attacker
# that stays on the lawn. Above that the extras are random, EXCEPT that a sun
# producer is never given away -- a plant handed over at generation time
# satisfies every rule that asks for it before the rule is checked, and Egypt's
# egypt6 checkpoint wants a sun producer plus a cheap attacker whose attacker
# half is already free from the starter. Measured before the option was written:
# a free sun producer takes sphere 1 from 9 to 12, or 17 with shopsanity.
#
# Range pinned as literals, not from the option: an expectation read out of the
# class under test passes whatever the class says.
assert StartingPlants.range_start == 1, StartingPlants.range_start
assert StartingPlants.range_end == 10, StartingPlants.range_end
assert StartingPlants.default == 1, StartingPlants.default

_SUN = set(C.SUN_PRODUCER_PLANTS)
for _n in (1, 2, 5, 10):
    for _label, _kw in (("13 worlds", {}), ("Egypt only", dict(world_count=1))):
        _wS, _ = run(f"start {_n}: {_label}", starting_plants=_n, **_kw)
        _pre = [i.name for i in _wS.multiworld.precollected]
        assert len(_pre) == _n, f"start {_n} {_label}: precollected {len(_pre)}, expected {_n}"
        assert len(set(_pre)) == _n, f"start {_n} {_label}: duplicates in {_pre}"
        assert _pre == sorted(_wS.starting_plants), \
            f"start {_n} {_label}: starting_plants disagrees with precollected"

        # The guarantee: exactly one is a lane-holding cheap attacker, whatever
        # the count. It is what the whole mechanism exists for -- the client
        # blocks every AP-managed plant until it arrives, so a run with nothing
        # placeable is a run that cannot begin.
        _atk = [p for p in _pre if p in set(C.STARTER_PLANTS)]
        assert _atk, f"start {_n} {_label}: no lane-holding attacker granted"

        # NEVER a plant any rule names, at any setting: not a sun producer and
        # not a world entry plant. Either one would satisfy its gate before the
        # gate is ever checked.
        # LOGIC_PLANTS holds all 36 Jester counters, but a slot NAMES only the
        # one it drew, so only that one may not be granted. Excluding all 36
        # would take a quarter of the roster out of the draw for a rule that
        # asks for one plant.
        _named = ((set(C.LOGIC_PLANTS) - set(C.JESTER_COUNTER_PLANTS))
                  | set(_wS.logic_jesters))
        _logic_given = _named & set(_pre)
        assert not _logic_given, \
            f"start {_n} {_label}: a rule-named plant was granted outright: {sorted(_logic_given)}"

        # Granted plants are not shipped again. Before this the starter was
        # precollected AND left in the pool, wasting a check in every seed.
        _pool = [i.name for i in _wS.multiworld.itempool]
        _dupes = sorted(p for p in _pre if p in _pool)
        assert not _dupes, f"start {_n} {_label}: granted plants also in the pool: {_dupes}"
        _fillableS = len(_wS.active_locations()) - len(_wS.goal_locations())
        assert len(_pool) == _fillableS, \
            f"start {_n} {_label}: pool {len(_pool)} does not fill {_fillableS}"

# ...and sphere 1 is untouched at every setting, which is the whole reason sun
# producers are held back. Checked through the region graph, not by counting.
from apstub import CollectionState as _CS2
for _n in (1, 10):
    _wS, _ = run(f"start {_n}: sphere", starting_plants=_n, shopsanity=1)
    _st = _CS2(_wS.multiworld, W.items.ITEM_NAME_GROUPS)
    for _i in _wS.multiworld.precollected: _st.collect(_i.name)
    _st.sweep()
    _s1 = len(_st.reachable_locations())
    assert _s1 == 9, f"starting_plants={_n} makes sphere 1 {_s1}, expected 9"

# ...and the count really is the option, not a constant: 10 must differ from 1.
_w1, _ = run("start 1: draw", starting_plants=1)
_w10, _ = run("start 10: draw", starting_plants=10)
assert len(_w1.starting_plants) == 1 and len(_w10.starting_plants) == 10
# THE EXCLUSION NEEDS A SWEEP, NOT A SEED. The extras are drawn at random, so a
# single seed proves nothing: with 9 extras from ~130 plants a sun producer
# turns up roughly one run in three and an entry plant in seven of ten, which
# means a fixed seed passes most of the time with the exclusion DELETED. That is
# exactly how the first version of this test went green against a broken draw.
#
# 40 seeds at the maximum count puts the odds of missing a leak below 1e-6.
_span, _leaked = set(), []
for _seed in range(40):
    _mwX = MultiWorld(); _mwX.random.seed(_seed)
    _wX = W.PvZ2GardendlessWorld(_mwX, 1)
    _wX.options = Opts(starting_plants=10)
    _wX.random.seed(_seed)
    _wX.generate_early()
    _got = set(_wX.starting_plants)
    assert len(_got) == 10, f"seed {_seed}: {len(_got)} starting plants"
    _named = ((set(C.LOGIC_PLANTS) - set(C.JESTER_COUNTER_PLANTS))
              | set(_wX.logic_jesters))
    _leaked += sorted(_named & _got)
    _span |= _got
assert not _leaked, \
    f"a rule-named plant was granted in {len(_leaked)} of 40 seeds: {_leaked[:5]}"

# The drawn Jester counter is excluded, but the OTHER 35 are drawable -- that is
# the point of drawing one rather than naming all of them. If none of them ever
# turns up across 40 maximum-size draws, the exclusion is too wide.
_others = set(C.JESTER_COUNTER_PLANTS) & _span
assert _others, ("no undrawn Jester counter was ever granted across 40 seeds; "
                 "the exclusion is taking the whole group, not the drawn one")

# ...and the sweep has to be capable of seeing a leak, or it proves nothing.
# The draw should range over everything that is NOT rule-named -- 116 of the 135
# plants -- so a narrow span means the sweep would miss one.
assert len(_span) > 60, \
    f"the extras only ever draw {len(_span)} distinct plants; too narrow to catch a leak"
# The FIXED entry plants -- the Jester group is excluded per slot, not as a
# group, and is checked above instead.
_ENTRY = ({_n2 for _g in C.WORLD_ENTRY_PLANTS.values() for _grp in _g for _n2 in _grp}
          - set(C.JESTER_COUNTER_PLANTS))
assert not (_SUN & _span), f"sun producers reachable by the draw: {sorted(_SUN & _span)}"
assert not (_ENTRY & _span), f"entry plants reachable by the draw: {sorted(_ENTRY & _span)}"

# The two exclusions are separately load-bearing, so neither may be empty --
# an exclusion over an empty set passes trivially.
assert _SUN and _ENTRY, "a plant exclusion set is empty, so the assertions above are vacuous"

print(f"starting_plants: 1..10, always one lane-holding attacker, granted plants "
      f"dropped from the pool, sphere 1 stays 9, and no sun producer or world "
      f"entry plant in {len(_span)} plants drawn across 40 seeds")

# CLASSIFICATION IS TESTED THROUGH create_item, NOT THROUGH CollectionState.
# apstub's collect() takes a bare NAME and ignores classification entirely, so
# every state-driven test in this suite and in sphere_test would pass with every
# plant marked useful -- which is precisely the bug LOGIC_PLANTS exists to
# prevent (AP tracks only advancement items in prog_items, so has_any is
# permanently False for a useful item and the rule naming it silently dies).
# The only honest check is the classification of the Item that create_item
# actually builds.
for _label, _kw in (("default", {}), ("Egypt only", dict(world_count=1))):
    _wC, _ = run(f"classification: {_label}", **_kw)
    _want = W.items.slot_progression_plants(_wC)
    _wrong = []
    for _p in W.items.PLANT_ITEMS:
        _cls = _wC.create_item(_p.name).classification
        _expected = _IC.progression if _p.name in _want else _IC.useful
        if _cls != _expected:
            _wrong.append((_p.name, _cls, _expected))
    assert not _wrong, f"{_label}: create_item classified {len(_wrong)} plants wrongly: {_wrong[:4]}"
    # ...and the two classes are both non-empty, or "all correct" is vacuous.
    assert _want, f"{_label}: no plant is progression"
    assert len(_want) < len(W.items.PLANT_ITEMS), f"{_label}: every plant is progression"

# A NON-plant keeps its static classification -- create_item must not sweep the
# unlocks, upgrades, filler or traps into the per-slot plant logic.
_wC, _ = run("classification: non-plants", world_count=1)
for _name in ("Progressive Ancient Egypt", "Sky Shield", "100 Coins",
              C.SHOP_REGION and "Lawn Mower Trap", GEM_GRANT):
    assert _wC.create_item(_name).classification == \
        W.items.ITEM_NAME_TO_ITEM[_name].classification, \
        f"create_item changed the classification of {_name}"

# ENTRY PLANTS ARE SCOPED TO THE WORLDS THE SEED BUILT. rules.py skips a world
# that is not enabled, so Lily Pad gates nothing in an Egypt-only run and must
# not eat a progression slot there. Stated as an exact set, which is what makes
# it worth asserting: anything beyond it is a slot taken from the useful plants,
# the filler and the traps in a seed that has few to spare.
#
# The default goal trims Egypt at egypt8, so " Mid" is not built and Grave
# Buster is not named either -- the exact set is the FIVE sun producers and
# nothing else. That is down from 15 before 2026-08-25, when the attacker half
# of the egypt6 checkpoint went: it was satisfied by the precollected starter in
# every seed, so naming ten attackers bought nothing and cost ten slots.
_wE2, _ = run("classification: Egypt-only progression set", world_count=1)
assert _wE2.enabled_worlds == {"Ancient Egypt"}, _wE2.enabled_worlds
_egypt_prog = W.items.slot_progression_plants(_wE2)
_want_egypt = set(C.SUN_PRODUCER_PLANTS)
assert _egypt_prog == _want_egypt, (
    f"an Egypt-only seed's progression plants are {sorted(_egypt_prog - _want_egypt)} "
    f"beyond its sun producers, and missing {sorted(_want_egypt - _egypt_prog)}")
# Five, as a literal: reading the length off SUN_PRODUCER_PLANTS would agree
# with whatever that list said.
assert len(_egypt_prog) == 5, sorted(_egypt_prog)
assert not ({"Lily Pad", "Blover", "Perfume-shroom", "Torchwood"} & _egypt_prog), \
    "an Egypt-only seed still carries entry plants for worlds it does not have"
print(f"per-slot classification: {len(_egypt_prog)} progression plants in an "
      f"Egypt-only seed, {len(W.items.PLANT_ITEMS) - len(_egypt_prog)} useful")

# ── the guaranteed gem grant ───────────────────────────────────────────────
class _GemProbe:
    """Stands in for the gem item when probing an item rule. Synthetic on
    purpose: probing with an item drawn from the pool passes vacuously in a seed
    that does not contain it, which is how an earlier item-rule test passed with
    the rule deleted."""
    name = GEM_GRANT
    player = 1
    advancement = True

# Gems are the shop's only currency and a player can earn ZERO of them under
# Archipelago: the game's whole resource set holds one GIVE_GEM, worth 20, in
# the PREMIUM_BRING_OUT flow the client deliberately silences. So the pool is
# the only source, and before these items a small seed had none at all --
# filler is what is left after the plants, and the plants outnumber the
# locations until a seed is several worlds wide.
#
# It is progression rather than filler for exactly that reason: filler is
# trimmed first, in the seeds that need it most.
import re as _re

# SHIPPED ONLY WITH SHOPSANITY. Shop cards are the only AP locations that cost
# anything -- no access rule reads currency, and nothing else in a seed can be
# bought -- so with the option off there is no wall to break and the mandatory
# slot is better spent on a plant. Both sides are checked: a seed that needs it
# has exactly one, a seed that does not has none.
_gem_seeds = [("1 world", dict(world_count=1), 0),
              ("1 world + shopsanity", dict(world_count=1, shopsanity=1), 1),
              ("2 worlds + shopsanity", dict(world_count=2, shopsanity=1), 1),
              ("13 worlds + shopsanity", dict(world_count=13, shopsanity=1), 1),
              ("13 worlds, no shopsanity", dict(world_count=13), 0),
              ("13 worlds, 100% traps", dict(world_count=13, trap_percentage=100), 0),
              ("side paths, no shopsanity",
               dict(world_count=1, include_side_paths=1), 0)]
for _label, _kw, _want_n in _gem_seeds:
    _wG, _ = run(f"gems: {_label}", **_kw)
    _n = [i.name for i in _wG.multiworld.itempool].count(GEM_GRANT)
    assert _n == _want_n, f"{_label}: {_n} copies of {GEM_GRANT}, expected {_want_n}"
    # A seed with no shop checks must have no grant, and vice versa: the two are
    # the same condition and drifting apart is the bug this guards.
    _shop_n = len([l for l in _wG.active_locations() if l.name.startswith("Shop: ")])
    assert bool(_n) == bool(_shop_n), \
        f"{_label}: {_n} grants against {_shop_n} shop checks"
    if not _want_n:
        continue
    # Literal counts above, not GEM_GRANT_COUNT: an expectation read out of the
    # constant under test passes whatever that constant says, which is how a
    # first version of this let the count change silently. One item of 150
    # rather than two of 75 is deliberate (Kurt, 2026-08-23) -- two halves can
    # both land late, and half a gem budget is no better than none if the other
    # half is behind the wall it was meant to open.
    assert GEM_GRANT_COUNT == 1, f"GEM_GRANT_COUNT is {GEM_GRANT_COUNT}, expected 1"

# ...and they are progression, which is the whole mechanism. As filler they
# would be the first thing the trim drops, in precisely the small seeds that
# have no other gems. Mutation-proved: flip this to filler and the 1-world
# cases above fail.
assert all(i.classification == _IC.progression for i in GEM_GRANT_ITEMS), \
    f"{GEM_GRANT} is not progression, so a small seed will trim it away"

# ...and nothing in logic may name them. They are progression to survive the
# trim, not because they gate anything -- affordability is deliberately not
# modelled, since currency accrues from play as well as from items.
assert GEM_GRANT not in C.LOGIC_PLANTS, f"{GEM_GRANT} is being treated as a plant"

# THE NAME IS THE INTERFACE. The client reads the amount straight off it with
# a regex; a rename that regex does not match turns the item into a toast that
# grants nothing, and no test of the pool would notice. So the regex is read
# out of the client itself (_JS, already extracted above for LOC_LEVELS)
# rather than restated here, and the item name is run through the Python
# equivalent.
assert r"const currencyMatch = /^(\d+) (Coins|Gems)$/" in _JS, \
    "the client's currency regex has moved or changed shape; re-pin this test"
_parsed = _re.match(r"^(\d+) (Coins|Gems)$", GEM_GRANT)
assert _parsed and _parsed.group(2) == "Gems", \
    f"the client's currency regex does not match {GEM_GRANT!r}, so it grants nothing"
assert int(_parsed.group(1)) == 150, f"{GEM_GRANT} is not worth 150"
# ...and the negative-trap regex must NOT claim it, or a grant would be read as
# a debit. The two patterns differ by one leading minus.
assert not _re.match(r"^-(\d+) (Coins|Gems)$", GEM_GRANT), \
    f"{GEM_GRANT} parses as a currency TRAP"

# IT LANDS BEFORE EGYPT 9. The store opens at egypt6 and its five ungated
# upgrade cards cost 30 gems apiece, so a grant found in Egypt's endgame arrives
# after every point it was needed. Enforced as an item rule, so the test is
# whether every OTHER location refuses it -- checking the one place fill happened
# to pick would pass on luck.
#
# The expectation is LITERAL, not gem_grant_regions(). Deriving it from the
# function under test is worthless: a first version of this did exactly that and
# passed with the region set widened to include Egypt Mid and the Shop. It is
# stated as LEVELS rather than regions, since "before egypt9" is the contract
# and the region names are just how it is currently implemented.
#
# egypt9 is Egypt's " Mid" cut, which is its World Key level -- pinned as a
# literal in the world_gates block above, sourced from the game's own map data.
_WANT_GEM_LOCS = ({f"tutorial{_i}" for _i in range(1, 5)}
                  | {f"egypt{_i}" for _i in range(1, 9)})

# Every case here runs shopsanity, since that is the only way the grant is in
# the pool at all. The no-shopsanity case is checked separately below.
for _label, _kw in (("default", dict(shopsanity=1)),
                    ("Egypt only", dict(world_count=1, shopsanity=1)),
                    ("3 worlds", dict(world_count=3, shopsanity=1)),
                    ("everything on", dict(world_count=13, shopsanity=1,
                                           include_side_paths=1,
                                           include_danger_rooms=1,
                                           early_world_keys=1))):
    _wP, _ = run(f"gem placement: {_label}", **_kw)
    _open = set()
    _shut = 0
    for _r in _wP.multiworld.get_regions(_wP.player):
        for _loc in _r.locations:
            if _loc.name == "Victory":
                continue  # an event carrying a locked item; fill never fills it
            if _loc.item_rule(_GemProbe()):
                _open.add(_loc.name)
            else:
                _shut += 1
    assert _open == _WANT_GEM_LOCS, (
        f"{_label}: {GEM_GRANT} may land on "
        f"{sorted(_open - _WANT_GEM_LOCS)[:5]} and may NOT land on "
        f"{sorted(_WANT_GEM_LOCS - _open)[:5]}")
    assert _shut, f"{_label}: nothing rejects {GEM_GRANT}, so the rule is not applied"

# The store hangs off Ancient Egypt Early and so would qualify by REGION. It is
# excluded by name above, and called out here because it is the one exclusion
# that is a judgement rather than a consequence: a grant sitting on a card the
# player cannot afford is the exact deadlock the item exists to break.
assert not any(_n.startswith("Shop: ") for _n in _WANT_GEM_LOCS)

# With shopsanity off the rule is not applied at all -- there is no grant to
# place. Everything must accept it, which is the harmless state: the item does
# not exist, so nothing can be placed anywhere.
_wNo, _ = run("gem placement: no shopsanity", world_count=1)
_refused = [l.name for _r in _wNo.multiworld.get_regions(_wNo.player)
            for l in _r.locations if not l.item_rule(_GemProbe())]
assert not _refused, \
    f"the gem placement rule is still applied with shopsanity off: {_refused[:4]}"
assert GEM_GRANT not in {i.name for i in _wNo.multiworld.itempool}, \
    "shopsanity is off but the grant is in the pool"

print(f"{GEM_GRANT} is confined to the {len(_WANT_GEM_LOCS)} checks before "
      f"egypt9, shop cards excluded")

# What the guarantee is actually worth against the shop, reported rather than
# asserted: the gem PRICES live in the game's store data, not in this repo, and
# an upstream reshuffle should not fail the suite. Read the number.
_wS, _ = run("gems: cost vs grant", world_count=1, shopsanity=1)
_shop_n = len([l for l in _wS.active_locations() if l.name.startswith("Shop: ")])
_granted = GEM_GRANT_COUNT * int(_parsed.group(1))
print(f"guaranteed gems: {GEM_GRANT_COUNT} x {_parsed.group(1)} = {_granted} in "
      f"every SHOPSANITY seed, against {_shop_n} shop cards in the smallest one; "
      f"none at all with shopsanity off")


# ── Option groups reach the options page ──────────────────────────────────────
#
# OPTION_GROUPS sat in options.py for a while with nothing reading it, so every
# option still rendered in one undifferentiated list. WebHost reads the groups
# off `world.web.option_groups`, so defining the list is only half the wiring.

import dataclasses as _dc_og
from pvz2gardendless.options import OPTION_GROUPS as _OG

assert getattr(W.PvZ2Web, "option_groups", None), \
    "PvZ2Web does not expose option_groups, so WebHost renders one flat list"
assert W.PvZ2Web.option_groups is _OG, \
    "PvZ2Web.option_groups is not the OPTION_GROUPS defined in options.py"

_og_names = [g.name for g in _OG]
assert len(set(_og_names)) == len(_og_names), \
    f"two option groups share a name: {_og_names}"

_og_flat = [o for g in _OG for o in g.options]
_og_declared = [f.type for f in _dc_og.fields(W.PvZ2Options)]

# Literals, not len(OPTION_GROUPS) / len(fields) -- an expectation read from the
# thing under test passes whatever that thing says. 21 is every option in
# PvZ2Options as of 2026-08-25 (20 before include_levels_past_goal); 7 is the
# groups options.py declares.
assert len(_OG) == 7, f"expected 7 option groups, got {len(_OG)}"
assert len(_og_declared) == 21, \
    f"PvZ2Options declares {len(_og_declared)} options, not 21 -- if that is " \
    "intended, update this literal AND put the new option in a group"

_og_missing = [o.__name__ for o in _og_declared if o not in _og_flat]
assert not _og_missing, \
    f"options in PvZ2Options but in no group, so they land in AP's fallback " \
    f"group instead of where they belong: {_og_missing}"

_og_stray = [o.__name__ for o in _og_flat if o not in _og_declared]
assert not _og_stray, \
    f"options grouped but not in PvZ2Options, so they render nowhere: {_og_stray}"

_og_dupes = sorted({o.__name__ for o in _og_flat if _og_flat.count(o) > 1})
assert not _og_dupes, f"options named by more than one group: {_og_dupes}"

print(f"option groups: {len(_OG)} groups covering all {len(_og_declared)} "
      f"options, reached via PvZ2Web.option_groups ({', '.join(_og_names)})")


# ── trap weights ──────────────────────────────────────────────────────────────
#
# trap_percentage decides HOW MANY traps; the four weights decide which. The
# split is apportioned, not sampled, so a slot's trap mix is identical every
# generation -- the property the old uniform rotation had and that a random
# draw would have quietly given up.

from pvz2gardendless.items import (weighted_trap_names, trap_weights,
                                   TRAP_CYCLE, TRAP_WEIGHT_OPTIONS,
                                   LAWN_MOWER_TRAP, COSTUME_SHUFFLE_TRAP,
                                   COIN_TRAP, GEM_TRAP)

# The four traps, named as literals rather than read off TRAP_CYCLE: this is
# the set the option list has to keep up with, and reading it from the table
# under test would agree with whatever that table said.
assert set(TRAP_CYCLE) == {LAWN_MOWER_TRAP, COSTUME_SHUFFLE_TRAP,
                           COIN_TRAP, GEM_TRAP}, TRAP_CYCLE
assert set(TRAP_WEIGHT_OPTIONS) == set(TRAP_CYCLE)
for _t, _opt in TRAP_WEIGHT_OPTIONS.items():
    assert hasattr(Opts(), _opt), f"{_t} names {_opt}, which is not an option"

# THE BACK-COMPAT CLAIM. Equal weights must reproduce the old
# TRAP_CYCLE[i % len(TRAP_CYCLE)] rotation item for item, or every seed rolled
# before the weights existed would regenerate with a different pool.
for _n in range(0, 40):
    _old = [TRAP_CYCLE[_i % len(TRAP_CYCLE)] for _i in range(_n)]
    assert weighted_trap_names(_n, [25] * 4) == _old, _n
    # Relative, not absolute: any equal weighting is the same even mix.
    assert weighted_trap_names(_n, [7] * 4) == _old, _n
print(f"trap weights: equal weights reproduce the old rotation exactly for "
      f"every count 0..39")

# A weight of 0 keeps that trap out entirely, and the others still fill the
# whole allocation -- the slots are not silently lost.
_only_mower = weighted_trap_names(20, [1, 0, 0, 0])
assert _only_mower == [LAWN_MOWER_TRAP] * 20, _only_mower
_no_gems = weighted_trap_names(21, [1, 1, 1, 0])
assert len(_no_gems) == 21 and GEM_TRAP not in _no_gems
assert set(_no_gems) == {LAWN_MOWER_TRAP, COSTUME_SHUFFLE_TRAP, COIN_TRAP}

# Ratios are honoured, not merely "the heavy one appears more often". 3:1 over
# 40 traps is exactly 30 and 10 -- an apportionment claim a sampler could not
# make.
_three_one = weighted_trap_names(40, [3, 1, 0, 0])
assert _three_one.count(LAWN_MOWER_TRAP) == 30, _three_one.count(LAWN_MOWER_TRAP)
assert _three_one.count(COSTUME_SHUFFLE_TRAP) == 10

# Every count is filled exactly, at a lopsided weighting where the floors do
# not add up on their own and the largest-remainder pass has to make it up.
for _n in range(0, 60):
    _w = weighted_trap_names(_n, [5, 3, 1, 1])
    assert len(_w) == _n, (_n, len(_w))

# All zero means no traps, whatever trap_percentage says. This is the one case
# that returns fewer than asked for, and the pool builder turns the rest back
# into filler rather than leaving the pool short.
assert weighted_trap_names(50, [0, 0, 0, 0]) == []
assert weighted_trap_names(0, [25] * 4) == []

# Now through the pool builder, where the count comes from trap_percentage.
# Every world, since a small seed ships no filler at all and so no traps.
_tw, _ = run("traps: default weights", trap_percentage=50, **ALL_WORLDS)
_tp = [i.name for i in _tw.multiworld.itempool if i.name in set(TRAP_CYCLE)]
assert len(set(_tp)) == 4, f"default weights did not ship all four traps: {set(_tp)}"

# Zeroing one trap removes it from the seed without changing the trap TOTAL --
# the others absorb its share. That is the whole point of a weight as against
# just turning the trap off.
_zw, _ = run("traps: no gems", trap_percentage=50, trap_weight_gems=0, **ALL_WORLDS)
_zp = [i.name for i in _zw.multiworld.itempool if i.name in set(TRAP_CYCLE)]
assert GEM_TRAP not in _zp, "a -20 Gems trap survived a weight of 0"
assert len(_zp) == len(_tp), \
    f"zeroing a weight changed the trap count: {len(_zp)} against {len(_tp)}"

# All four zeroed: no traps, and the pool is still exactly the right size --
# the freed slots become filler.
_nw, _ = run("traps: all weights zero", trap_percentage=50, **ALL_WORLDS,
             trap_weight_lawn_mower=0, trap_weight_costume_shuffle=0,
             trap_weight_coins=0, trap_weight_gems=0)
assert not [i for i in _nw.multiworld.itempool if i.name in set(TRAP_CYCLE)], \
    "traps were generated with every weight at 0"
assert len(_nw.multiworld.itempool) == (len(_nw.active_locations())
                                       - len(_nw.goal_locations())), \
    "zeroing every weight left the pool short of its locations"

# ...and that matches trap_percentage=0, which is the other way to say it.
_0w, _ = run("traps: percentage zero", trap_percentage=0, **ALL_WORLDS)
assert not [i for i in _0w.multiworld.itempool if i.name in set(TRAP_CYCLE)]

# Same seed, same mix, twice: apportionment must not have picked up an RNG
# dependency.
_dA, _ = run("traps: determinism A", trap_percentage=50,
             trap_weight_coins=90, **ALL_WORLDS)
_dB, _ = run("traps: determinism B", trap_percentage=50,
             trap_weight_coins=90, **ALL_WORLDS)
_cnt = lambda w: collections.Counter(
    i.name for i in w.multiworld.itempool if i.name in set(TRAP_CYCLE))
assert _cnt(_dA) == _cnt(_dB), (_cnt(_dA), _cnt(_dB))
print(f"trap mix at 50%: {dict(_cnt(_tw))}, "
      f"gems zeroed: {dict(_cnt(_zw))}, coins at 90: {dict(_cnt(_dA))}")


# ── the Jester counter is drawn per slot ──────────────────────────────────────
#
# 36 plants can damage the Dark Ages Jester; the entrance names ONE of them,
# drawn per slot, so each seed asks for a different plant. The other 35 are
# ordinary useful plants. Naming all 36 would promote all 36 to progression,
# which is the exact cost LOGIC_ATTACKER_COUNT was introduced to avoid.

from apstub import ItemClassification as _IC_j

# Literals: 36 is the derived list, 1 is the design decision. Reading either off
# the constant under test would agree with whatever the constant said.
assert C.JESTER_DRAW_COUNT == 1, C.JESTER_DRAW_COUNT
assert len(C.JESTER_COUNTER_PLANTS) == 36, len(C.JESTER_COUNTER_PLANTS)
assert len(set(C.JESTER_COUNTER_PLANTS)) == 36, "duplicate Jester counters"

# Neither of the two plants removed for dealing no damage may come back, and
# neither may Magnifying Grass, whose only projectile the Jester catches.
for _bad in ("Sap-fling", "Chard Guard", "Magnifying Grass"):
    assert _bad not in C.JESTER_COUNTER_PLANTS, f"{_bad} is not a Jester counter"
# Nothing in the list may be a known non-damaging plant.
assert not (set(C.JESTER_COUNTER_PLANTS) & set(C.NON_DAMAGING_PLANTS)), \
    sorted(set(C.JESTER_COUNTER_PLANTS) & set(C.NON_DAMAGING_PLANTS))
# Every one must have an item, or the rule naming it could never pass.
_no_item = sorted(set(C.JESTER_COUNTER_PLANTS) - {p.name for p in PLANT_ITEMS})
assert not _no_item, f"Jester counters with no item: {_no_item}"

# THE CLASSIFICATION, which is the whole request. Asserted through create_item,
# because apstub's collect() takes a bare name and ignores classification -- no
# state-driven test could ever see this being wrong.
_jw, _ = run("jester: drawn is progression", **ALL_WORLDS)
# Entry plants of every other world, which stay progression regardless.
_OTHER_ENTRY = {_n for _w2, _gs in C.WORLD_ENTRY_PLANTS.items()
                for _g2 in _gs if _g2 is not C.JESTER_COUNTER_PLANTS
                for _n in _g2}
_drawn = sorted(_jw.logic_jesters)
assert len(_drawn) == 1, _drawn
assert _jw.create_item(_drawn[0]).classification == _IC_j.progression, \
    f"the drawn counter {_drawn[0]} is not progression"
for _other in sorted(set(C.JESTER_COUNTER_PLANTS) - set(_drawn)):
    # Except the ones another rule names anyway, which are progression for
    # their OWN reason: this slot's drawn cheap attackers, the sun producers,
    # and the other worlds' entry plants. Lava Guava is the live example -- it
    # is both a Jester counter and a Frostbite Caves warming plant.
    if _other in _jw.logic_attackers or _other in C.SUN_PRODUCER_PLANTS             or _other in _OTHER_ENTRY:
        continue
    assert _jw.create_item(_other).classification == _IC_j.useful, \
        f"undrawn counter {_other} is progression; the draw is not narrowing"

# It really is random per slot, not a fixed pick: across 40 seeds the draw must
# range widely. One seed proves nothing about a random draw.
_jspan = set()
for _seed in range(40):
    _mwJ = MultiWorld(); _mwJ.random.seed(_seed)
    _wJ = W.PvZ2GardendlessWorld(_mwJ, 1)
    _wJ.options = Opts()
    _wJ.random.seed(_seed)
    _wJ.generate_early()
    assert len(_wJ.logic_jesters) == 1
    _jspan |= set(_wJ.logic_jesters)
    assert set(_wJ.logic_jesters) <= set(C.JESTER_COUNTER_PLANTS), sorted(_wJ.logic_jesters)
assert len(_jspan) > 12, \
    f"40 seeds only ever drew {len(_jspan)} distinct counters; the draw is not random"
print(f"Jester counters: {len(C.JESTER_COUNTER_PLANTS)} can damage him, "
      f"{C.JESTER_DRAW_COUNT} named per slot, {len(_jspan)} distinct across 40 seeds")

# An Egypt-only seed builds no Dark Ages, so no counter may be progression there
# -- the same scoping the entry plants already have.
_je, _ = run("jester: Egypt only", world_count=1)
_je_prog = [n for n in C.JESTER_COUNTER_PLANTS
            if n not in _je.logic_attackers and n not in C.SUN_PRODUCER_PLANTS
            and n not in _OTHER_ENTRY
            and _je.create_item(n).classification == _IC_j.progression]
assert not _je_prog, \
    f"Egypt-only seed marks Jester counters progression for a world it never built: {_je_prog}"


# ── the goal trim ─────────────────────────────────────────────────────────────
#
# With include_levels_past_goal off (the default) a world ends where the Goal
# Type measures it: at its World Key level, or at its Zomboss. The cut lands on
# a stretch boundary because world_stretches cuts on those same two milestones,
# so it takes whole stretches and the unlock count falls out with it.

# The goal values are copied into constants.py as literals -- it cannot import
# options.py without a cycle. This is the only thing keeping the copy honest.
assert C.GOAL_WORLD_KEY == GoalType.option_world_key
assert C.GOAL_ZOMBOSS == GoalType.option_zomboss
assert C.GOAL_COMPLETION == GoalType.option_completion

# What each goal keeps, pinned as literals rather than read from the table.
# Ancient Egypt has a fourth stretch (its egypt6 checkpoint splits the opening),
# and BOTH halves are the opening as far as the milestones go -- so world_key
# keeps two of its suffixes and one of everyone else's.
assert C.stretches_kept("Dark Ages", C.GOAL_WORLD_KEY) == [""]
assert C.stretches_kept("Dark Ages", C.GOAL_ZOMBOSS) == ["", " Mid"]
assert C.stretches_kept("Dark Ages", C.GOAL_COMPLETION) == ["", " Mid", " Late"]
assert C.stretches_kept("Ancient Egypt", C.GOAL_WORLD_KEY) == ["", " Early"]
assert C.stretches_kept("Ancient Egypt", C.GOAL_ZOMBOSS) == ["", " Early", " Mid"]
# The option puts the whole game back, whatever the goal.
assert C.stretches_kept("Dark Ages", C.GOAL_WORLD_KEY, True) == ["", " Mid", " Late"]

# THE CUT IS THE GOAL LOCATION ITSELF. Nothing past it survives, and the goal
# location does -- a goal you cannot check would put the win out of reach.
from pvz2gardendless.locations import (WORLD_KEY_LOCS as _WK,
                                       WORLD_ZOMBOSS_LOCS as _WZ, _play_order)
for _goal, _table, _lbl in ((C.GOAL_WORLD_KEY, _WK, "world_key"),
                            (C.GOAL_ZOMBOSS, _WZ, "zomboss")):
    _gw, _gsd = run(f"goal trim: {_lbl}", goal_type=_goal, **_EVERY_WORLD)
    _built = {l.name for l in _gw.active_locations()}
    for _goal_loc in _table:
        _wn = C._REGION_TO_WORLD.get(_lnames[_goal_loc]) if hasattr(C, "_REGION_TO_WORLD") else None
        if _goal_loc not in _built:
            continue  # that world is not in this seed
        _o = _play_order(_goal_loc)
        _region = _lnames[_goal_loc]
        _past = [n for n in _built
                 if _lnames.get(n) == _region and (_play_order(n) or -1) > _o]
        assert not _past, (
            f"{_lbl}: {len(_past)} level(s) past the goal {_goal_loc} survived, "
            f"e.g. {sorted(_past)[:4]}")
    # ...and it really did remove something, or the assertion above is vacuous.
    _all_w, _ = run(f"goal trim: {_lbl} untrimmed", goal_type=_goal,
                    include_levels_past_goal=1, **_EVERY_WORLD)
    _n_all = len(_all_w.active_locations())
    assert len(_built) < _n_all, (
        f"{_lbl}: the trim removed nothing ({len(_built)} of {_n_all})")
    print(f"goal trim {_lbl}: {len(_built)} locations against {_n_all} untrimmed")

# completion trims nothing: its goal IS the last level.
_cw, _ = run("goal trim: completion", goal_type=C.GOAL_COMPLETION, **_EVERY_WORLD)
_cw_all, _ = run("goal trim: completion untrimmed", goal_type=C.GOAL_COMPLETION,
                 include_levels_past_goal=1, **_EVERY_WORLD)
assert len(_cw.active_locations()) == len(_cw_all.active_locations()), \
    "the completion goal trimmed something; its goal is the final level"

# A side path revealed past the cut goes with it. Appease-mint opens at
# egypt29, well past egypt8, so a world_key seed cannot build it.
_sp_w, _ = run("goal trim: side paths", goal_type=C.GOAL_WORLD_KEY,
               include_side_paths=1, **_EVERY_WORLD)
_sp_built = {l.region for l in _sp_w.active_locations()}
assert "Appease-mint Sidepath" not in _sp_built, \
    "a side path revealed at egypt29 survived a seed that ends at egypt8"
# ...and one revealed BEFORE the cut stays. Squash opens at egypt6.
assert "Squash Sidepath" in _sp_built, \
    "the Squash quest opens at egypt6 and must survive a world_key seed"

# A store card stocked past the cut goes too.
_sh_w, _ = run("goal trim: shop", goal_type=C.GOAL_WORLD_KEY, shopsanity=1,
               **_EVERY_WORLD)
_sh_built = {l.name for l in _sh_w.active_locations() if l.is_shop}
_late_cards = [C.shop_location_name(_c) for _c, _l in C.SHOP_UNLOCK.items()
               if _l in W.locations.past_goal_names(C.GOAL_WORLD_KEY)]
assert _late_cards, "no shop card is stocked past a World Key level; check the data"
assert not (set(_late_cards) & _sh_built), \
    f"store cards stocked past the goal survived: {sorted(set(_late_cards) & _sh_built)[:4]}"

# THE UNLOCKS SHRINK WITH THE WORLD. A trimmed world is one stretch long, so
# shipping three would be two dead items per world.
_uw, _ = run("goal trim: unlocks", goal_type=C.GOAL_WORLD_KEY, **_EVERY_WORLD)
_ucount = collections.Counter(
    i.name[len("Progressive "):] for i in _uw.multiworld.itempool
    if i.name.startswith("Progressive "))
assert _ucount["Dark Ages"] == 1, f"Dark Ages ships {_ucount['Dark Ages']} unlocks, want 1"
assert "Ancient Egypt" not in _ucount, \
    "Ancient Egypt needs no unlock to reach egypt8, so it must ship none"
_zw, _ = run("goal trim: unlocks, zomboss", goal_type=C.GOAL_ZOMBOSS, **_EVERY_WORLD)
_zcount = collections.Counter(
    i.name[len("Progressive "):] for i in _zw.multiworld.itempool
    if i.name.startswith("Progressive "))
assert _zcount["Dark Ages"] == 2, f"Dark Ages ships {_zcount['Dark Ages']} unlocks, want 2"
assert _zcount["Ancient Egypt"] == 1, "Ancient Egypt wants one unlock to reach egypt25"

# EVERY BUILT LOCATION IS IN A REGION THAT EXISTS. The trap this guards is
# subtle: world_stretches infers its cuts from the names it is handed, so
# cutting from the TRIMMED list would lose the Zomboss, fall into the Kongfu
# fallback and re-split the surviving opening into thirds -- putting egypt6-8
# behind unlocks the seed no longer ships.
for _goal in (C.GOAL_WORLD_KEY, C.GOAL_ZOMBOSS):
    _rw, _ = run(f"goal trim: regions {_goal}", goal_type=_goal,
                 include_side_paths=1, include_danger_rooms=1, **_EVERY_WORLD)
    _regions = {r.name for r in _rw.multiworld.regions}
    for _loc in _rw.active_locations():
        _rw.multiworld.get_location(_loc.name, 1)
    _stray = [r for r in _regions
              if any(r.endswith(sfx) for sfx in (" Mid", " Late"))
              and not any(l.parent_region.name == r
                          for reg in _rw.multiworld.regions for l in reg.locations)]
    assert not _stray, f"goal {_goal}: empty stretch regions were built: {_stray[:4]}"

# THE EDGE CASE KURT NAMED. Ancient Egypt alone under the world_key goal is the
# tutorial plus egypt1-8: twelve locations. It needs exactly ONE progression
# item -- a sun producer, because the egypt6 checkpoint's other half is a cheap
# attacker and the starter is always one, precollected. Everything else is
# useful. This failed to generate outright before the upgrades were made to
# give.
_ew, _esd = run("goal trim: Egypt only, world_key", world_count=1,
                goal_type=C.GOAL_WORLD_KEY, worlds_required=1)
_enames = [l.name for l in _ew.active_locations()]
assert len(_enames) == 12, f"Egypt-only world_key is {len(_enames)} locations, want 12"
assert "egypt8" in _enames and "egypt9" not in _enames, sorted(_enames)
# Eleven, not twelve: egypt8 is the goal level and holds the locked Time Key.
assert len(_ew.multiworld.itempool) == 11, len(_ew.multiworld.itempool)
assert _ew.multiworld.get_location("egypt8", 1).item.name == "Time Key"
_eprog = [i.name for i in _ew.multiworld.itempool
          if i.classification == _IC_j.progression]
# Every progression item is a sun producer, and there is at least one. Not a
# fixed COUNT: since the upgrades started taking a 20% share instead of all 14
# slots, this seed has room for more than one of the five. What matters is that
# nothing ELSE is progression -- the whole point of the Egypt-only case is that
# a sun producer is the only thing the run actually requires.
assert _eprog, "no progression item at all, so egypt8 would be unreachable"
_enonsun = sorted(set(_eprog) - set(C.SUN_PRODUCER_PLANTS))
assert not _enonsun, f"progression items that are not sun producers: {_enonsun}"
assert _esd["goal_locations"] == ["egypt8"], _esd["goal_locations"]
print(f"Egypt-only world_key: {len(_enames)} locations, {len(_eprog)} progression "
      f"(all sun producers), {len(_ew.multiworld.itempool) - len(_eprog)} other")


# THE CROSS-CHECK, ON A TRIMMED SEED. gen_test already checks that the client's
# gate for a location agrees with the region it was built into -- if those
# disagree, fill places progression in a level the player cannot start and
# nothing else notices. That check ran only on untrimmed seeds, which is how a
# real bug survived to 2026-08-25: world_gates cut its stretches from the
# TRIMMED location list while regions.py cut from the full one, so for the two
# worlds with no milestone to cut on the two disagreed by 7 to 10 levels.
#
# Aerial Fortress has neither a World Key level nor a Zomboss and Kongfu Temple
# has no Zomboss, so world_stretches gives them fallback cuts (equal thirds, and
# the midpoint of the remainder). Re-deriving a fallback from an already-trimmed
# list is not the same operation, which is the whole reason both callers must cut
# from the full list.
_SUFFIX_SET = ("", " Early", " Mid", " Late")
for _goal in (C.GOAL_WORLD_KEY, C.GOAL_ZOMBOSS, C.GOAL_COMPLETION):
    _tw, _tsd = run(f"trim cross-check: goal {_goal}", goal_type=_goal,
                    include_side_paths=1, include_danger_rooms=1, **_EVERY_WORLD)
    _gate_need_t = {}
    for _w2, _g2 in _tsd["world_gates"].items():
        for _i2, _part2 in enumerate(_g2["stretches"]):
            for _n2 in _part2:
                _gate_need_t[_n2] = _i2 + 1

    # No empty stretch. A trimmed world ships fewer unlocks, so a gate table
    # listing three stretches with the last two empty tells the client this
    # world needs three unlocks when the pool ships one. It gates nothing
    # either way, but the shape is the interface.
    for _w3, _g3 in _tsd["world_gates"].items():
        assert all(_g3["stretches"]), (
            f"goal {_goal}: {_w3} ships an empty gate stretch "
            f"{[len(x) for x in _g3['stretches']]}")

    # Every gated name is a location this seed actually built.
    _built_t = {l.name for l in _tw.active_locations()}
    _ghosts = sorted(n for n in _gate_need_t if n not in _built_t)
    assert not _ghosts, (
        f"goal {_goal}: world_gates names {len(_ghosts)} location(s) the seed "
        f"does not build: {_ghosts[:5]}")

    # ...and the gate matches the region it was built into.
    _mismatch_t = []
    for _r2 in _tw.multiworld.regions:
        _owner2 = _suffix2 = None
        for _wn2 in C.WORLD_REGIONS:
            if _r2.name == _wn2:
                _suffix2, _owner2 = "", _wn2
            elif _r2.name.startswith(_wn2) and _r2.name[len(_wn2):] in _SUFFIX_SET:
                _suffix2, _owner2 = _r2.name[len(_wn2):], _wn2
        if _owner2 is None:
            continue
        _need2 = C.progressive_need(_owner2, _suffix2)
        for _loc2 in _r2.locations:
            if _loc2.name not in _built_t:
                continue
            if _gate_need_t.get(_loc2.name, 0) != _need2:
                _mismatch_t.append(
                    (_loc2.name, _r2.name, _need2, _gate_need_t.get(_loc2.name, 0)))
    assert not _mismatch_t, (
        f"goal {_goal}: {len(_mismatch_t)} location(s) whose client gate and "
        f"region disagree, so fill can bury progression behind a level that "
        f"cannot be started: {_mismatch_t[:4]}")

# The check must actually SEE the two fallback worlds, or it proves nothing
# about the case that broke.
_fw, _fsd = run("trim cross-check: fallback worlds", goal_type=C.GOAL_ZOMBOSS,
                **_EVERY_WORLD)
for _fb in ("Aerial Fortress", "Kongfu Temple"):
    assert _fb in _fw.enabled_worlds, f"{_fb} is not in the cross-checked seed"
    _fb_locs = [l.name for l in _fw.active_locations()
                if l.region in C.WORLD_REGIONS[_fb]]
    assert len(_fb_locs) > 10, f"{_fb} contributes only {len(_fb_locs)} locations"
print("goal trim: client gates and regions agree on a trimmed seed, "
      "Aerial Fortress and Kongfu Temple included")


# ── Grave Buster gates the back half of two worlds ───────────────────────────
#
# Ancient Egypt and Dark Ages want it for everything past their World Key level.
# Both are cut on their own milestones, so " Mid" is exactly key -> Zomboss and
# " Late" is Zomboss -> final level. Logic only, like every plant requirement:
# it never reaches world_gates, so the client still lets those levels start.

# Literals, not read from the table under test.
assert C.GRAVE_CLEAR_PLANTS == ["Grave Buster"], C.GRAVE_CLEAR_PLANTS
assert sorted(C.STRETCH_ENTRY_PLANTS) == ["Ancient Egypt", "Dark Ages"], \
    sorted(C.STRETCH_ENTRY_PLANTS)
for _sw in ("Ancient Egypt", "Dark Ages"):
    assert sorted(C.STRETCH_ENTRY_PLANTS[_sw]) == [" Late", " Mid"], \
        sorted(C.STRETCH_ENTRY_PLANTS[_sw])
# It has an item, or the rule could never pass and would fail silently.
assert "Grave Buster" in {p.name for p in PLANT_ITEMS}
# ...and it is rule-named, so starting_plants may never hand it over.
assert "Grave Buster" in C.LOGIC_PLANTS, \
    "Grave Buster is not in LOGIC_PLANTS, so the starting draw could grant it"

# Progression in a seed that builds those stretches, useful in one that does
# not. Asserted through create_item: apstub's collect() ignores classification,
# so no state-driven test could catch this being wrong.
_gw, _ = run("grave: full seed", **ALL_WORLDS)
assert _gw.create_item("Grave Buster").classification == _IC_j.progression, \
    "Grave Buster is not progression in a seed whose Egypt Mid wants it"

# The world_key goal ends Ancient Egypt at egypt8 and Dark Ages at dark10, so
# neither " Mid" nor " Late" is built and nothing names it.
_gk, _ = run("grave: world_key goal", goal_type=C.GOAL_WORLD_KEY, **_EVERY_WORLD)
assert _gk.create_item("Grave Buster").classification == _IC_j.useful, \
    ("Grave Buster is progression under the world_key goal, which builds no "
     "stretch that wants it")

# The zomboss goal builds " Mid" but not " Late", so it IS wanted again.
_gz, _ = run("grave: zomboss goal", goal_type=C.GOAL_ZOMBOSS, **_EVERY_WORLD)
assert _gz.create_item("Grave Buster").classification == _IC_j.progression, \
    "the zomboss goal builds Egypt Mid, which wants Grave Buster"

# A seed with neither world does not want it either.
_gn, _ = run("grave: neither world", world_count=2,
             enabled_worlds=["Pirate Seas"], include_levels_past_goal=1)
assert "Ancient Egypt" in _gn.enabled_worlds and "Dark Ages" not in _gn.enabled_worlds
# Ancient Egypt is always in, so this one still wants it -- the honest check is
# a seed whose ONLY grave world is Egypt still names it.
assert _gn.create_item("Grave Buster").classification == _IC_j.progression, \
    "Ancient Egypt alone still wants Grave Buster past egypt8"

# THE POOL FLOOR keeps it. Squeezed to EXACTLY the floor, the way the
# entry-plant floor test is: with slack the trim tops the pool up at random and
# a plant appearing proves nothing about what was forced.
#
# Egypt-only with the levels past the goal kept builds egypt9-35, so its floor is
# TWO plants now -- a sun producer for the egypt6 checkpoint, and Grave Buster
# for " Mid". The attacker half is free from the precollected starter.
_gf, _ = run("grave: small seed floor", world_count=1,
             include_levels_past_goal=1, worlds_required=1)
# Squeezed to the floor itself: two plants, a sun producer for the egypt6
# checkpoint and Grave Buster for " Mid". Four slots, because this seed keeps
# the levels past the goal and so ships Ancient Egypt's two unlocks; 20% of four
# locations is no upgrade and shopsanity is off, so the other two slots are
# exactly the floor and whatever survives IS what it forced.
_gf_pool = {i.name for i in W.items.create_item_pool(_gf, 4)}
_gf_plants = _gf_pool & {p.name for p in W.items.PLANT_ITEMS}
assert len(_gf_plants) == 2, f"floor is {sorted(_gf_plants)}, expected 2 plants"
assert "Grave Buster" in _gf_plants, (
    f"the floor dropped Grave Buster, which Egypt Mid needs: {sorted(_gf_plants)}")
assert set(C.SUN_PRODUCER_PLANTS) & _gf_plants, "floor has no sun producer"

# It is LOGIC ONLY: world_gates must never mention a plant, so the client keeps
# letting those levels start.
_gg, _gsd2 = run("grave: not client-enforced", **ALL_WORLDS)
for _w4, _g4 in _gsd2["world_gates"].items():
    assert _g4["item"].startswith("Progressive "), \
        f"{_w4} gates on {_g4['item']}, which is not an unlock"
print("Grave Buster: gates Mid and Late of Ancient Egypt and Dark Ages, "
      "progression only when those stretches are built")


# ── create_item must never raise ─────────────────────────────────────────────
#
# Classification is per slot, so create_item reads enabled_worlds, logic_attackers
# and logic_jesters -- all filled in by generate_early. Generation always runs
# that first, but a TRACKER does not: Universal Tracker rebuilds the world itself
# and resolves items against it. An AttributeError there leaves the tracker with
# no item to reason about, which reads to a player as "I am holding the plant and
# nothing opened".
#
# enabled_worlds had no class-level default and raised for exactly that reason.
_bare_mw = MultiWorld()
_bare = W.PvZ2GardendlessWorld(_bare_mw, 1)
_bare.options = Opts()
for _attr in ("enabled_worlds", "logic_attackers", "logic_jesters", "starting_plants"):
    assert hasattr(_bare, _attr), \
        f"{_attr} has no class-level default, so create_item raises before generate_early"
# Every item name the game defines, on a world that has not generated.
for _n in W.items.ITEM_NAME_TO_ID:
    _bare.create_item(_n)
# ...and a sun producer still comes back progression, since that is slot
# independent -- a silent demotion here would make a tracker call the Egypt 6
# gate unsatisfiable while the player holds the plant that opens it.
assert _bare.create_item("Sunflower").classification == _IC_j.progression, \
    "a sun producer is not progression before generate_early"
print(f"create_item: all {len(W.items.ITEM_NAME_TO_ID)} items resolve on a world "
      f"that has not run generate_early")


# ── goal levels hold the McGuffin, and nothing else ──────────────────────────
#
# Each goal level carries a locked McGuffin, which is what makes the win an
# item rather than a location-reachability rule. Locked means fill never sees
# the location at all -- so this replaces the old "goal locations accept only
# this slot's items" item rule, which existed to stop another player's
# progression sitting behind a level its owner had no reason to play.
for _gt3 in (C.GOAL_WORLD_KEY, C.GOAL_ZOMBOSS, C.GOAL_COMPLETION):
    _lw, _lsd = run(f"goal mcguffins: goal {_gt3}", goal_type=_gt3, **ALL_WORLDS)
    _goals3 = _lsd["goal_locations"]
    assert _goals3, "no goal locations, so this proves nothing"
    _mcg = _lsd["goal_item"]
    for _gn in _goals3:
        _gl = _lw.multiworld.get_location(_gn, 1)
        assert _gl.item is not None and _gl.item.name == _mcg,             f"goal {_gn} holds {_gl.item and _gl.item.name}, not {_mcg}"
        assert _gl.item.player == 1, f"goal {_gn} holds another slot's McGuffin"
        assert _gl.locked, f"goal {_gn} is not locked; fill could move the McGuffin"

    # The McGuffin exists ONLY on goal levels. One loose in the pool would let
    # the goal be met without completing the world it stands for.
    assert not [i for i in _lw.multiworld.itempool if i.name == _mcg],         f"{_mcg} is in the fillable pool as well as on the goal levels"
    # And the other two goal types' McGuffins are not in this seed at all.
    _others = set(W.items.GOAL_ITEM_NAMES) - {_mcg}
    assert not [i for i in _lw.multiworld.itempool if i.name in _others],         "a seed ships a McGuffin belonging to a goal type it did not roll"

# A NON-goal location is untouched: still fillable, still open to anyone.
_open3 = [l for r in _lw.multiworld.get_regions(1)
          for l in r.locations if l.name not in set(_goals3)]
assert any(l.item is None for l in _open3),     "every location is pre-filled; the McGuffins are not scoped to the goals"
print(f"goal mcguffins: {len(_goals3)} goal levels each hold a locked {_mcg}")


# ── the upgrades take a proportional share ───────────────────────────────────
#
# All 14 upgrades are mandatory and gate nothing, so in a small seed they used
# to crowd out the plants entirely: Ancient Egypt alone under the world_key goal
# is 12 locations, and 14 upgrades left room for none. They now take at most
# UPGRADE_POOL_SHARE percent of the seed.
#
# A percentage is self-limiting: 20% of a full seed is far past the 14 that
# exist, so this only ever bites where it was needed.
assert C.UPGRADE_POOL_SHARE == 20, C.UPGRADE_POOL_SHARE
_UPG_NAMES = {u.name for u in W.items.UPGRADE_ITEMS}

# A full seed still ships every upgrade -- the cap must not touch it.
_ub, _ = run("upgrade share: full seed", **ALL_WORLDS)
_ub_n = sum(1 for i in _ub.multiworld.itempool if i.name in _UPG_NAMES)
assert _ub_n == C.UPGRADE_ITEM_COUNT, \
    f"a full seed ships {_ub_n} upgrades, not all {C.UPGRADE_ITEM_COUNT}"

# The smallest seed there is: 12 locations, so at most 2 upgrades, and the rest
# goes to plants. Literals, because the point is the SHAPE of a small seed.
_us, _ = run("upgrade share: Egypt only", world_count=1, worlds_required=1)
_us_locs = len(_us.active_locations())
_us_pool = [i.name for i in _us.multiworld.itempool]
_us_n = sum(1 for n in _us_pool if n in _UPG_NAMES)
_us_plants = sum(1 for n in _us_pool if n in {p.name for p in PLANT_ITEMS})
assert _us_locs == 12, f"Egypt-only world_key is {_us_locs} locations, want 12"
assert _us_n <= _us_locs * C.UPGRADE_POOL_SHARE // 100, \
    f"{_us_n} upgrades in a {_us_locs}-location seed exceeds the share"
assert _us_n == 2, f"expected 2 upgrades in a 12-location seed, got {_us_n}"
# ...and the point of the whole exercise: the seed is mostly plants now.
assert _us_plants >= 8, \
    f"only {_us_plants} plants in a 12-location seed; the share bought nothing"
print(f"upgrade share: {_us_n} upgrades and {_us_plants} plants in a "
      f"{_us_locs}-location seed, all {_ub_n} upgrades in a full one")

# The share holds across every small size, not just the one measured above.
for _wc3 in (1, 2, 3, 4):
    _uw, _ = run(f"upgrade share: {_wc3} worlds", world_count=_wc3,
                 worlds_required=1)
    _un = sum(1 for i in _uw.multiworld.itempool if i.name in _UPG_NAMES)
    _ulocs = len(_uw.active_locations())
    assert _un <= max(_ulocs * C.UPGRADE_POOL_SHARE // 100, 0), \
        f"{_wc3} worlds: {_un} upgrades exceeds the share of {_ulocs} locations"
