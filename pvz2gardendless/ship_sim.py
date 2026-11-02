"""
PvZ2 Gardendless: the Aerial Fortress ship guard on the budget zombie roll.

Design: POWER_SIM.md, "Ship levels". On a ship lawn (SIM_DATA["ships"]) a
zombie never eats its way in: it stops at the ship's edge and either fires at
the ship (ShipDPS, for as long as it lives) or crashes into it
(CrashDamageToShip, once). So how many bodies reach the edge matters more than
their total HP, and an HP-balanced roll can still swap a few tough zombies for a
swarm that burns the ship down. This module measures that.

    damage(level_id, plan, dps, hp_scale) -> ship damage

runs the level's roster against a REFERENCE DEFENCE: `dps` damage per second
in every lane, from the first wave on, killing each lane's zombies in turn.
That stands in for whatever the belt (or the player) actually supplies, which
generation does not know; only comparisons at the same `dps` mean anything.

    reference_dps(level_id) -> the dps at which the vanilla roster costs the
                               ship CALIBRATION_PERMILLE of its HP
    accepts(level_id, plan) -> the roll passes the guard

A plan passes when its ship damage at the reference defence is at most
TOLERANCE_PERMILLE of the vanilla roster's, scaled to the plan's HP ratio, and
below the ship's HP. Generation picks the attempt (zombie_roll.roll_level's
`accept`) and sends it to the client, which rolls that attempt directly.

Pure Python floats: the guard runs only at generation (and in Universal
Tracker, which re-runs generation), never in the client.
"""

from typing import Any, Dict, Optional

from . import power_sim

# [user] Relative to vanilla. A roll may cost the ship up to this per mille of
# what vanilla costs it at the same defence (scaled to the roll's HP ratio).
TOLERANCE_PERMILLE = 1150
# The reference defence is calibrated so that vanilla costs the ship half its
# HP: hard enough that a swarm shows, soft enough that a damage-free vanilla
# run does not make every roll fail.
CALIBRATION_PERMILLE = 500
_DPS_LO, _DPS_HI, _STEPS = 1.0, 50000.0, 40

SHIPS = power_sim.SHIPS
LEVELS = power_sim.LEVELS


def is_ship_level(level_id: str) -> bool:
    return level_id in SHIPS


def _timing(level_id: str):
    """(first wave, flag interval, next-wave health fraction) of the level."""
    ship = SHIPS[level_id]
    return ship["first"], ship["flag"], ship["next"]


def damage(level_id: str, plan: Optional[Dict[str, Any]] = None, dps: float = 0.0,
           hp_scale: float = 1.0) -> float:
    """Ship damage the roster deals against `dps` per lane. `plan` None is vanilla."""
    ship = SHIPS[level_id]
    waves, lanes = power_sim.roster(level_id, plan)
    first, flag, nxt_frac = _timing(level_id)
    dist = max(0.0, power_sim.SPAWN_X - ship["edge"])
    free = [0.0] * lanes          # when each lane's defence is next free
    load = [0.0] * lanes
    total = 0.0
    t_wave = first
    for w, zombies in enumerate(waves):
        here = [0.0] * lanes
        kills = []
        for hp, walk, _, row, _, sdps, crash, _ in sorted(zombies, key=lambda z: -z[0]):
            lane = row if 0 <= row < lanes else min(range(lanes),
                                                     key=lambda x: (here[x], load[x]))
            here[lane] += hp
            load[lane] += hp
            if walk <= 0:
                continue                         # immobile: never reaches the ship
            hp *= hp_scale
            arrive = t_wave + dist / walk
            start = max(free[lane], t_wave)
            done = start + hp / dps
            if done <= arrive:
                free[lane] = done
                kills.append((done, hp))
            elif crash:
                # Spent on the ship at arrival; the defence moves on.
                total += crash
                free[lane] = max(free[lane], min(arrive, done))
                kills.append((arrive, hp))
            else:
                total += sdps * (done - arrive)
                free[lane] = done
                kills.append((done, hp))
        timer = t_wave + power_sim.WAVE_TIMER + (
            power_sim.FLAG_EXTRA if flag and (w + 1) % flag == 0 else 0.0)
        nxt = timer
        whole = sum(h for _, h in kills)
        if whole > 0:
            gone = 0.0
            for done, h in sorted(kills):
                gone += h
                if gone >= whole * (1.0 - nxt_frac):
                    nxt = min(timer, max(t_wave + power_sim.EARLY_WAVE_MIN, done))
                    break
        t_wave = nxt
    return total


_REF: Dict[str, float] = {}


def reference_dps(level_id: str) -> float:
    """Per-lane dps at which vanilla costs the ship CALIBRATION_PERMILLE of its HP.

    Ship damage falls as dps rises, so this bisects. A level whose vanilla
    roster cannot reach that much damage even at _DPS_LO gets _DPS_LO.
    """
    if level_id in _REF:
        return _REF[level_id]
    goal = SHIPS[level_id]["hp"] * CALIBRATION_PERMILLE / 1000.0
    lo, hi = _DPS_LO, _DPS_HI
    if damage(level_id, None, lo) <= goal:
        _REF[level_id] = lo
        return lo
    for _ in range(_STEPS):
        mid = (lo * hi) ** 0.5
        if damage(level_id, None, mid) > goal:
            lo = mid
        else:
            hi = mid
    _REF[level_id] = hi
    return hi


def accepts(level_id: str, plan: Dict[str, Any]) -> bool:
    """The roll's ship damage is within TOLERANCE of vanilla's and below ship HP."""
    if plan.get("vanilla"):
        return True
    dps = reference_dps(level_id)
    ratio = plan.get("ratio", 1000) / 1000.0
    base = damage(level_id, None, dps, ratio)
    got = damage(level_id, plan, dps)
    return got <= base * TOLERANCE_PERMILLE / 1000.0 and got < SHIPS[level_id]["hp"]
