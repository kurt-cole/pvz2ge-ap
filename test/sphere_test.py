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
report("1 world (Egypt only)", world_count=1, worlds_required=11)
report("2 worlds, completion goal", world_count=2, goal_type=1,
       worlds_required=11, modern_day_victory=2)
report("12 worlds, completion goal", goal_type=1, worlds_required=11, modern_day_victory=2)

# ── per-world entry requirements ────────────────────────────────────────────
from pvz2gardendless.constants import WORLD_ENTRY_PLANTS, SUN_PRODUCER_PLANTS, JESTER_COUNTER_PLANTS

print("\n=== world entry requirements ===")
mw, w = build()
for world_name, groups in WORLD_ENTRY_PLANTS.items():
    key = f"{world_name} Key"
    base = [i.name for i in mw.precollected] + [key]

    def opens(extra):
        st = state_with(mw, base + extra)
        return any(r.name == world_name for r in st._reachable)

    if opens([]):
        fail(f"{world_name} opens on its key alone, ignoring its plant requirements")
    else:
        ok(f"{world_name}: key alone is not enough ({len(groups)} plant requirement(s))")

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
fbase = [i.name for i in mw.precollected] + ["Frostbite Caves Key"]
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

print()
print(f"progression plants available: {len(PROG_PLANTS)}")
print("\n" + (f"{failed} FAILURE(S)" if failed else "SPHERE LOGIC OK"))
sys.exit(1 if failed else 0)
