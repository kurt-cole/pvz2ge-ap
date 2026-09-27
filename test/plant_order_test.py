"""useful_plant_order: weak useful plants early, strong ones late (plant_order.py).

Checks, on a real default slot's item pool placed across a fake multiworld:
  - the option defaults to tiered and the world registers the reorder stage;
  - after the reorder, every band's latest sphere is at or before the next
    band's earliest (tiered), or the full ranking is monotone (strict);
  - only this slot's rankable non-progression plants move, and only among the
    locations they already held (other players' items, progression, locked
    and unreachable locations are untouched);
  - a location item rule is honoured, and an impossible one falls back to
    fill's placement unchanged;
  - off leaves everything alone.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401
from apstub import MultiWorld  # noqa: E402

import pvz2gardendless as W  # noqa: E402
from pvz2gardendless import plant_order as PO  # noqa: E402
from pvz2gardendless.options import UsefulPlantOrder  # noqa: E402
from opts import Opts  # noqa: E402

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


class Loc:
    def __init__(self, name, player, rule=None, locked=False):
        self.name, self.player, self.item, self.locked = name, player, None, locked
        self.rule = rule or (lambda item: True)

    def can_fill(self, state, item, check_access=True):
        return self.rule(item)


class It:
    def __init__(self, name, player, advancement=False):
        self.name, self.player, self.advancement, self.location = name, player, advancement, None


def place(loc, it):
    loc.item, it.location = it, loc


def slot_items():
    mw = MultiWorld()
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts()
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    return w, list(mw.itempool)


def scatter(items, seed, spheres=12):
    """Every item into its own location across two players, random spheres."""
    rng = random.Random(seed)
    locs, sphere_of = [], {}
    for i, it in enumerate(items):
        loc = Loc(f"L{i}", rng.choice((1, 2)))
        place(loc, it)
        locs.append(loc)
        sphere_of[loc] = rng.randrange(spheres)
    return locs, sphere_of


def movable(locs, player=1):
    scores = PO.strength_scores()
    return [l for l in locs if l.item.player == player and l.item.name in scores
            and not l.item.advancement and not l.locked]


def check_order(locs, sphere_of, mode, label):
    ms = [l for l in movable(locs) if l in sphere_of]
    names = [l.item.name for l in ms]
    scores = PO.strength_scores()
    if mode == "strict":
        # Strict monotone: any stronger plant in a strictly earlier sphere than a weaker one fails.
        inv = sum(1 for a in ms for b in ms
                  if sphere_of[a] < sphere_of[b] and scores[a.item.name] > scores[b.item.name])
        (fail if inv else ok)(f"{label}: strict order has {inv} inversions")
        return
    ranked = sorted(names, key=lambda n: scores[n])
    n = len(ranked)
    first = {}
    for rank, name in enumerate(ranked):
        first.setdefault(scores[name], rank)
    band_of = {name: first[scores[name]] * PO.BANDS // n for name in names}
    inv = 0
    for a in ms:
        for c in ms:
            if sphere_of[a] > sphere_of[c] and band_of[a.item.name] < band_of[c.item.name]:
                inv += 1
    (fail if inv else ok)(f"{label}: {len(ms)} plants, {inv} weaker-band-after-stronger-band pairs")


print("\n-- option and hook")
(ok if UsefulPlantOrder.default == UsefulPlantOrder.option_tiered else fail)(
    "useful_plant_order defaults to tiered")
hook = (getattr(W.PvZ2GardendlessWorld, "stage_finalize_multiworld", None)
        or getattr(W.PvZ2GardendlessWorld, "stage_post_fill", None))
(ok if hook else fail)("the world registers a post-fill reorder stage")
scores = PO.strength_scores()
_instants = [n for n in ("Cherry Bomb", "Jalapeno", "Doom-shroom", "Squash") if n in scores]
(fail if _instants else ok)(f"single-use instants are not ranked ({_instants or 'none'})")
(ok if len(scores) > 50 else fail)(f"power_table ranks {len(scores)} attackers")

w, base_pool = slot_items()
rankable = [it for it in base_pool if it.name in scores and not it.advancement]
(ok if len(rankable) >= 10 else fail)(
    f"a default slot has {len(rankable)} rankable useful plants to order")

for mode in ("tiered", "strict"):
    for seed in range(5):
        pool = [It(it.name, it.player, it.advancement) for it in base_pool]
        others = [It(f"Other {i}", 2) for i in range(40)] + [It("Peashooter", 2)]
        items = pool + others
        locs, sphere_of = scatter(items, seed)
        # One locked and one unreachable location holding rankable plants.
        movers = movable(locs)
        movers[0].locked = True
        unreachable = movers[1]
        del sphere_of[unreachable]
        before = {l: l.item for l in locs}
        moved = PO.order_player(1, sphere_of, locs, mode, random.Random(seed), None)
        (ok if moved else fail)(f"{mode} seed {seed}: {moved} plants moved")
        check_order(locs, sphere_of, mode, f"{mode} seed {seed}")
        fixed = [l for l in locs if l not in movable(locs) or l.locked or l is unreachable]
        changed = [l.name for l in fixed if l.item is not before[l]]
        (fail if changed else ok)(f"{mode} seed {seed}: unmovable locations untouched ({len(changed)} changed)")
        ms_before = sorted(id(before[l]) for l in locs if l in movable(locs))
        ms_after = sorted(id(l.item) for l in locs if l in movable(locs))
        (ok if ms_before == ms_after else fail)(f"{mode} seed {seed}: a permutation of the same items")
        linked = all(l.item.location is l for l in locs)
        (ok if linked else fail)(f"{mode} seed {seed}: item.location follows each move")

print("\n-- item rules")
names = sorted(scores, key=scores.get)
weak, strong = names[0], names[-1]
a, b = It(weak, 1), It(strong, 1)
early = Loc("early", 1, rule=lambda it: it.name != weak)   # cannot take the weak plant
late = Loc("late", 1)
place(early, b), place(late, a)
PO.order_player(1, {early: 0, late: 5}, [early, late], "tiered", random.Random(0), None)
(ok if early.item is b and late.item is a else fail)(
    "a rule forbidding the ideal swap keeps fill's placement")

early.rule = lambda it: True
PO.order_player(1, {early: 0, late: 5}, [early, late], "strict", random.Random(0), None)
(ok if early.item is a and late.item is b else fail)("with no rule, the weaker plant moves early")

nowhere = Loc("nowhere", 1, rule=lambda it: False)
c = It(names[len(names) // 2], 1)
place(nowhere, c)
before = (early.item, late.item, nowhere.item)
PO.order_player(1, {early: 0, late: 5, nowhere: 9}, [early, late, nowhere], "strict",
                random.Random(0), None)
(ok if (early.item, late.item, nowhere.item) == before else fail)(
    "an unsatisfiable rule falls back to no change")

print("\n-- off")
mw = MultiWorld()
w1 = W.PvZ2GardendlessWorld(mw, 1)
w1.options = Opts(useful_plant_order=0)
mw.worlds = {1: w1}
called = []
mw.get_spheres = lambda: called.append(1) or iter(())
mw.get_filled_locations = lambda: []
mw.state = None
W.PvZ2GardendlessWorld._order_useful_plants(mw)
(ok if not called else fail)("off never computes spheres")
w1.options = Opts()
W.PvZ2GardendlessWorld._order_useful_plants(mw)
(ok if called else fail)("tiered computes spheres through the stage hook")

print(f"\n{'FAILED: %d' % failed if failed else 'all plant order checks passed'}")
sys.exit(1 if failed else 0)
