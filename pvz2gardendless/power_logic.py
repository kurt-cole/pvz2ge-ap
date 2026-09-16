"""
PvZ2 Gardendless: generation logic for the plant-power loadout simulation.

Design: POWER_SIM.md. This module reads pvz2gardendless/power_table.py (the
offline break-even of every loadout per level) and turns it into what rules.py,
the progression promote and the item-pool floor need:

  level_requirement(world, name) -> Requirement or None
      the loadouts that pass this built level at its rolled HP ratio.
  nullifier_groups(world, name) -> [plant group, ...]
      counter rules for plant-nullifying zombies the level fields.
  promoted_plants(world) -> set of plant names every requirement can name.
  floor_groups(world) -> [[plant], ...] a loadout set that passes every built
      level, for the pool floor.
  select(world) -> the plants this slot's power and counter rules may name.

Selection [user]: naming every passing loadout made nearly every plant
progression. select() walks the built levels in play order and keeps a small
set of plants, adding plants only where a level has fewer than
power_loadouts_per_level distinct passing loadouts (1 for the opening levels)
from what is already kept. New plants are preferred when they are cheap (fewest
new plants), then by how many built levels they help pass, with a seeded pick
among the best few so seeds differ. Every rule afterwards names only kept
plants (and granted ones).

No simulation runs here: a loadout passes a rolled level when the level's HP
ratio is at or below the loadout's break-even (see POWER_SIM.md for the
approximation this makes and why).
"""

import bisect
import base64
import zlib
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from . import level_model, zombie_roll
from .sim_data import SIM_DATA

try:
    from . import power_table as _T
except ImportError:          # a checkout before the offline run; old model applies
    _T = None

PLANTS = SIM_DATA["plants"]
ZOMBIES = SIM_DATA["zombies"]

# Triples are packed as ints: producer * NA * NU + attacker * NU + utility.
Requirement = FrozenSet[int]

_DECODED: Dict[str, bytes] = {}
_REQ_CACHE: Dict[Tuple[str, int], Requirement] = {}


def available() -> bool:
    return _T is not None


def has_level(name: str) -> bool:
    return _T is not None and name in _T.TABLE


def _row(name: str) -> bytes:
    if name not in _DECODED:
        _DECODED[name] = zlib.decompress(base64.b64decode(_T.TABLE[name]))
    return _DECODED[name]


def _ratio(world, name: str) -> int:
    plan = getattr(world, "budget_plans", {}).get(name)
    if not plan or plan.get("vanilla"):
        return 1000
    return int(plan["ratio"])


def requirement_for(name: str, ratio: int) -> Requirement:
    """Every packed loadout whose break-even covers `ratio` per mille.

    If no loadout reaches it (the model finds the level unwinnable at that HP),
    the best score any loadout reaches is used instead, so a rule never names an
    impossible requirement.
    """
    key = (name, ratio)
    if key in _REQ_CACHE:
        return _REQ_CACHE[key]
    row = _row(name)
    need = bisect.bisect_left(_T.SCALES, ratio) + 1
    best = max(row) if row else 0
    if best < need:
        need = best
    out = frozenset(i for i, v in enumerate(row) if v >= need and v > 0)
    _REQ_CACHE[key] = out
    return out


def _plant_sets() -> List[FrozenSet[str]]:
    """Packed triple -> the plant names it holds, for every table index."""
    global _SETS
    if _SETS is None:
        out = []
        for p in _T.PRODUCER_AXIS:
            for a in _T.ATTACKERS:
                for u in _T.UTILITY_AXIS:
                    out.append(frozenset(x for x in (p, a, u) if x))
        _SETS = out
    return _SETS


_SETS: Optional[List[FrozenSet[str]]] = None


def _available(world) -> Optional[Set[str]]:
    """Kept plants plus granted ones, or None when the slot has no selection
    (plant power logic off, or a seed from before selection existed)."""
    sel = getattr(world, "power_selection", None)
    if sel is None:
        return None
    return set(sel) | set(getattr(world, "starting_plants", ()))


def level_requirement(world, name: str) -> Optional[Requirement]:
    if not has_level(name):
        return None
    req = requirement_for(name, _ratio(world, name))
    avail = _available(world)
    if avail is not None and req:
        cache = world.__dict__.setdefault("_power_req_cache", {})
        if name not in cache:
            sets = _plant_sets()
            kept = frozenset(i for i in req if sets[i] <= avail)
            # Never empty: a selection that cannot pass the level (a tracker
            # fed a foreign selection) falls back to every passing loadout.
            cache[name] = kept or req
        req = cache[name]
    return req or None


