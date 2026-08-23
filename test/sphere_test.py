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

PROG_PLANTS = [p.name for p in PLANT_ITEMS if p.classification == IC.progression]

failed = 0


def fail(m):
    global failed
    failed += 1
    print("  FAIL  " + m)


def ok(m):
    print("  ok    " + m)


def build(**kw):
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
    # Exactly ONE path may be in sphere 1 now, and only because the game puts
    # it there: Squash is revealed by egypt6, and since 2026-08-23 Ancient
    # Egypt's opening runs to egypt8. Every other path hangs off a level behind
    # a world key or a progressive unlock. Naming it rather than counting means
    # a second path appearing here still fails.
    _S1_ALLOWED = {"Squash Sidepath"}
    _s1 = {l.name for l in state_with(_mwS, _preS).reachable_locations()}
    _s1paths = sorted(_sp for _sp, _l in _locsS.items() if _l & _s1)
    if set(_s1paths) - _S1_ALLOWED:
        fail(f"side paths in sphere 1: {sorted(set(_s1paths) - _S1_ALLOWED)}")
    elif _S1_ALLOWED - set(_s1paths):
        fail(f"expected in sphere 1 but gated: {sorted(_S1_ALLOWED - set(_s1paths))} "
             "-- if Egypt's opening moved, this is the test to re-derive")
    else:
        ok(f"sphere 1 is {len(_s1)} locations; of the "
           f"{sum(len(_l) for _l in _locsS.values())} side path checks only "
           f"{sorted(_S1_ALLOWED)} is in it, which is where the game puts it")

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
report("2 worlds, completion goal", world_count=2, goal_type=1,
       worlds_required=11, modern_day_victory=2, include_side_paths=1)
report("all worlds + side paths", include_side_paths=1)
report("12 worlds, completion goal", goal_type=1, worlds_required=11, modern_day_victory=2)

# ── per-world entry requirements ────────────────────────────────────────────
from pvz2gardendless.constants import WORLD_ENTRY_PLANTS, SUN_PRODUCER_PLANTS, JESTER_COUNTER_PLANTS

print("\n=== world entry requirements ===")
mw, w = build()
# WORLD_ENTRY_PLANTS holds only a world's OWN extra asks. Every world also
# needs a sun producer now (rules.py), which is not listed there, so it is
# carried in the baseline here -- these cases are about the per-world plants.
for world_name, groups in WORLD_ENTRY_PLANTS.items():
    key = f"{world_name} Key"
    base = [i.name for i in mw.precollected] + [key, "Sunflower"]

    def opens(extra):
        st = state_with(mw, base + extra)
        return any(r.name == world_name for r in st._reachable)

    if opens([]):
        fail(f"{world_name} opens on its key alone, ignoring its plant requirements")
    else:
        ok(f"{world_name}: key + sun is not enough ({len(groups)} more requirement(s))")

    # each requirement must be independently necessary
    for i, g in enumerate(groups):
        others = [grp[0] for j, grp in enumerate(groups) if j != i]
        if opens(others):
            fail(f"{world_name}: requirement {i + 1} ({g[0]}...) is not enforced")
    one_from_each = [g[0] for g in groups]
    if not opens(one_from_each):
        fail(f"{world_name}: one plant from each requirement still does not open it")
    else:
        ok(f"{world_name}: opens with one plant from each requirement")

    # ...and the universal sun requirement must bite here too: drop it and the
    # world must close again, however many of its own plants are held.
    st_nosun = state_with(mw, [i.name for i in mw.precollected] + [key] + one_from_each)
    if any(r.name == world_name for r in st_nosun._reachable):
        fail(f"{world_name} opens with no sun producer")
    else:
        ok(f"{world_name}: still closed without a sun producer")

