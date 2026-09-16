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


def level_requirement(world, name: str) -> Optional[Requirement]:
    if not has_level(name):
        return None
    req = requirement_for(name, _ratio(world, name))
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


def nullifier_groups(world, name: str) -> List[List[str]]:
    """[user] counter rules for zombies that disable plants, per level fielding them."""
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
