"""Reachability and sphere-depth checks for the world-stretch logic.

Two things matter and neither is visible from the region graph alone:
  1. completability -- with every progression item, is everything reachable?
     An over-tight rule shows up here as a location nothing can get to.
  2. layering -- does the seed actually open in stages, or is it still one
     sphere wearing three region names?
"""
import sys, os, collections

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
sys.path.insert(0, os.path.dirname(S))
import apstub
from apstub import MultiWorld, CollectionState, ItemClassification as IC
import gen_test
import pvz2gardendless as W
from pvz2gardendless.items import PLANT_ITEMS, ITEM_NAME_GROUPS
from pvz2gardendless import constants as C
from pvz2gardendless.options import GoalType

PROG_PLANTS = [p.name for p in PLANT_ITEMS if p.classification == IC.progression]

failed = 0


def fail(m):
    global failed
    failed += 1
    print("  FAIL  " + m)


def ok(m):
    print("  ok    " + m)


def build(**kw):
    """A seed for the sphere checks.

    include_levels_past_goal defaults ON here, unlike generation, because these
    tests reason about the WHOLE logic structure -- egypt9 opening on one unlock,
    egypt26 on two, every world's Mid and Late stretches. The default goal trims
    each world at its World Key level, so those stretches would simply not exist
    and the checks would pass vacuously. The trim gets its own checks at the end
    of this file; pass include_levels_past_goal=0 to reach it.
    """
    kw.setdefault("include_levels_past_goal", 1)
    mw = MultiWorld()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = gen_test.Opts(**kw)
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    return mw, w


def state_with(mw, names):
    st = CollectionState(mw, ITEM_NAME_GROUPS)
    for n in names:
        st.collect(n)
    st.sweep()
    return st


def report(label, **kw):
    global failed
    mw, w = build(**kw)
    total = len(w.active_locations())
    print(f"\n=== {label} ===  {len(w.enabled_worlds)} worlds, {total} locations")

    # --- 1. everything reachable with the full progression pool -------------
    allprog = [i.name for i in mw.itempool if i.classification == IC.progression]
    allprog += [i.name for i in mw.precollected]
    st = state_with(mw, allprog)
    reach = st.reachable_locations()
    names = {l.name for l in reach}
    placed = [l for r in mw.regions for l in r.locations]
    unreachable = [l.name for l in placed if l.name not in names]
    if unreachable:
        fail(f"{len(unreachable)} unreachable with every progression item: {unreachable[:6]}")
    else:
        ok(f"all {len(placed)} placed locations reachable with the full pool")

    victory = [l for l in placed if l.name == "Victory"]
    if not victory:
        fail("no Victory location")
    elif victory[0].name not in names:
        fail("Victory unreachable with every progression item")
    else:
        ok("Victory reachable")

    # --- 2. layering ---------------------------------------------------------
    steps = [
        ("start (precollected only)", [i.name for i in mw.precollected]),
        ("+6 plants", [i.name for i in mw.precollected] + PROG_PLANTS[:6]),
        ("+12 plants", [i.name for i in mw.precollected] + PROG_PLANTS[:12]),
        ("+all plants", [i.name for i in mw.precollected] + PROG_PLANTS),
        ("+all plants +keys", allprog),
    ]
    prev = 0
    line = []
    for label, items in steps:
        n = len(state_with(mw, items).reachable_locations())
        line.append(f"{label} {n}")
        if n < prev:
            fail(f"reachable count went backwards at '{label}'")
        prev = n
    print("        " + "  ->  ".join(line))

    # Isolate what the stretch rules actually govern: locations inside a world.
    # Side paths, Tutorial and Shop are ungated by design and dominate a small
    # seed, so measuring against the whole seed says more about the side paths
    # than about this logic.
    from pvz2gardendless.constants import ALL_WORLD_REGIONS
    world_locs = {l.name for l in w.active_locations() if l.region in ALL_WORLD_REGIONS}
    keys = [i.name for i in mw.itempool if i.name.endswith(" Key")]
    pre = [i.name for i in mw.precollected]

    def world_reach(items):
        return len([l for l in state_with(mw, items).reachable_locations()
                    if l.name in world_locs])

    k0 = world_reach(pre + keys)                      # every key, almost no plants
    k12 = world_reach(pre + keys + PROG_PLANTS[:12])  # every key, plants for both gates
    kall = world_reach(pre + keys + PROG_PLANTS)
    print(f"        world locations: keys only {k0}  ->  keys+12 plants {k12}"
          f"  ->  keys+all {kall}  (of {len(world_locs)})")
    if kall == 0:
        fail("no world locations reachable at all")
    elif k0 >= kall:
        fail("holding every key opens every world location -- stretches gate nothing")
    else:
        held = k0 / kall * 100
        ok(f"keys alone open {held:.0f}% of world locations; plants gate the other "
           f"{100 - held:.0f}%")

    first = len(state_with(mw, pre).reachable_locations())
    # Shop is NOT counted here any more: it hangs off Ancient Egypt Mid1, since
    # the game only grows a store button once egypt6 is cleared.
    # Side paths are NOT counted here any more either: each one hangs off the
    # stretch holding the level that reveals it, so the only thing left that is
    # ungated by design is the tutorial.
    ungated = len([l for l in w.active_locations() if l.region == "Tutorial"])
    print(f"        sphere 1 {first} of {total} ({first / total * 100:.0f}%) "
          f"-- {ungated} of those are the tutorial, ungated by design")

    # --- 3. the stretches actually gate something ---------------------------
    stretch_regions = [r for r in mw.regions if r.name.endswith((" Mid", " Late"))]
    empty = [r.name for r in stretch_regions if not r.locations]
    if empty:
        fail(f"stretch regions with no locations: {empty}")
    elif stretch_regions:
        sizes = collections.Counter()
        for r in stretch_regions:
            sizes[r.name.rsplit(" ", 1)[1]] += len(r.locations)
        ok(f"{len(stretch_regions)} stretch regions built, "
           f"{sizes[' Mid'.strip()]} mid + {sizes['Late']} late locations")
    return w