def unpack(i: int) -> Tuple[Optional[str], str, Optional[str]]:
    nu = len(_T.UTILITY_AXIS)
    na = len(_T.ATTACKERS)
    return (_T.PRODUCER_AXIS[i // (na * nu)], _T.ATTACKERS[(i // nu) % na],
            _T.UTILITY_AXIS[i % nu])


class RuleShape:
    """A requirement arranged for fast evaluation: {(producer, utility): attackers}."""
    __slots__ = ("by_pu",)

    def __init__(self, req: Requirement):
        by: Dict[Tuple[Optional[str], Optional[str]], Set[str]] = {}
        for i in req:
            p, a, u = unpack(i)
            by.setdefault((p, u), set()).add(a)
        # Cheapest checks first: no producer, no utility.
        self.by_pu = sorted(((p, u, tuple(sorted(a))) for (p, u), a in by.items()),
                            key=lambda e: (e[0] is not None, e[1] is not None, e[0] or "",
                                           e[1] or ""))

    def passes(self, state, player) -> bool:
        for p, u, attackers in self.by_pu:
            if p is not None and not state.has(p, player):
                continue
            if u is not None and not state.has(u, player):
                continue
            if state.has_any(attackers, player):
                return True
        return False


def requirement_plants(req: Requirement) -> Set[str]:
    out: Set[str] = set()
    for i in req:
        p, a, u = unpack(i)
        out.add(a)
        if p:
            out.add(p)
        if u:
            out.add(u)
    return out


# ── nullifiers ───────────────────────────────────────────────────────────────

def _tagged(tag: str) -> List[str]:
    return sorted(n for n, p in PLANTS.items() if tag in p.get("tags", ()))


def _ranged() -> List[str]:
    return sorted(n for n, p in PLANTS.items()
                  if p["k"] in ("shooter", "burst", "sunburn") and not p.get("r"))


def level_zombies(world, name: str) -> Set[str]:
    """Codenames a built level fields: its rolled plan, else its vanilla roster."""
    plan = getattr(world, "budget_plans", {}).get(name)
    level = level_model.load()["levels"].get(name)
    if level is None:
        return set()
    if plan and not plan.get("vanilla"):
        names = set(zombie_roll.roster(plan))
    else:
        names = {c for g in level["groups"] for c, _ in g["z"]}
    for entry in level["dynamic"]:
        names.update(entry["pool"])
    return names


def narrow(world, group) -> List[str]:
    """`group` cut to the slot's selection, or whole when that leaves nothing
    or the slot has no selection."""
    avail = _available(world)
    if avail is None:
        return list(group)
    return sorted(set(group) & avail) or list(group)


def nullifier_groups(world, name: str) -> List[List[str]]:
    """[user] counter rules for zombies that disable plants, per level fielding
    them, narrowed to the slot's selection where it has one."""
    groups = _raw_nullifier_groups(world, name)
    avail = _available(world)
    if avail is None:
        return groups
    return [sorted(set(g) & avail) or g for g in groups]


def _raw_nullifier_groups(world, name: str) -> List[List[str]]:
    if not has_level(name):
        return []
    tags: Set[str] = set()
    for c in level_zombies(world, name):
        tags.update(ZOMBIES.get(c, {}).get("tags", ()))
    instant = _tagged("instant")
    groups: List[List[str]] = []
    if "torch" in tags:
        groups.append(_tagged("ice"))
    if tags & {"wizard", "drone", "breakdancer", "garg"}:
        groups.append(instant)
    if tags & {"boombox", "skunk"}:
        groups.append(_ranged())
    if "excavator" in tags:
        groups.append(sorted(set(_tagged("backward")) | set(instant)))
    if "bomb" in tags:
        groups.append(sorted(set(instant) | {n for n, p in PLANTS.items() if p["k"] == "burst"}))
    return groups


# ── selection ────────────────────────────────────────────────────────────────

OPENING_LOADOUTS = 1   # [user] tutorial and egypt1-5 need one loadout, not more
PICK_AMONG = 3         # the seeded pick is among this many best candidates


def _play_order(world, names: List[str]) -> List[str]:
    from .locations import level_predecessors
    preds = level_predecessors(names)

    def d(n):
        k, seen = 0, set()
        while n in preds and n not in seen:
            seen.add(n)
            n = preds[n]
            k += 1
        return k

    # Ties (same depth in different worlds) are drawn, so the worlds a seed
    # meets first are not always settled alphabetically.
    keyed = [((0 if n.startswith(("tutorial", "egypt")) else 1), d(n), world.random.random(), n)
             for n in sorted(names)]
    return [k[-1] for k in sorted(keyed)]


def _antichain_count(sets) -> int:
    """How many of `sets` are not a strict superset of another: the loadouts
    that are genuinely different ways to pass, not the same one plus extras."""
    uniq = sorted(set(sets), key=len)
    kept: List[FrozenSet[str]] = []
    for s in uniq:
        if not any(k <= s for k in kept):
            kept.append(s)
    return len(kept)


def select(world) -> FrozenSet[str]:
    """The plants this slot's power and counter rules may name (see module doc)."""
    if not available() or not getattr(world.options, "plant_power_logic", 0):
        return frozenset()
    want_n = int(getattr(getattr(world.options, "power_loadouts_per_level", None),
                         "value", 2))
    granted = set(getattr(world, "starting_plants", ()))
    sets = _plant_sets()
    from . import budget_logic
    hazards = getattr(world, "budget_hazards", {})
    names = [loc.name for loc in world.active_locations()
             if has_level(loc.name) or hazards.get(loc.name)]
    reqs = {n: requirement_for(n, _ratio(world, n)) if has_level(n) else frozenset()
            for n in names}
    # Counter groups: nullifiers, and the budget roll's hazard counters (read
    # before a selection exists, so whole).
    counters = {n: _raw_nullifier_groups(world, n)
                + [g for g, _ in budget_logic.level_hazard_groups(world, n) if g]
                for n in names}
    # How many built levels each plant helps pass: the "global" half of a pick.
    help_count: Dict[str, int] = {}
    for n in names:
        seen: Set[str] = set()
        for i in reqs[n]:
            seen |= sets[i]
        for g in counters[n]:
            seen.update(g)
        for plant in seen:
            help_count[plant] = help_count.get(plant, 0) + 1

    chosen: Set[str] = set()
    rng = world.random

    def pick(cands):
        """cands: [(cost, -help, tiebreak, value)] -> a seeded pick among the best."""
        cands.sort()
        best = [c for c in cands if c[0] == cands[0][0]][:PICK_AMONG]
        return best[rng.randrange(len(best))][-1]

    for n in _play_order(world, names):
        need = OPENING_LOADOUTS if n in zombie_roll.OPENING_LEVELS else want_n
        for g in counters[n]:
            target = min(need, len(g))
            while len(set(g) & (chosen | granted)) < target:
                free = sorted(set(g) - chosen - granted)
                chosen.add(pick([(1, -help_count.get(x, 0), x, x) for x in free]))
        req = reqs[n]
        if not req:
            continue
        distinct = {sets[i] for i in req}
        target = min(need, _antichain_count(distinct))
        while True:
            avail = chosen | granted
            held = [s for s in distinct if s <= avail]
            if _antichain_count(held) >= target:
                break
            cands = []
            for s in distinct:
                if s <= avail or any(h <= s for h in held):
                    continue          # already held, or adds nothing new
                new = s - avail
                cands.append((len(new), -sum(help_count.get(x, 0) for x in new),
                              tuple(sorted(s)), s))
            if not cands:
                break
            chosen |= pick(cands)
    return frozenset(chosen)


# ── promote and floor ────────────────────────────────────────────────────────

def built_requirements(world) -> Dict[str, Requirement]:
    out = {}
    if not getattr(world.options, "plant_power_logic", 0):
        return out
    for loc in world.active_locations():
        req = level_requirement(world, loc.name)
        if req:
            out[loc.name] = req
    return out


def promoted_plants(world) -> Set[str]:
    plants: Set[str] = set()
    for req in built_requirements(world).values():
        plants |= requirement_plants(req)
    for loc in world.active_locations():
        for group in nullifier_groups(world, loc.name):
            plants.update(group)
    return plants


def floor_loadouts(world) -> List[Tuple[Optional[str], str, Optional[str]]]:
    """A few loadouts that between them pass every built level, greedy set cover.

    Ties go to the loadout with fewer plants, then by name, so a seed is stable.
    Granted plants count as already held.
    """
    reqs = built_requirements(world)
    uncovered = set(reqs)
    chosen = []
    while uncovered:
        counts: Dict[int, int] = {}
        for lv in uncovered:
            for i in reqs[lv]:
                counts[i] = counts.get(i, 0) + 1
        if not counts:
            break

        def key(i):
            p, a, u = unpack(i)
            return (-counts[i], (p is not None) + (u is not None), p or "", a, u or "")
        pick = min(counts, key=key)
        chosen.append(unpack(pick))
        uncovered = {lv for lv in uncovered if pick not in reqs[lv]}
    return chosen


def floor_groups(world) -> List[List[str]]:
    out, seen = [], set()
    for p, a, u in floor_loadouts(world):
        for plant in (p, a, u):
            if plant and plant not in seen:
                seen.add(plant)
                out.append([plant])
    return out
