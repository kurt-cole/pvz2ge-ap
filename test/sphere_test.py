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
    from pvz2gardendless.constants import SHOP_REGION
    ungated = len([l for l in w.active_locations()
                   if l.region not in ALL_WORLD_REGIONS and l.region != SHOP_REGION])
    print(f"        sphere 1 {first} of {total} ({first / total * 100:.0f}%) "
          f"-- {ungated} of those are ungated by design (side paths, tutorial)")

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

# ── the Egypt sun gate starts at egypt6 ─────────────────────────────────────
# "By Egypt level 6 you are expected to have a sun producing plant", expressed
# as a rule. egypt1-5 stay playable with nothing but the free starting plant --
# they are what sphere 1 is made of, and gating them would leave a seed with
# nowhere to begin.
#
# World locations are named for their level id, so these are just the level
# codes. They used to be spelled out as reward names ('Map Unlock',
# 'Cabbagepult Unlock' ...) with the codes in a trailing comment.
_mw, _w = build()
_pre = [i.name for i in _mw.precollected]
_open_egypt = ['egypt1', 'egypt2', 'egypt3', 'egypt4', 'egypt5']
_gated_egypt = ['egypt6', 'egypt7', 'egypt8', 'egypt9']

_no_sun = {l.name for l in state_with(_mw, _pre).reachable_locations()}
_with_sun = {l.name for l in state_with(_mw, _pre + ['Sunflower']).reachable_locations()}

_missing = [n for n in _open_egypt if n not in _no_sun]
if _missing:
    fail(f"egypt1-5 need more than the starting plant: {_missing}")
else:
    ok('egypt1-5 are playable with only the free starting plant')

_leaked = [n for n in _gated_egypt if n in _no_sun]
if _leaked:
    fail(f"reachable with no sun producer, so the gate does not start at egypt6: {_leaked}")
else:
    ok(f'all {len(_gated_egypt)} of egypt6-9 need a sun producer')

_still = [n for n in _gated_egypt if n not in _with_sun]
if _still:
    fail(f"a sun producer does not open egypt6-9: {_still}")
else:
    ok('a sun producer opens egypt6-9')

# Every sun producer must work, not just Sunflower -- the gate is has_any() and
# a seed may only ever offer one of the six.
for _p in SUN_PRODUCER_PLANTS:
    _r = {l.name for l in state_with(_mw, _pre + [_p]).reachable_locations()}
    if any(n not in _r for n in _gated_egypt):
        fail(f'{_p} does not satisfy the Egypt sun gate')
        break
else:
    ok(f'all {len(SUN_PRODUCER_PLANTS)} sun producers satisfy the gate')

# ── the shop opens with egypt6, not at the start ────────────────────────────
# index.js only sets feature_store once egypt6 is cleared (the same chain gives
# coins at tutorial4 and the zen garden at egypt5), so the store button does not
# exist in sphere 1 and its checks cannot be there either. regions.py hangs Shop
# off Ancient Egypt Mid1 to say exactly that.
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

    _open = {l.name for l in state_with(_mws, _pres + ["Sunflower"]).reachable_locations()}
    _shut = [n for n in _shop_locs if n not in _open]
    if _shut:
        fail(f"a sun producer does not open the shop: {_shut[:3]}")
    else:
        ok("a sun producer opens the shop, same as egypt6-9")

# THE structural guarantee, and the reason no early_items nudge is needed:
# a sun producer is the ONLY way out of sphere 1. Every world's entrance wants
# one on top of its key, and Egypt's own gate wants one at egypt6, so fill has
# to place a sun producer in sphere 1 or the seed never opens.
#
# Checked by brute force over the whole pool rather than by spot-checking a
# key, because the claim is about every item there is. This is what the
# comments in rules.py assert; if it ever stops holding, they overclaim and a
# seed can bury every sun producer behind a world key again.
_escapes = sorted(
    n for n in {i.name for i in _mw.itempool}
    if n not in SUN_PRODUCER_PLANTS
    and len(state_with(_mw, _pre + [n]).reachable_locations()) > len(_no_sun)
)
if _escapes:
    fail(f'{len(_escapes)} non-sun item(s) open locations on their own, so a sun '
         f'producer is not forced into sphere 1: {_escapes[:6]}')
else:
    ok('no item other than a sun producer opens anything from sphere 1, so fill '
       'must place one there')

# ...and each sun producer on its own really does open it, or that is a wall.
_stuck = [p for p in SUN_PRODUCER_PLANTS
          if len(state_with(_mw, _pre + [p]).reachable_locations()) <= len(_no_sun)]
if _stuck:
    fail(f'sun producers that open nothing: {_stuck}')
else:
    ok(f'each of the {len(SUN_PRODUCER_PLANTS)} sun producers opens sphere 1 on its own')

print()
print(f"progression plants available: {len(PROG_PLANTS)}")
print("\n" + (f"{failed} FAILURE(S)" if failed else "SPHERE LOGIC OK"))
sys.exit(1 if failed else 0)