# The eleven random_* levels are defined in the game data but attached to no
# map node, so their checks can never fire. They used to be reachable in logic,
# and random_zomboss_egypt sat in Ancient Egypt's opening stretch -- a
# preferred early-fill target that no player could ever check.
_mwU, _wU = build()
_sphere1 = {l.name for l in state_with(_mwU, [i.name for i in _mwU.precollected])
            .reachable_locations()}
from pvz2gardendless.constants import UNREACHABLE_LOCATIONS
_bad = sorted(UNREACHABLE_LOCATIONS & _sphere1)
if _bad:
    fail(f"unreachable levels are in sphere 1: {_bad}")
else:
    ok(f"none of the {len(UNREACHABLE_LOCATIONS)} unreachable levels is in sphere 1")
_placedU = {l.name for r in _mwU.regions for l in r.locations}
_bad2 = sorted(UNREACHABLE_LOCATIONS & _placedU)
if _bad2:
    fail(f"unreachable levels were built into regions: {_bad2}")
else:
    ok("...and none is built into a region at all")

# ── a Danger Room is never in logic before the level that unlocks it ────────
# In game the room's map node reads its own level progress, which nothing
# raises except beating the level whose FirstRewardParam names its trophy
# (constants.DANGER_ROOM_UNLOCK). Five rooms lead their world's location list
# and so landed in that world's OPENING stretch -- iceage/lostcity/kongfu/
# eighties/dino_dangerroom -- while the game does not hand them over until
# level 14-20, so they were reachable the moment the world's key turned up.
#
# Proved over many item sets, not one: the claim is that the room NEVER
# precedes its unlock, and most states cannot tell the difference. THE STATE
# THAT DISCRIMINATES IS "every key plus a single sun producer" -- a world is
# open, its opening stretch is reachable, and its Mid stretch (6 plants) is
# not, which is exactly where a room sitting in the opening leaks. Delete the
# rule in rules.py and that one row reports lostcity_dangerroom and
# eighties_dangerroom; a ladder that jumps straight from 3 plants to 6 passes
# clean with the rule gone, which is what this test did on its first draft.
#
# The random sweep is there so the same hole cannot reopen for a room whose
# world happens to want more plants at its entrance. Fixed seed: this suite has
# to give the same answer twice.
import random as _rndD
from pvz2gardendless.constants import DANGER_ROOM_UNLOCK, SUN_PRODUCER_PLANTS as _SUND

print("\n=== danger rooms wait for their unlock level ===")
_mwD, _wD = build(include_danger_rooms=1)
_preD = [i.name for i in _mwD.precollected]
_keysD = [i.name for i in _mwD.itempool if i.name.endswith(" Key")]
_placedD = {l.name for r in _mwD.regions for l in r.locations}
_roomsD = {r: u for r, u in DANGER_ROOM_UNLOCK.items() if r in _placedD}
if not _roomsD:
    fail("no Danger Rooms were built, so this proves nothing")
else:
    _ladder = [("precollected only", _preD), ("+keys", _preD + _keysD)]
    # One row per sun producer, since which one fill hands over first varies.
    _ladder += [(f"+keys +{_p}", _preD + _keysD + [_p]) for _p in _SUND]
    # ...and every plant count either side of the 6-plant Mid gate.
    _ladder += [(f"+keys +{_n} plants", _preD + _keysD + PROG_PLANTS[:_n])
                for _n in range(1, 14)]
    _ladder.append(("+keys +all plants", _preD + _keysD + PROG_PLANTS))
    _rng = _rndD.Random(0)
    _poolD = sorted({i.name for i in _mwD.itempool
                     if i.classification == IC.progression})
    _ladder += [(f"random {_i}", _preD + _rng.sample(_poolD, _rng.randint(1, 20)))
                for _i in range(60)]
    _early = []
    for _label, _items in _ladder:
        _r = {l.name for l in state_with(_mwD, _items).reachable_locations()}
        for _room, _unlock in sorted(_roomsD.items()):
            if _room in _r and _unlock not in _r:
                _early.append(f"{_room} at '{_label}' without {_unlock}")
    if _early:
        fail(f"{len(_early)} Danger Room(s) in logic before their unlock level: "
             f"{_early[:4]}")
    else:
        ok(f"none of the {len(_roomsD)} rooms precedes its unlock level, "
           f"across {len(_ladder)} item sets")

    # ...and the gate is not a wall: with everything, every room is reachable.
    _allD = [i.name for i in _mwD.itempool if i.classification == IC.progression] + _preD
    _rall = {l.name for l in state_with(_mwD, _allD).reachable_locations()}
    _wall = sorted(r for r in _roomsD if r not in _rall)
    if _wall:
        fail(f"Danger Rooms unreachable with the full pool: {_wall[:4]}")
    else:
        ok(f"all {len(_roomsD)} rooms still reachable with the full pool")


