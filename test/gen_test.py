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
)
from apstub import DeathLink


class Opts:
    def __init__(self, **kw):
        self.world_count = WorldCount(kw.get("world_count", WorldCount.default))
        self.enabled_worlds = EnabledWorlds(frozenset(kw.get("enabled_worlds", ())))
        self.goal_type = GoalType(kw.get("goal_type", GoalType.default))
        self.worlds_required = WorldsRequired(kw.get("worlds_required", 7))
        self.modern_day_victory = ModernDayVictory(kw.get("modern_day_victory", 1))
        self.skip_tutorial = SkipTutorial(kw.get("skip_tutorial", 0))
        self.include_side_paths = IncludeSidePaths(
            kw.get("include_side_paths", IncludeSidePaths.default))
        self.include_danger_rooms = IncludeDangerRooms(
            kw.get("include_danger_rooms", IncludeDangerRooms.default))
        self.shopsanity = Shopsanity(kw.get("shopsanity", 0))
        self.shuffle_upgrades = ShuffleUpgrades(kw.get("shuffle_upgrades", ShuffleUpgrades.default))
        self.randomize_conveyor_plants = RandomizeConveyorPlants(
            kw.get("randomize_conveyor_plants", RandomizeConveyorPlants.default))
        self.shuffle_zombies = ShuffleZombies(kw.get("shuffle_zombies", 0))
        self.early_world_keys = EarlyWorldKeys(kw.get("early_world_keys", 0))
        self.trap_percentage = TrapPercentage(kw.get("trap_percentage", 5))
        self.death_link = DeathLink(0)


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
    keys = [i.name for i in mw.itempool if i.name.endswith(" Key")]
    built = {r.name for r in mw.regions}
    dead = {r for r in C.ALL_WORLD_REGIONS if r not in w.enabled_regions}

    print(f"\n=== {label} ===")
    print(f"  worlds({len(w.enabled_worlds)}): {sorted(w.enabled_worlds)}")
    print(f"  locations={len(locs)}  itempool={len(mw.itempool)}  keys={len(keys)}")
    print(f"  goal_type={sd['goal_type']} worlds_required={sd['worlds_required']}"
          f" goal_locations={len(sd['goal_locations'])}")
    assert len(locs) == len(mw.itempool), "pool must exactly fill locations"
    assert not (built & dead), f"built a disabled region: {built & dead}"
    # every location built lands in a region that exists
    for loc in locs:
        assert loc.region in built, f"{loc.name} -> missing region {loc.region}"
    # no key for a disabled world
    for k in keys:
        assert C.KEY_NAME_TO_WORLD[k] in w.enabled_worlds, f"stray key {k}"
    assert "Modern Day Key" not in keys
    # goal locations all exist and are reachable-by-name
    for name in sd["goal_locations"]:
        mw.get_location(name, 1)
    # the free starting plant must be able to hold a lane: no single-use
    # instants, no non-damaging support
    from pvz2gardendless.constants import (STARTER_PLANTS, SINGLE_USE_PLANTS,
                                           NON_DAMAGING_PLANTS,
                                           SUN_PRODUCER_PLANTS)
    assert len(mw.precollected) == 1, "expected exactly one starting plant"
    starter = mw.precollected[0].name
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
    # Every sun producer has to actually be in the pool, or the gate is a wall.
    _pool_names = {i.name for i in mw.itempool}
    assert set(SUN_PRODUCER_PLANTS) <= _pool_names, \
        f"sun producers missing from the pool: {sorted(set(SUN_PRODUCER_PLANTS) - _pool_names)}"
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
    from pvz2gardendless.constants import CHEAP_ATTACKER_PLANTS
    _overlap = set(NON_DAMAGING_PLANTS) & set(CHEAP_ATTACKER_PLANTS)
    assert not _overlap, f"non-damaging plants count as attackers: {_overlap}"
    # Water-only plants cannot be placed on Ancient Egypt's terrain.
    for _wet in ("Tangle Kelp", "Lily Pad"):
        assert _wet not in CHEAP_ATTACKER_PLANTS, f"{_wet} is water-only"
    # Real attackers the old Family heuristic wrongly dropped.
    for _good in ("Puff-shroom", "Pea-nut", "Chard Guard", "Endurian"):
        assert _good in CHEAP_ATTACKER_PLANTS, f"{_good} should be an attacker"
    # Sheetless plants are attackers by inspection, not omissions.
    for _ns in ("Scaredy-shroom", "Vamporcini", "Skyshooter"):
        assert _ns in CHEAP_ATTACKER_PLANTS, f"{_ns} dropped for having no sheet"
    assert sd["worlds_required"] <= len(sd["goal_locations"])
    assert sd["worlds_required"] >= 1, "goal must stay satisfiable"
    # indirect conditions registered for every goal
    assert len(mw.indirect) == len(sd["goal_locations"])
    from pvz2gardendless.items import UPGRADE_ITEMS
    from pvz2gardendless.constants import UPGRADE_GROUPS, UPGRADE_ITEM_COUNT
    upnames = {u.name for u in UPGRADE_ITEMS}
    ups = [i.name for i in mw.itempool if i.name in upnames]
    want = UPGRADE_ITEM_COUNT if w.options.shuffle_upgrades else 0
    assert len(ups) == want, f"upgrade copies in pool {len(ups)} != {want}"
    if w.options.shuffle_upgrades:
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
run("explicit + topup", world_count=5, enabled_worlds=["Big Wave Beach"])
run("trophies, 3 worlds", world_count=3, goal_type=0, worlds_required=11)
run("completions, 2 worlds", world_count=2, goal_type=1, worlds_required=11,
    include_side_paths=1)