# Dark Ages spelled out, since it is the first world to carry two asks
mw, w = build()
base = [i.name for i in mw.precollected] + ["Dark Ages Key"]
cases = [
    ("key only", []),
    ("key + sun producer", ["Sunflower"]),
    ("key + Jester counter", ["Sap-fling"]),
    ("key + both", ["Sunflower", "Sap-fling"]),
    # The Jester returns lobbed shots like anything else, so a pult is not a
    # counter and sun + a pult must NOT open the world.
    ("key + sun + Cabbage-pult", ["Sunflower", "Cabbage-pult"]),
    ("key + sun + Melon-Pult", ["Sunflower", "Melon-Pult"]),
    ("key + sun + Winter Melon", ["Sunflower", "Winter Melon"]),
]
print()
for label, extra in cases:
    st = state_with(mw, base + extra)
    got = any(r.name == "Dark Ages" for r in st._reachable)
    want = label in ("key + both",)
    mark = "ok   " if got == want else "FAIL "
    if got != want:
        failed += 1
    print(f"  {mark} Dark Ages, {label:<22} reachable={got}  (expected {want})")

# Frostbite Caves wants a standing heat source, not just any fire plant.
from pvz2gardendless.constants import FIRE_AURA_PLANTS
mw, w = build()
fbase = [i.name for i in mw.precollected] + ["Frostbite Caves Key", "Sunflower"]
print()
for label, extra, want in [
    ("key only", [], False),
    ("key + Hot Potato", ["Hot Potato"], False),
    ("key + Pepper-pult", ["Pepper-pult"], False),
    ("key + Torchwood", ["Torchwood"], True),
    ("key + Jack O' Lantern", ["Jack O' Lantern"], True),
]:
    st = state_with(mw, fbase + extra)
    got = any(r.name == "Frostbite Caves" for r in st._reachable)
    mark = "ok   " if got == want else "FAIL "
    if got != want:
        failed += 1
    print(f"  {mark} Frostbite Caves, {label:<24} reachable={got}  (expected {want})")

# shuffle_zombies must not move a single location between spheres. It is a
# client-side swap confined to tiers that keep every threat mechanic in the
# world it started in, so no access rule can change -- and the sphere shape is
# a design target (sphere 1 is deliberately ~7% of locations), so a silent
# shift here is the failure mode worth catching.
def sphere_shape(**kw):
    mw, w = build(**kw)
    pre = [i.name for i in mw.precollected]
    out = []
    for extra in ([], ["Sunflower"], [f"{n} Key" for n in
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
_mw, _w = build()
_pre = [i.name for i in _mw.precollected]
# Egypt's stretches stack a plant count on the unlock and the sun rule, so a
# probe that means to test one of the three has to satisfy the other two.
# Non-sun on purpose: drawing these from the front of PROG_PLANTS would
# sometimes hand over a sun producer and make the "no sun" states pass for the
# wrong reason.
_nosun_plants = [p for p in PROG_PLANTS if p not in SUN_PRODUCER_PLANTS]
_p3, _p6 = _nosun_plants[:3], _nosun_plants[:6]
_open_egypt = ['egypt1', 'egypt5', 'egypt6', 'egypt7', 'egypt8']
_gated_egypt = ['egypt9', 'egypt10', 'egypt25']

_no_sun = {l.name for l in state_with(_mw, _pre).reachable_locations()}
_with_sun = {l.name for l in
             state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT] + _p3).reachable_locations()}

_missing = [n for n in _open_egypt if n not in _no_sun]
if _missing:
    fail(f"egypt1-8 need more than the starting plant: {_missing}")
else:
    ok('egypt1-8 are playable with only the free starting plant')

_leaked = [n for n in _gated_egypt if n in _no_sun]
if _leaked:
    fail(f"reachable with nothing, so the gate does not start at egypt9: {_leaked}")
else:
    ok(f'all {len(_gated_egypt)} of egypt9+ are gated')

# The unlock alone is not enough, and neither is the sun producer alone. Both
# halves are checked because either one going missing leaves a gate that still
# looks gated from the outside.
_only_prog = {l.name for l in
              state_with(_mw, _pre + [_PROG_EGYPT] + _p3).reachable_locations()}
_only_sun = {l.name for l in
             state_with(_mw, _pre + ['Sunflower'] + _p3).reachable_locations()}
if any(n in _only_prog for n in _gated_egypt):
    fail('the unlock alone opened egypt9+, so the sun rule is gone')
elif any(n in _only_sun for n in _gated_egypt):
    fail('a sun producer alone opened egypt9+, so the unlock is not required')
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
        state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT] + _p6).reachable_locations()}