# Side paths wait for the level that reveals them, same shape as the rooms above
# and for the same reason: a path used to hang off its world's OPENING, so every
# check in it was in logic the moment the world was. In Ancient Egypt, whose
# opening is ungated, that meant Squash's 4 and Appease-mint's 14 were sphere 1 --
# a real seed put the Lost City and Neon Mixtape Tour keys in Appease-mint, which
# in game sits behind Egypt 29.
#
# Asserted per LOCATION, not per region: the region could be connected correctly
# and still leak if something else reached inside it. Hot Date has no branch node
# of its own and chains off Sweet Potato, so it is held to Sweet Potato's level.
print("\n=== side paths wait for the level that reveals them ===")
from pvz2gardendless.constants import (
    SIDE_PATH_CHAIN as _CHAIN, SIDE_PATH_UNLOCK as _UNLOCK,
)
_mwS, _wS = build(include_side_paths=1, include_danger_rooms=1)
_preS = [i.name for i in _mwS.precollected]
_keysS = [i.name for i in _mwS.itempool if i.name.endswith(" Key")]

# Resolve each built path to the world level it ultimately waits on, following
# the chain, and to the locations that must not precede it.
_rootS = {}
for _sp in list(_UNLOCK) + list(_CHAIN):
    _cur = _sp
    while _cur in _CHAIN:
        _cur = _CHAIN[_cur]
    if _cur in _UNLOCK:
        _rootS[_sp] = _UNLOCK[_cur]
_locsS = {}
for _r in _mwS.regions:
    if _r.name in _rootS and _r.locations:
        _locsS[_r.name] = {l.name for l in _r.locations}
if not _locsS:
    fail("no side paths were built, so this proves nothing")
else:
    _ladderS = [("precollected only", _preS), ("+keys", _preS + _keysS)]
    _ladderS += [(f"+keys +{_p}", _preS + _keysS + [_p]) for _p in _SUND]
    _ladderS += [(f"+keys +{_n} plants", _preS + _keysS + PROG_PLANTS[:_n])
                 for _n in range(1, 14)]
    _ladderS.append(("+keys +all plants", _preS + _keysS + PROG_PLANTS))
    _rngS = _rndD.Random(1)
    _poolS = sorted({i.name for i in _mwS.itempool
                     if i.classification == IC.progression})
    _ladderS += [(f"random {_i}", _preS + _rngS.sample(_poolS, _rngS.randint(1, 20)))
                 for _i in range(60)]
    _earlyS = []
    for _label, _items in _ladderS:
        _rS = {l.name for l in state_with(_mwS, _items).reachable_locations()}
        for _sp, _unlock in sorted(_rootS.items()):
            if _sp not in _locsS or _unlock in _rS:
                continue
            _leak = _locsS[_sp] & _rS
            if _leak:
                _earlyS.append(f"{_sp} at '{_label}' without {_unlock} "
                               f"({len(_leak)} checks)")
    if _earlyS:
        fail(f"{len(_earlyS)} side path(s) in logic before their unlock level: "
             f"{_earlyS[:4]}")
    else:
        ok(f"none of the {len(_locsS)} paths precedes its unlock level, "
           f"across {len(_ladderS)} item sets")

    # Sphere 1 with side paths on is the number that regressed once: it was 27
    # with every world enabled, against 9 without them.
    #
    # Not one path may be in sphere 1. The closest is Squash, revealed by
    # egypt6 -- which is inside Egypt's opening stretch but past the egypt6
    # checkpoint, so it costs a sun producer and an attacker like the levels
    # around it.
    _s1 = {l.name for l in state_with(_mwS, _preS).reachable_locations()}
    _s1paths = sorted(_sp for _sp, _l in _locsS.items() if _l & _s1)
    if _s1paths:
        fail(f"side paths in sphere 1: {_s1paths}")
    else:
        ok(f"sphere 1 is {len(_s1)} locations and none of the "
           f"{sum(len(_l) for _l in _locsS.values())} side path checks is in it")

    _allS = [i.name for i in _mwS.itempool if i.classification == IC.progression] + _preS
    _rallS = {l.name for l in state_with(_mwS, _allS).reachable_locations()}
    _wallS = sorted(_sp for _sp, _l in _locsS.items() if not _l <= _rallS)
    if _wallS:
        fail(f"side paths unreachable with the full pool: {_wallS[:4]}")
    else:
        ok(f"all {len(_locsS)} paths still fully reachable with the full pool")


# Shop cards wait for the level that stocks them, same shape again. The Shop
# region only models the store BUTTON (egypt6), so all 39 checks used to be in
# logic from there while the game does not put shrinkingviolet on the shelf
# until Modern Day 14 or floawerPot until Aerial Fortress 31.
print("\n=== shop cards wait for the level that stocks them ===")
from pvz2gardendless.locations import SHOP_LOC_UNLOCK as _UNLOCKC
_mwC, _wC = build(shopsanity=1)
_preC = [i.name for i in _mwC.precollected]
_keysC = [i.name for i in _mwC.itempool if i.name.endswith(" Key")]
_placedC = {l.name for r in _mwC.regions for l in r.locations}
_cardsC = {c: u for c, u in _UNLOCKC.items() if c in _placedC}
if not _cardsC:
    fail("no gated shop cards were built, so this proves nothing")