run("3 worlds + shopsanity", world_count=3, shopsanity=1, worlds_required=11)
run("all worlds + shopsanity + traps", shopsanity=1, trap_percentage=50)

# explicit beats a lower count
w, _ = run("explicit 4 vs count 2", world_count=2,
           enabled_worlds=["Pirate Seas", "Wild West", "Far Future", "Dark Ages"])
assert {"Pirate Seas", "Wild West", "Far Future", "Dark Ages"} <= w.enabled_worlds
assert "Ancient Egypt" in w.enabled_worlds and "Modern Day" in w.enabled_worlds

# Egypt counts toward world_count: 3 => Egypt + 2 others (+ Modern Day)
w, _ = run("count semantics", world_count=3)
assert len(w.enabled_worlds - {"Modern Day"}) == 3, w.enabled_worlds

# determinism for a given slot seed
a, _ = run("determinism A", world_count=4)
b, _ = run("determinism B", world_count=4)
assert a.enabled_worlds == b.enabled_worlds

# Frostbite Caves entry-plant rule only when the world is in
w, _ = run("BWB forced in", world_count=1, enabled_worlds=["Big Wave Beach"],
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
    {"shuffle_zombies", "zombie_tiers", "zombie_seed"}, \
    f"unexpected new slot_data keys: {sorted(set(_z_on) - _SLOT_DATA_BEFORE_ZOMBIES)}"

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
                                   COIN_TRAP, GEM_TRAP)