_two = {l.name for l in
        state_with(_mw, _pre + ['Sunflower', _PROG_EGYPT, _PROG_EGYPT] + _p6
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
          state_with(_mw, _pre + [_p, _PROG_EGYPT] + _p3).reachable_locations()}
    if any(n not in _r for n in _gated_egypt):
        fail(f'{_p} does not satisfy the Egypt sun gate')
        break
else:
    ok(f'all {len(SUN_PRODUCER_PLANTS)} sun producers satisfy the gate')

# ── the shop follows the game's own store unlock ────────────────────────────
# index.js sets feature_store once egypt6 is cleared (the same chain gives coins
# at tutorial4 and the zen garden at egypt5). egypt6 is inside Ancient Egypt's
# opening as of 2026-08-23, so the store button really does exist in sphere 1
# and regions.py hangs Shop off the opening to say exactly that.
#
# What must NOT be in sphere 1 is a card gated on a level that is not: the five
# cards with no UnlockLevel are on the shelf from the moment the button is, and
# the other 29 wait for their own level. Between egypt6 and egypt8 no gated card
# unlocks, so the sphere-1 set is exactly the ungated five.
#
# Built with shopsanity on, since with it off the region holds no locations and
# the probe would pass vacuously -- the same trap the early_world_keys probe hit.
_mws, _ws = build(shopsanity=1)
_pres = [i.name for i in _mws.precollected]
_shop_locs = [l.name for l in _ws.active_locations() if l.is_shop]
_ungated = [n for n in _shop_locs
            if C.SHOP_UNLOCK.get(n.split(': ', 1)[-1]) is None]
if not _shop_locs:
    fail("shopsanity built no shop locations, so this proves nothing")
elif not _ungated:
    fail("no ungated shop cards, so the split below proves nothing")
else:
    _start = {l.name for l in state_with(_mws, _pres).reachable_locations()}
    _leak = sorted(set(n for n in _shop_locs if n in _start) - set(_ungated))
    _absent = sorted(set(_ungated) - _start)
    if _leak:
        fail(f"{len(_leak)} shop cards are in sphere 1 but are gated on a "
             f"level that is not: {_leak[:3]}")
    elif _absent:
        fail(f"{len(_absent)} ungated shop cards are NOT in sphere 1, but the "
             f"store button is: {_absent[:3]}")
    else:
        ok(f"of {len(_shop_locs)} shop checks exactly the {len(_ungated)} "
           "ungated ones are in sphere 1, the rest behind their own level")

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

# THE structural guarantee, and the reason no early_items nudge is needed: a
# sun producer is NECESSARY to leave sphere 1. Every world's entrance wants one
# on top of its key, and Ancient Egypt's stretches want one on top of their
# unlock, so fill has to place a sun producer in sphere 1 or the seed never
# opens.
#
# Stated as necessity rather than "a sun producer opens it on its own", which
# stopped being true on 2026-08-23: with the stretch unlocks, leaving sphere 1
# takes at least two items (a sun producer AND either a world key or a
# Progressive Ancient Egypt). Collecting EVERYTHING ELSE is the direct test of
# necessity and costs one state instead of one per item.
_everything_else = [n for n in
                    ([i.name for i in _mw.itempool] + _pre)
                    if n not in SUN_PRODUCER_PLANTS]
_no_sun_ever = {l.name for l in state_with(_mw, _everything_else).reachable_locations()}
_escapes = sorted(_no_sun_ever - _no_sun)
if _escapes:
    fail(f'{len(_escapes)} location(s) open with every item in the seed EXCEPT a '
         f'sun producer, so fill is not forced to place one early: {_escapes[:6]}')
else:
    ok('nothing at all opens without a sun producer, whatever else is held, so '
       'fill must place one in sphere 1')

# ...and no single item opens anything either, which is what makes the above a
# two-item threshold rather than a wall: check that some pair does open it.
_singles = sorted(
    n for n in {i.name for i in _mw.itempool}
    if len(state_with(_mw, _pre + [n]).reachable_locations()) > len(_no_sun)
)
if _singles:
    fail(f'{len(_singles)} item(s) open locations on their own, so a stretch '
         f'unlock or a key is not being asked for: {_singles[:6]}')
else:
    ok('no single item opens anything: leaving sphere 1 takes a sun producer '
       'plus an unlock')

# ...and each sun producer really does work as that half of the pair, or the
# gate is a wall for a seed that only offers one of the five.
_stuck = [p for p in SUN_PRODUCER_PLANTS
          if len(state_with(_mw, _pre + [p, _PROG_EGYPT] + _p3).reachable_locations())
          <= len(_no_sun)]
if _stuck:
    fail(f'sun producers that open nothing even with the unlock: {_stuck}')
else:
    ok(f'each of the {len(SUN_PRODUCER_PLANTS)} sun producers opens sphere 1 '
       'when paired with the first Ancient Egypt unlock')

# ── the win condition is a COUNT of completed worlds ────────────────────────
# Victory hangs off Tutorial, which is sphere 1, so nothing but its own access
# rule keeps it out of reach. "Nothing -> everything" would prove none of that:
# both ends agree with a rule that ignores the count entirely. So this walks
# the world keys in one at a time and checks Victory flips exactly where the
# number of reachable goal locations crosses worlds_required, at every step.
for _gt, _gtname in ((2, "world_key"), (1, "completion"), (0, "zomboss")):
    _mwv, _wv = build(goal_type=_gt, worlds_required=4)
    _sdv = _wv.fill_slot_data()
    _req = _sdv["worlds_required"]
    _goals = _sdv["goal_locations"]
    _base = [i.name for i in _mwv.precollected] + PROG_PLANTS
    _keys = sorted(i.name for i in _mwv.itempool if i.name.endswith(" Key"))
    # Both stretch unlocks for every world come along from the start: a world's
    # Zomboss and its final level sit behind them, so a ladder of keys alone
    # could never reach those two goal types and would pass vacuously.
    _unlocks = [i.name for i in _mwv.itempool if i.name.startswith("Progressive ")]
    _wrong, _seen_both = [], set()
    for _i in range(len(_keys) + 1):
        _reached = {l.name for l in
                    state_with(_mwv, _base + _unlocks + _keys[:_i]).reachable_locations()}
        _done = sum(1 for _g in _goals if _g in _reached)
        _vic = "Victory" in _reached
        _seen_both.add(_vic)
        if _vic != (_done >= _req):
            _wrong.append((_i, _done, _vic))
    if _wrong:
        fail(f"goal_type={_gtname}: Victory disagrees with the goal count at "
             f"{len(_wrong)} step(s) (keys, goals reached, victory): {_wrong[:4]}")
    elif _seen_both != {False, True}:
        # Both sides of the threshold have to actually occur, or the loop
        # agreed with the rule without ever testing it.
        fail(f"goal_type={_gtname}: the ladder never crossed the threshold "
             f"(victory was always {_seen_both})")
    else:
        ok(f"goal_type={_gtname}: Victory opens exactly when {_req} worlds are "
           f"complete, over {len(_keys) + 1} key states")

# ...and the count has to be the thing that moves it, not the world count. A
# seed asking for more worlds than it contains clamps to what it has, so the
# win stays possible -- this is the "3 worlds, want 11" shape.
_mwc, _wc = build(world_count=3, worlds_required=11)
_sdc = _wc.fill_slot_data()
if _sdc["worlds_required"] > len(_sdc["goal_locations"]):
    fail(f"worlds_required {_sdc['worlds_required']} exceeds the "
         f"{len(_sdc['goal_locations'])} goals a 3-world seed builds")
else:
    _allc = [i.name for i in _mwc.precollected] +             [i.name for i in _mwc.itempool if i.classification == IC.progression]
    if "Victory" not in {l.name for l in state_with(_mwc, _allc).reachable_locations()}:
        fail("a 3-world seed asking for 11 worlds cannot be won")
    else:
        ok(f"worlds_required clamps to {_sdc['worlds_required']} in a 3-world "
           "seed and the win stays reachable")

print()
print(f"progression plants available: {len(PROG_PLANTS)}")
print("\n" + (f"{failed} FAILURE(S)" if failed else "SPHERE LOGIC OK"))
sys.exit(1 if failed else 0)