else:
    _ladderC = [("precollected only", _preC), ("+keys", _preC + _keysC)]
    _ladderC += [(f"+keys +{_p}", _preC + _keysC + [_p]) for _p in _SUND]
    _ladderC += [(f"+keys +{_n} plants", _preC + _keysC + PROG_PLANTS[:_n])
                 for _n in range(1, 14)]
    _ladderC.append(("+keys +all plants", _preC + _keysC + PROG_PLANTS))
    _rngC = _rndD.Random(2)
    _poolC = sorted({i.name for i in _mwC.itempool
                     if i.classification == IC.progression})
    _ladderC += [(f"random {_i}", _preC + _rngC.sample(_poolC, _rngC.randint(1, 20)))
                 for _i in range(60)]
    _earlyC = []
    for _label, _items in _ladderC:
        _rC = {l.name for l in state_with(_mwC, _items).reachable_locations()}
        for _card, _unlock in sorted(_cardsC.items()):
            if _card in _rC and _unlock not in _rC:
                _earlyC.append(f"{_card} at '{_label}' without {_unlock}")
    if _earlyC:
        fail(f"{len(_earlyC)} shop card(s) on sale before their unlock level: "
             f"{_earlyC[:4]}")
    else:
        ok(f"none of the {len(_cardsC)} gated cards precedes its unlock level, "
           f"across {len(_ladderC)} item sets")

    _allC = [i.name for i in _mwC.itempool if i.classification == IC.progression] + _preC
    _rallC = {l.name for l in state_with(_mwC, _allC).reachable_locations()}
    _wallC = sorted(c for c in _cardsC if c not in _rallC)
    if _wallC:
        fail(f"shop cards unreachable with the full pool: {_wallC[:4]}")
    else:
        ok(f"all {len(_cardsC)} gated cards still reachable with the full pool")


report("all worlds, default")
report("all worlds + shuffle_zombies", shuffle_zombies=1)
report("all worlds + shopsanity", shopsanity=1)
report("3 worlds", world_count=3, worlds_required=11)
# Both sides of include_side_paths on the smallest seeds. With it off a
# one-world seed is 101 locations and create_item_pool trims useful plants to
# fit, so these also check that the trim leaves the logic reachable.
report("1 world (Egypt only)", world_count=1, worlds_required=11)
report("1 world + side paths", world_count=1, worlds_required=11,
       include_side_paths=1)
report("2 worlds, completion goal", world_count=2,
       goal_type=GoalType.option_completion,
       worlds_required=11, modern_day_victory=2, include_side_paths=1)
report("all worlds + side paths", include_side_paths=1)
report("12 worlds, completion goal", goal_type=GoalType.option_completion,
       worlds_required=11, modern_day_victory=2)

# ── what opens a world: its unlock, plus a plant for four of them ──────────
# The contract as of 2026-08-23. EVERY world but Ancient Egypt wants its first
# Progressive <World> AND a sun producer; five of them want a specific plant on
# top of that. Nothing opens with any one of those missing.
#
# The sun requirement is what makes a sun producer structurally guaranteed:
# sphere 1 is the tutorial plus egypt1-5, and every way out of it now runs
# through one -- Egypt's egypt6 checkpoint, and every other world's entrance --
# so fill has to place one there or the seed never opens.
#
# Checked in every direction rather than only the positive one: asserting just
# "unlock + sun + plants opens it" would pass with any of the three rules
# deleted, since dropping a requirement only makes the world easier to open.
print("\n=== world entry ===")
mw, w = build()
_pre_only = [i.name for i in mw.precollected]
_SUN1 = C.SUN_PRODUCER_PLANTS[0]


def _entry_plants(world_name):
    """One plant from each of this world's requirement lists, or [] for a world
    that asks for none. First member rather than a random one: build() is the
    default seed, so every plant is in the pool and the choice is arbitrary."""
    return [g[0] for g in C.slot_entry_groups(w, world_name)]


def _open(world_name, items):
    return any(r.name == world_name
               for r in state_with(mw, _pre_only + list(items))._reachable)


_shut, _open_early, _no_unlock, _no_sun, _no_plant = [], [], [], [], []
for world_name in sorted(w.enabled_worlds):
    if world_name == "Ancient Egypt":
        continue  # no entrance to rule on: it is where a run starts
    unlock = C.progressive_item_name(world_name)
    plants = _entry_plants(world_name)
    full = [unlock, _SUN1] + plants
    if not _open(world_name, full):
        _shut.append(world_name)
    if _open(world_name, []):
        _open_early.append(world_name)
    # Drop each requirement in turn; the world must stay shut every time.
    if _open(world_name, [_SUN1] + plants):
        _no_unlock.append(world_name)
    if _open(world_name, [unlock] + plants):
        _no_sun.append(world_name)
    if plants and _open(world_name, [unlock, _SUN1]):
        _no_plant.append(world_name)

if _shut:
    fail(f"{len(_shut)} world(s) do not open on unlock + sun + entry plants: {_shut[:4]}")
elif _open_early:
    fail(f"{len(_open_early)} world(s) are open with nothing held: {_open_early[:4]}")
elif _no_unlock:
    fail(f"{len(_no_unlock)} world(s) open with no unlock held: {_no_unlock[:4]}")
elif _no_sun:
    fail(f"{len(_no_sun)} world(s) open with no sun producer: {_no_sun[:4]}")
elif _no_plant:
    fail(f"{len(_no_plant)} world(s) open without their entry plant: {_no_plant[:4]}")
