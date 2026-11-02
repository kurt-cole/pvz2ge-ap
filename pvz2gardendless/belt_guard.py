"""
PvZ2 Gardendless: the conveyor belt guard. Design: POWER_SIM.md, "Conveyor
levels".

    attempts(world, conveyor_seed) -> {level id: attempt}

For each conveyor level the slot builds, rolls the belt the client would deal
(belt_roll.roll) attempt by attempt, and keeps the first one that beats the
level's zombies as this slot rolls them at the vanilla belt's score over
BELT_TOLERANCE (belt_table.BELT_SCORES; relative, so what the simulation gets
wrong about a level cancels). None of BELT_ATTEMPTS holds: -1, the belt as
shipped. A level scoring 0, which the simulation cannot judge, gets no entry
and so rolls attempt 0, the swap's own rules only [user].

Zombies: the budget roll's plan where it ran (world.budget_plans); otherwise
the vanilla roster, which is what the tier shuffle keeps in HP band and
threat tag (zombie_data tiers), so the belt's threats are the vanilla ones too.
Deterministic in the seed, consumes no RNG.
"""

import hashlib
import os
from typing import Any, Dict

from . import belt_roll, belt_sim, level_model, zombie_roll

BELT_TOLERANCE = 1.15
BELT_ATTEMPTS = 8

_INPUTS = ("belt_sim.py", "power_sim.py", "sim_data.py", "level_model.py")


def input_hash() -> str:
    """Hash of the files a vanilla score depends on (belt_table.INPUT_HASH)."""
    here = os.path.dirname(os.path.abspath(__file__))
    h = hashlib.sha256()
    for name in _INPUTS:
        with open(os.path.join(here, name), "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def _scores() -> Dict[str, float]:
    try:
        from .belt_table import BELT_SCORES
    except ImportError:
        return {}
    return BELT_SCORES


def _fielded(level_id: str, plan) -> set:
    if plan is not None:
        return zombie_roll.fielded(plan)
    level = level_model.load()["levels"][level_id]
    return {c for g in level["groups"] for c, _ in g["z"]} | \
        {c for e in level["dynamic"] for c in e["pool"]}


def choose(seed: int, level_id: str, plan=None) -> int:
    """The attempt for one level, or 0 when the guard does not judge it."""
    vanilla = _scores().get(level_id, 0.0)
    if vanilla <= 0 or level_id not in belt_sim.BELTS:
        return 0
    level = level_model.load()["levels"][level_id]
    threats = belt_roll.level_threats(level_id, _fielded(level_id, plan), level["stage"])
    need = vanilla / BELT_TOLERANCE
    for attempt in range(BELT_ATTEMPTS):
        belt = belt_roll.roll(seed, level_id, attempt, threats)
        if belt_sim.passes(level_id, belt, plan, need):
            return attempt
    return -1


def attempts(world, seed: int) -> Dict[str, int]:
    """slot_data belt_attempts: only the levels whose pick is not attempt 0."""
    plans: Dict[str, Any] = getattr(world, "budget_plans", {}) or {}
    out = {}
    for loc in world.active_locations():
        if loc.name not in belt_sim.BELTS:
            continue
        pick = choose(seed, loc.name, plans.get(loc.name))
        if pick:
            out[loc.name] = pick
    return dict(sorted(out.items()))
