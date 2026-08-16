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
    ungated = total - len(world_locs)
    print(f"        sphere 1 {first} of {total} ({first / total * 100:.0f}%) "
          f"-- {ungated} of those are ungated by design (side paths, tutorial, shop)")

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


report("all worlds, default")
report("all worlds + shuffle_zombies", shuffle_zombies=1)
report("all worlds + shopsanity", shopsanity=1)
report("3 worlds", world_count=3, worlds_required=11)
# Small seeds need the side paths back: without them the fixed plant+key block
# does not fit under a 3-world seed (see create_item_pool).
report("1 world (Egypt only)", world_count=1, worlds_required=11,
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
# Location names rather than level codes because that is what the regions hold;
# the mapping is the client's own LOC_LEVELS (egypt1 = Map Unlock,
# egypt2 = Cabbagepult Unlock, egypt3 = Bloomerang Unlock ... egypt9).
_mw, _w = build()
_pre = [i.name for i in _mw.precollected]
_open_egypt = ['Map Unlock', 'Cabbagepult Unlock', 'Bloomerang Unlock',
               'Powerupgadget Unlock', 'Iceburg Unlock']            # egypt1-5
_gated_egypt = ['Branch Unlock Egypt 6', 'Note Egypt Unlock',
                'World Key - Ancient Egypt', 'Gravebuster Unlock']  # egypt6-9

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