else:
    _gated = sorted(set(C.WORLD_ENTRY_PLANTS) & w.enabled_worlds)
    ok(f"all {len(w.enabled_worlds) - 1} keyed worlds want their unlock AND a sun "
       f"producer, {len(_gated)} of them an entry plant too, and drop any one "
       f"and the world stays shut")

# The table has to actually gate something, or the split above is vacuous.
if not set(C.WORLD_ENTRY_PLANTS) & w.enabled_worlds:
    fail("no enabled world names an entry plant, so the world-entry test is empty")
else:
    ok(f"{len(C.WORLD_ENTRY_PLANTS)} worlds name an entry plant")

# ...and the locations inside really are reachable, not just the region. This is
# the shape of the complaint that prompted the 2026-08-23 simplification: the
# tracker showed dino1-16 shut while the player held Progressive Jurassic Marsh.
# It wants Perfume-shroom and a sun producer alongside it now, deliberately.
_dino_open = {l.name for l in
              state_with(mw, _pre_only + ["Progressive Jurassic Marsh",
                                          "Perfume-shroom", _SUN1]).reachable_locations()}
_dino_want = ["dino1", "dino8", "dino16"]
_dino_missing = [n for n in _dino_want if n not in _dino_open]
if _dino_missing:
    fail(f"Progressive Jurassic Marsh + Perfume-shroom + sun does not open {_dino_missing}")
elif "dino17" in _dino_open:
    fail("dino17 opened on one unlock; it is the middle stretch")
else:
    ok("one Progressive Jurassic Marsh + Perfume-shroom + a sun producer opens "
       "dino1-16 and stops there")

# Each gated world named individually, with the plant that opens it pinned as a
# literal rather than read back out of WORLD_ENTRY_PLANTS -- a test derived from
# the table under test would pass whatever the table said. Pirate Seas is the
# control: it names no entry plant, so its unlock plus a sun producer is enough.
_named = []
for _wn, _plant, _wants in (("Big Wave Beach",  "Lily Pad",       True),
                            ("Far Future",      "Blover",         True),
                            ("Jurassic Marsh",  "Perfume-shroom", True),
                            # Whatever this slot drew of the 36 that can hurt
                            # the Jester. Read from the slot, not pinned: the
                            # draw is the feature. The literal checks are the
                            # two below the loop.
                            ("Dark Ages",  sorted(w.logic_jesters)[0], True),
                            ("Frostbite Caves", "Torchwood",      True),
                            ("Pirate Seas",     "Peashooter",     False)):
    if _wn not in w.enabled_worlds:
        continue
    _unlock = C.progressive_item_name(_wn)
    _bare = _open(_wn, [_unlock, _SUN1])
    _with = _open(_wn, [_unlock, _SUN1, _plant])
    if _wants and _bare:
        _named.append(f"{_wn} opens without {_plant}")
    elif _wants and not _with:
        _named.append(f"{_wn} does not open with {_plant}")
    elif not _wants and not _bare:
        _named.append(f"{_wn} wants a plant it should not")
# Sap-fling was a Jester counter until 2026-08-25 and must not be one again: its
# projectile really is unreversible, but it deals no damage, so it declines to
# arm the Jester rather than answering him. Asserted as its own case because the
# positive checks above would all still pass with it back in the group.
if "Dark Ages" in w.enabled_worlds:
    _da = C.progressive_item_name("Dark Ages")
    if _open("Dark Ages", [_da, _SUN1, "Sap-fling"]):
        _named.append("Dark Ages opens on Sap-fling, which deals no damage")

    # EXACTLY ONE of the 36 is named. The whole point of the draw is that the
    # other 35 are ordinary useful plants, so holding one must NOT open the
    # world -- if it did, the group would be back to being free.
    assert len(w.logic_jesters) == 1, sorted(w.logic_jesters)
    _undrawn = sorted(set(C.JESTER_COUNTER_PLANTS) - set(w.logic_jesters))
    assert len(_undrawn) == 35, len(_undrawn)
    _wrongly_open = [p for p in _undrawn if _open("Dark Ages", [_da, _SUN1, p])]
    if _wrongly_open:
        _named.append(f"Dark Ages opens on {len(_wrongly_open)} counters it did "
                      f"not draw, e.g. {_wrongly_open[:3]}")

    # ...and Magnifying Grass, dropped 2026-08-25: its only projectile is not
    # flagged, so the Jester catches it.
    if _open("Dark Ages", [_da, _SUN1, "Magnifying Grass"]):
        _named.append("Dark Ages opens on Magnifying Grass, whose shot he catches")

if _named:
    fail(f"world entry plants wrong: {_named}")
else:
    ok("Lily Pad, Blover, Perfume-shroom, a Jester answer and a warming plant "
       "each open their world on top of unlock+sun, and Pirate Seas needs none")

# shuffle_zombies must not move a single location between spheres. It is a
# client-side swap confined to tiers that keep every threat mechanic in the
# world it started in, so no access rule can change -- and the sphere shape is
# a design target (sphere 1 is deliberately ~7% of locations), so a silent
# shift here is the failure mode worth catching.
def sphere_shape(**kw):
    mw, w = build(**kw)
    pre = [i.name for i in mw.precollected]
    out = []
    for extra in ([], ["Sunflower"], [C.progressive_item_name(n) for n in
                       ("Pirate Seas", "Wild West", "Dark Ages")]):
        st = state_with(mw, pre + extra)
        out.append(sorted(l.name for l in st.reachable_locations()))
    return out