BLOCKS = [
    ("plants+keys+filler+traps", PLANT_ITEMS + KEY_ITEMS + FILLER_ITEMS + TRAP_ITEMS),
    ("upgrades", UPGRADE_ITEMS),
    ("costume filler", COSTUME_ITEMS),
    ("costume trap", COSTUME_TRAP_ITEMS),
    ("currency traps", CURRENCY_TRAP_ITEMS),
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
_expected = _rand | _orphan_rooms | _orphan_paths | {"iceage24_B"}
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
_pw, _ = run("side path parents", include_side_paths=1, include_danger_rooms=1)
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
# branch "6-1" and the Appease-mint branch "29-1", and locations.py puts egypt6
# in Mid1 and egypt29 in Mid2. Those two are the whole reason for the change --
# Egypt's opening is ungated, so a path left on it is in sphere 1.
for _sp, _want_region in (("Squash Sidepath", "Ancient Egypt Mid1"),
                          ("Appease-mint Sidepath", "Ancient Egypt Mid2")):
    _got = _pmw.get_entrance(f"Enter {_sp}", 1).parent_region.name
    assert _got == _want_region, f"{_sp} hangs off {_got}, want {_want_region}"
# 16 of the 27 land past their world's opening stretch. The other 11 branch
# early enough that the opening third really is where the game puts them
# (dark4, beach7, lostcity8, dark9, modern10, kongfu12, iceage12, future13,
# beach14, eighties14, dark16), so a bigger number here would mean the stretch
# cut had moved, not that the gating got better.
_deep = [_sp for _sp in C.SIDE_PATH_UNLOCK
         if _pmw.get_entrance(f"Enter {_sp}", 1).parent_region.name
         not in C.ALL_WORLD_REGIONS]
assert len(_deep) == 16, f"{len(_deep)} side paths are gated past a world opening, want 16"
print(f"all {len(C.SIDE_PATH_UNLOCK)} branch side paths hang off their unlock level's "
      f"region ({len(_deep)} past the world opening), Hot Date chains off Sweet Potato")

# Shop cards: the gate table has to agree with the commodity list and with the
# locations, or a card is either ungated or gated on something that is not there.
_shop_names = {C.shop_location_name(c) for c in C.SHOP_COMMODITIES}
assert set(C.SHOP_UNLOCK) <= set(C.SHOP_COMMODITIES),     f"SHOP_UNLOCK names commodities that are not sold: "     f"{sorted(set(C.SHOP_UNLOCK) - set(C.SHOP_COMMODITIES))}"
# The ten with no UnlockLevel in the game's store data. Pinned as literals from
# `StoreCommodityFeatures` rather than derived, so a card losing its gate by
# accident shows up here instead of quietly becoming an egypt6 check.
assert set(C.SHOP_COMMODITIES) - set(C.SHOP_UNLOCK) == {
    "jalapeno", "mirrornut", "wasabiwhip", "pyrevine", "cranjelly",
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
_e1w, _ = run("shop cards drop with their world", world_count=1, shopsanity=1,
              worlds_required=11)
_e1shop = {l.name for l in _e1w.active_locations() if l.is_shop}
_egypt_cards = {C.shop_location_name(_c) for _c, _l in C.SHOP_UNLOCK.items()
                if _lnames[_l] in C.WORLD_REGIONS["Ancient Egypt"]}
_modern_cards = {C.shop_location_name(_c) for _c, _l in C.SHOP_UNLOCK.items()
                 if _lnames[_l] in C.WORLD_REGIONS["Modern Day"]}
_ungated_cards = {C.shop_location_name(_c) for _c in C.SHOP_COMMODITIES
                  if _c not in C.SHOP_UNLOCK}
_want_1w = _ungated_cards | _egypt_cards | _modern_cards
assert _e1shop == _want_1w,     f"one-world shop checks wrong: missing {sorted(_want_1w - _e1shop)}, "     f"extra {sorted(_e1shop - _want_1w)}"
# ...and every world back in restores all 39, so the filter is not just deleting.
_eall, _ = run("shop cards with every world", shopsanity=1)
assert {l.name for l in _eall.active_locations() if l.is_shop} == _shop_names,     "some shop checks are missing from an all-worlds seed"
print(f"shop: {len(C.SHOP_UNLOCK)} of {len(C.SHOP_COMMODITIES)} cards gated on their "
      f"UnlockLevel, {len(_e1shop)} survive an Egypt-only seed")

# Hint buckets. The point is that "!hint World Keys" answers where all of them
# are in one command, so the group has to hold every key -- and the singular has
# to resolve to the same set, since AP matches a group name exactly and a player
# types whichever reads naturally.
from pvz2gardendless.items import ITEM_NAME_GROUPS, ALL_ITEMS, KEY_ITEMS
_keynames = {i.name for i in KEY_ITEMS}
assert ITEM_NAME_GROUPS["World Keys"] == _keynames,     f"World Keys group is not the key items: {ITEM_NAME_GROUPS['World Keys'] ^ _keynames}"
assert ITEM_NAME_GROUPS["World Key"] == ITEM_NAME_GROUPS["World Keys"],     "the singular alias does not match the plural"
for _p, _sg in (("Plants", "Plant"), ("Traps", "Trap"), ("Upgrades", "Upgrade"),
                ("Costumes", "Costume"), ("Coins", "Coin"), ("Gems", "Gem")):
    assert ITEM_NAME_GROUPS[_sg] == ITEM_NAME_GROUPS[_p], f"{_sg} does not match {_p}"
# Every item hintable as part of something. The currencies and the costume were
# in no group at all, so there was no way to ask about them as a set.
_allnames = {i.name for i in ALL_ITEMS}
_ungrouped = _allnames - set().union(*ITEM_NAME_GROUPS.values())
assert not _ungrouped, f"items in no hint group: {sorted(_ungrouped)}"
# A group naming something that is not an item would hint nothing.
for _g, _members in ITEM_NAME_GROUPS.items():
    assert _members, f"hint group {_g} is empty"
    _ghost = _members - _allnames
    assert not _ghost, f"group {_g} names non-items: {sorted(_ghost)}"
# Negative currency stays out of Coins/Gems: those are traps, and answering
# "where are my coins" with the places that take them away is worse than
# answering nothing.
assert not (ITEM_NAME_GROUPS["Currency"] & ITEM_NAME_GROUPS["Traps"]),     "a currency trap leaked into the Currency group"
# ...and a real seed's keys are all in the group, not just the static table.
_hw, _ = run("hint groups", shopsanity=1)
_pool_keys = {i.name for i in _hw.multiworld.itempool if i.name.endswith(" Key")}
assert _pool_keys <= ITEM_NAME_GROUPS["World Keys"],     f"keys in the pool but not the group: {sorted(_pool_keys - ITEM_NAME_GROUPS['World Keys'])}"
print(f"hint groups: {len(ITEM_NAME_GROUPS)} buckets over {len(_allnames)} items, "
      f"World Keys covers all {len(_pool_keys)} keys in the pool")

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
_wt, _ = run("currency traps at 100%", trap_percentage=100)
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
# An ITEM rule, not an access rule: it must change where fill may put keys and
# nothing else. Locations, pool size and logic all have to come out identical.
from pvz2gardendless.constants import is_early_region, KEYED_WORLDS
from apstub import MultiWorld as _MW


def _key_placement(**kw):
    mw = _MW()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    w.generate_early(); w.create_regions(); w.set_rules(); w.create_items()
    # A synthetic key rather than one drawn from the pool: a 1-world seed has
    # no keys in its pool at all, and `all()` over an empty set is vacuously
    # true, which would silently pass the whole probe.
    probe_key = w.create_item("Pirate Seas Key")
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
_keys_needed = sum(1 for i in _mw.itempool if i.name.endswith(" Key"))
assert _allowed >= _keys_needed, \
    f"only {_allowed} spots left for {_keys_needed} keys -- fill would fail"
print(f"early_world_keys on:  {_allowed} legal spots, {_denied} closed off, "
      f"{_keys_needed} keys to place")

# Modern Day is the latest place in any seed, so it must refuse keys too.
for _r in _mw.regions:
    if _r.name == "Modern Day":
        for _loc in _r.locations:
            assert not all(_loc.item_rule(i) for i in _mw.itempool
                           if i.name.endswith(" Key")), \
                f"Modern Day location {_loc.name} accepts a key"

# The rule must not touch anything that is not a key.
_plant = next(i for i in _mw.itempool if i.name == "Peashooter")
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

_dr_off, _ = run("danger rooms off", include_danger_rooms=0)
_dr_on, _ = run("danger rooms on", include_danger_rooms=1)
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
}
from pvz2gardendless.locations import WORLD_COMPLETION_LOCS as _WC, WORLD_TROPHY_LOCS as _WT
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
assert not _both, f"location used as BOTH trophy and completion goal: {sorted(_both)}"
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
_misnamed = [(l.name, _lvl[l.name]) for l in _wl if _lvl[l.name] != l.name]
assert not _misnamed, \
    f"world locations not named for their level id: {_misnamed[:5]}"
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

# ── small seeds trim useful plants rather than failing ──────────────────────
# A one-world seed with side paths off has 101 locations (140 with shopsanity)
# against a 149-item block. The useful plants are the only part that can give:
# they are named by no access rule, so shipping fewer of them costs reachability
# nothing. Progression plants, keys and upgrades all have to survive.
from apstub import ItemClassification as _IC
_prog_plants = {p.name for p in W.items.PLANT_ITEMS
                if p.classification == _IC.progression}

for _label, _kw in (("1 world", dict(world_count=1)),
                    ("1 world + shopsanity", dict(world_count=1, shopsanity=1)),
                    ("2 worlds", dict(world_count=2))):
    _w, _ = run(f"trim: {_label}", include_side_paths=0, worlds_required=11, **_kw)
    _mwT = _w.multiworld
    _names = [i.name for i in _mwT.itempool]
    _missing = _prog_plants - set(_names)
    assert not _missing, f"{_label}: dropped progression plants {sorted(_missing)[:5]}"
    _keys = [n for n in _names if n.endswith(" Key")]
    for _k in _keys:
        assert C.KEY_NAME_TO_WORLD[_k] in _w.enabled_worlds
    assert len(_names) == len(_w.active_locations()), f"{_label}: pool does not fill"
    _dupes = [n for n, c in collections.Counter(
        n for n in _names if n in _prog_plants).items() if c > 1]
    assert not _dupes, f"{_label}: duplicated a progression plant {_dupes}"

# ...and the trim is stable for a slot: same options, same plants dropped.
_a1, _ = run("trim determinism A", world_count=1, include_side_paths=0, worlds_required=11)
_b1, _ = run("trim determinism B", world_count=1, include_side_paths=0, worlds_required=11)
assert (sorted(i.name for i in _a1.multiworld.itempool)
        == sorted(i.name for i in _b1.multiworld.itempool)), "trim is not deterministic"
print("small seeds trim useful plants, keeping every progression plant and key")