_off, _on = sphere_shape(shuffle_zombies=0), sphere_shape(shuffle_zombies=1)
if _off != _on:
    _diff = next(sorted(set(a) ^ set(b)) for a, b in zip(_off, _on) if a != b)
    fail(f"shuffle_zombies moved {len(_diff)} locations between spheres: {_diff[:5]}")
else:
    ok(f"shuffle_zombies leaves every sphere identical "
       f"({', '.join(str(len(s)) for s in _off)} locations at 3 depths)")

# ── Egypt's opening is egypt1-8, and egypt9 is behind the first unlock ──────
# Ancient Egypt's opening runs to its World Key level, egypt8, and is playable
# with nothing but the free starting plant -- it is what sphere 1 is made of,
# and gating it would leave a seed with nowhere to begin. egypt9 starts the
# next stretch, which wants BOTH a Progressive Ancient Egypt and the world's
# sun-producer-and-attacker rule.
#
# World locations are named for their level id, so these are just the level
# codes. They used to be spelled out as reward names ('Map Unlock',
# 'Cabbagepult Unlock' ...) with the codes in a trailing comment.
_PROG_EGYPT = 'Progressive Ancient Egypt'
from pvz2gardendless.constants import SUN_PRODUCER_PLANTS

_mw, _w = build()
_pre = [i.name for i in _mw.precollected]
# Egypt's gated stretches want the sun rule and, past egypt8, an unlock. The
# plant counts they used to stack on top went with every other plant
# requirement on 2026-08-23, so these lists exist only to keep the "no sun"
# probes honest -- non-sun on purpose, since drawing from the front of
# PROG_PLANTS would sometimes hand over a sun producer and make those states
# pass for the wrong reason.
_nosun_plants = [p for p in PROG_PLANTS
                 if p not in SUN_PRODUCER_PLANTS and p not in C.GRAVE_CLEAR_PLANTS]
_p3, _p6 = _nosun_plants[:3], _nosun_plants[:6]
# Ancient Egypt and Dark Ages want Grave Buster for everything past their World
# Key level -- " Mid" is key -> Zomboss and " Late" is Zomboss -> final level.
# Held here as its own name so the probes below can add or withhold it
# deliberately; _nosun_plants excludes it so the "no grave" states stay honest.
_GRAVE = C.GRAVE_CLEAR_PLANTS[0]
_open_egypt = ['egypt1', 'egypt2', 'egypt3', 'egypt4', 'egypt5']
# Behind the egypt6 checkpoint: a sun producer and an attacker, no unlock.
_sun_egypt = ['egypt6', 'egypt7', 'egypt8']
# Behind the first progressive unlock as well.
_gated_egypt = ['egypt9', 'egypt10', 'egypt25']

_no_sun = {l.name for l in state_with(_mw, _pre).reachable_locations()}
_with_sun = {l.name for l in
             state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT, _GRAVE] + _p3
                        ).reachable_locations()}

_missing = [n for n in _open_egypt if n not in _no_sun]
if _missing:
    fail(f"egypt1-5 need more than the starting plant: {_missing}")
else:
    ok('egypt1-5 are playable with only the free starting plant')

# THE sun expectation: "by Egypt level 6 you should have a sun producer". It is
# what makes a sun producer findable at the start of every run rather than
# merely likely, so it is checked from both sides.
_sun_leak = [n for n in _sun_egypt if n in _no_sun]
_sun_shut = [n for n in _sun_egypt
             if n not in {l.name for l in
                          state_with(_mw, _pre + ['Sunflower']).reachable_locations()}]
if _sun_leak:
    fail(f"reachable with no sun producer, so the gate does not start at egypt6: {_sun_leak}")
elif _sun_shut:
    fail(f"a sun producer alone does not open egypt6-8: {_sun_shut} -- those are "
         "still the opening and must not want an unlock")
else:
    ok(f'all {len(_sun_egypt)} of egypt6-8 need a sun producer, and want nothing else')

_leaked = [n for n in _gated_egypt if n in _no_sun]
if _leaked:
    fail(f"reachable with nothing, so the gate does not start at egypt9: {_leaked}")
else:
    ok(f'all {len(_gated_egypt)} of egypt9+ are gated')

# The unlock alone is not enough, and neither is the sun producer alone. Both
# halves are checked because either one going missing leaves a gate that still
# looks gated from the outside.
# Grave Buster is in BOTH of these: the point of each is that ONE of the unlock
# and the sun producer is missing. Leaving the grave plant out as well would let
# them pass because of the new rule instead of the one under test.
_only_prog = {l.name for l in
              state_with(_mw, _pre + [_PROG_EGYPT, _GRAVE] + _p3).reachable_locations()}
_only_sun = {l.name for l in
             state_with(_mw, _pre + ['Sunflower', _GRAVE] + _p3).reachable_locations()}
if any(n in _only_prog for n in _gated_egypt):
    fail('the unlock alone opened egypt9+, so the sun rule is gone')
elif any(n in _only_sun for n in _gated_egypt):
    fail('a sun producer alone opened egypt9+, so the unlock is not required')
elif not all(n in _only_sun for n in _sun_egypt):
    fail('a sun producer alone should still open egypt6-8, which need no unlock')
else:
    ok('egypt9+ needs the unlock AND a sun producer, not either on its own')

_still = [n for n in _gated_egypt if n not in _with_sun]
if _still:
    fail(f"unlock + sun producer does not open egypt9+: {_still}")
else:
    ok('one Progressive Ancient Egypt plus a sun producer opens egypt9-25')

# The second unlock, and only the second, opens the last stretch.
_late = 'egypt26'
_one = {l.name for l in
        state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT, _GRAVE] + _p6
                   ).reachable_locations()}
_two = {l.name for l in
        state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT, _PROG_EGYPT, _GRAVE] + _p6
                   ).reachable_locations()}
if _late in _one:
    fail(f'{_late} opened on one unlock; it is the third stretch')
elif _late not in _two:
    fail(f'{_late} did not open on two unlocks')
else:
    ok('egypt26-35 needs the second Progressive Ancient Egypt')

# Every sun producer must work, not just Sunflower -- the gate is has_any() and
# a seed may only ever offer one of the five.
for _p in SUN_PRODUCER_PLANTS:
    _r = {l.name for l in
          state_with(_mw, _pre + [_p, _PROG_EGYPT, _GRAVE] + _p3).reachable_locations()}
    if any(n not in _r for n in _gated_egypt):
        fail(f'{_p} does not satisfy the Egypt sun gate')
        break
else:
    ok(f'all {len(SUN_PRODUCER_PLANTS)} sun producers satisfy the gate')

# ── the shop opens with egypt6, not at the start ────────────────────────────
# index.js only sets feature_store once egypt6 is cleared (the same chain gives
# coins at tutorial4 and the zen garden at egypt5), so the store button does not
# exist in sphere 1 and its checks cannot be there either. regions.py hangs Shop
# off "Ancient Egypt Early", the stretch that starts at egypt6, to say exactly
# that -- and that stretch wants a sun producer, so the cards do too.
#
# Built with shopsanity on, since with it off the region holds no locations and
# the probe would pass vacuously -- the same trap the early_world_keys probe hit.
_mws, _ws = build(shopsanity=1)
_pres = [i.name for i in _mws.precollected]
_shop_locs = [l.name for l in _ws.active_locations() if l.is_shop]
if not _shop_locs:
    fail("shopsanity built no shop locations, so this proves nothing")
else:
    _start = {l.name for l in state_with(_mws, _pres).reachable_locations()}
    _leak = [n for n in _shop_locs if n in _start]
    if _leak:
        fail(f"{len(_leak)} shop checks are in sphere 1, but the store opens at egypt6: {_leak[:3]}")
    else:
        ok(f"all {len(_shop_locs)} shop checks are behind the egypt6 gate")

    # A sun producer opens the store BUTTON, which is all the Shop region
    # models. It puts exactly the ten cards with no UnlockLevel on sale; the
    # other 29 wait for their own level, so a rule that expected all 39 here
    # would be asserting the bug this gating removed.
    from pvz2gardendless.locations import SHOP_LOC_UNLOCK as _SHOPU
    _open = {l.name for l in state_with(_mws, _pres + ["Sunflower"]).reachable_locations()}
    _ungated = [n for n in _shop_locs if n not in _SHOPU]
    _shut = [n for n in _ungated if n not in _open]
    # A gated card may legitimately be open here if its own level already is --
    # iceweed unlocks at egypt9, which is in the very region the Shop hangs
    # off. What must never happen is a card opening ahead of its level.
    _early = [n for n in _shop_locs
              if n in _SHOPU and n in _open and _SHOPU[n] not in _open]
    if _shut:
        fail(f"a sun producer does not open the ungated cards: {_shut[:3]}")
    elif _early:
        fail(f"cards on sale before their unlock level: {_early[:3]}")
    else:
        _still = [n for n in _shop_locs if n in _SHOPU and n not in _open]
        ok(f"a sun producer opens the {len(_ungated)} cards with no UnlockLevel; "
           f"{len(_still)} of the {len(_shop_locs) - len(_ungated)} gated ones "
           f"stay shut behind their own level")

# WHAT LEAVES SPHERE 1. Two kinds of item and no others: a sun producer, which
# opens egypt6-8, or a world's first unlock, which opens that world's opening
# stretch. Everything else in the pool -- every other plant, every upgrade,
# every filler and trap, and the second and third copies of an unlock -- opens
# nothing on its own.
#
# THE SUN PRODUCER IS GUARANTEED AGAIN, structurally, as of 2026-08-23. Every
# world but Ancient Egypt asks for one on its entrance, and Egypt asks at its
# egypt6 checkpoint -- so EVERY way out of sphere 1 runs through a sun producer
# and fill has to place one there or the seed never opens.
#
# That makes the claim below as strong as it can be: a sun producer is the ONLY
# kind of item that opens anything from sphere 1. A world unlock now opens
# nothing on its own, and neither does an entry plant, because each needs the
# others alongside it.
_by_kind = {}
for _n in sorted({i.name for i in _mw.itempool}):
    _opens = len(state_with(_mw, _pre + [_n]).reachable_locations()) > len(_no_sun)
    if not _opens:
        continue
    _by_kind[_n] = ("sun producer" if _n in SUN_PRODUCER_PLANTS else
                    "world unlock" if _n in {C.progressive_item_name(_w)
                                             for _w in C.WORLD_REGIONS} else
                    "SOMETHING ELSE")
_unexpected = sorted(n for n, k in _by_kind.items() if k == "SOMETHING ELSE")
if _unexpected:
    fail(f'{len(_unexpected)} item(s) that are neither a sun producer nor a world '
         f'unlock open locations on their own: {_unexpected[:6]}')
else:
    _suns = sum(1 for k in _by_kind.values() if k == "sun producer")
    _unlocks = sum(1 for k in _by_kind.values() if k == "world unlock")
    ok(f'only sun producers ({_suns}) and world unlocks ({_unlocks}) open anything '
       f'from sphere 1')

# ...and NO unlock opens anything on its own any more, because every world wants
# a sun producer alongside it. Stated separately from the count above: that one
# is an upper bound and would still pass if some unlocks slipped through.
_alone = {_n for _n, _k in _by_kind.items() if _k == "world unlock"}
if _alone:
    fail(f'{len(_alone)} world unlock(s) open something with no sun producer '
         f'held: {sorted(_alone)[:4]}')
else:
    ok('no world unlock opens anything on its own; every world wants a sun '
       'producer too')

# THE STRUCTURAL GUARANTEE, stated in one state rather than one item at a time:
# hold EVERYTHING in the pool except the sun producers and nothing beyond sphere
# 1 is reachable. That is what forces fill to put a sun producer in sphere 1,
# and it is the claim that was lost between 2026-08-23 and today.
_all_but_sun = [i.name for i in _mw.itempool if i.name not in set(SUN_PRODUCER_PLANTS)]
_reach_no_sun = state_with(_mw, _pre + _all_but_sun).reachable_locations()
if len(_reach_no_sun) > len(_no_sun):
    _leak = sorted({l.name for l in _reach_no_sun} - {l.name for l in _no_sun})
    fail(f'{len(_leak)} location(s) are reachable holding the whole pool minus '
         f'the sun producers, so a sun producer is not guaranteed: {_leak[:5]}')
else:
    ok(f'the entire pool minus its {len(SUN_PRODUCER_PLANTS)} sun producers '
       f'opens nothing past sphere 1, so fill must place one there')

# ...and each sun producer really does open egypt6-8 on its own, or that gate
# is a wall for a seed that offers only one of the five.
_stuck = [p for p in SUN_PRODUCER_PLANTS
          if len(state_with(_mw, _pre + [p]).reachable_locations()) <= len(_no_sun)]
if _stuck:
    fail(f'sun producers that open nothing: {_stuck}')
else:
    ok(f'each of the {len(SUN_PRODUCER_PLANTS)} sun producers opens egypt6-8 on its own')

# ...and every sun producer is in the pool, or the egypt6 gate is unopenable.
_pool_names = {i.name for i in _mw.itempool}
_absent = sorted(set(SUN_PRODUCER_PLANTS) - _pool_names)
if _absent:
    fail(f'sun producers missing from the pool: {_absent}')
else:
    ok('every sun producer is in the pool')

print()


# ── Grave Buster gates the back half of two worlds ───────────────────────────
#
# Ancient Egypt and Dark Ages want it for everything past their World Key level.
# Both worlds are cut on their own milestones, so " Mid" is exactly
# key -> Zomboss and " Late" is Zomboss -> final level.
#
# Checked in BOTH directions. Asserting only that holding it opens the stretch
# would pass with the rule deleted, since dropping a requirement only makes a
# region easier to reach.
_grave_cases = [
    ("Ancient Egypt", ['egypt9', 'egypt25'], ['egypt26', 'egypt35'],
     ['egypt1', 'egypt8'], ['Sunflower', _PROG_EGYPT, _PROG_EGYPT]),
    ("Dark Ages", ['dark11', 'dark20'], ['dark21', 'dark30'],
     ['dark1', 'dark10'], ['Sunflower', C.progressive_item_name("Dark Ages"),
                           C.progressive_item_name("Dark Ages"),
                           C.progressive_item_name("Dark Ages"),
                           sorted(w.logic_jesters)[0]]),
]
_grave_bad = []
for _wn, _mid, _late, _early, _base in _grave_cases:
    if _wn not in w.enabled_worlds:
        continue
    _without = {l.name for l in
                state_with(_mw, _pre + _base + _p6).reachable_locations()}
    _withg = {l.name for l in
              state_with(_mw, _pre + _base + [_GRAVE] + _p6).reachable_locations()}
    # The opening is NOT gated on it: this is the back half only.
    for _n in _early:
        if _n not in _without:
            _grave_bad.append(f"{_wn}: {_n} is in the opening but wants {_GRAVE}")
    # Mid and Late are shut without it...
    for _n in _mid + _late:
        if _n in _without:
            _grave_bad.append(f"{_wn}: {_n} opened without {_GRAVE}")
    # ...and open with it.
    for _n in _mid + _late:
        if _n not in _withg:
            _grave_bad.append(f"{_wn}: {_n} stayed shut with {_GRAVE} held")
if _grave_bad:
    fail(f"Grave Buster gating wrong: {_grave_bad[:4]}")
else:
    ok(f'{_GRAVE} gates Mid and Late of Ancient Egypt and Dark Ages, '
       f'and neither opening')

# No OTHER world picked the rule up. Far Future's middle must not want it.
_ff = C.progressive_item_name("Far Future")
if "Far Future" in w.enabled_worlds:
    _ff_open = {l.name for l in
                state_with(_mw, _pre + ['Sunflower', _ff, _ff, 'Blover'] + _p6
                           ).reachable_locations()}
    if 'future9' not in _ff_open:
        fail('Far Future Mid wants Grave Buster; only two worlds should')
    else:
        ok('no other world gained the requirement')
print(f"progression plants available: {len(PROG_PLANTS)}")
print("\n" + (f"{failed} FAILURE(S)" if failed else "SPHERE LOGIC OK"))
sys.exit(1 if failed else 0)
