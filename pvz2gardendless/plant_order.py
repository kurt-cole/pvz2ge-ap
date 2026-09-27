"""
PvZ2 Gardendless: place strong useful plants in later spheres than weak ones.

Why after fill rather than an item rule. Useful items are placed after
progression, and many land in other games' locations, which this world cannot
put rules on. An item rule keyed on this world's own level depth would only
bind the plants that happen to land at home. Instead, once fill (and
progression balancing) is done, this module takes every location in the whole
multiworld that holds one of this slot's rankable useful plants and permutes
those plants among exactly those locations, weakest into the earliest real
sphere. That is a guarantee against the seed's actual spheres, in every game.

Why it cannot break a seed. Only non-progression items move, and only among
locations that already held one of them: nothing that logic counts changes
place, so reachability and every sphere are unchanged, and the set of
locations holding useful items (so excluded and priority locations) is too.
Each move is checked against the target location's own item rule
(`can_fill` without access), so local/non-local item settings and any other
game's restrictions hold. If the constrained assignment cannot be completed the
slot is left exactly as fill placed it.

Locked locations (plando) and unreachable ones (minimal accessibility) are
left alone.

THE RANKING [data, with a modelling caveat]. A plant's strength is its mean,
over every level in power_table.py, of the best break-even rung any loadout
using it as the ATTACKER reaches (0 fails at 750 per mille of the level's HP,
12 passes at 1333). This is the plant-power simulation of POWER_SIM.md, the
same model the power logic uses, not a hand list. Its limits, which follow from
that model: only the table's attackers are ranked (utility and producer gains
measured the same way are near zero, so they cannot be ordered and stay where
fill put them), and single-use plants (Cherry Bomb, Jalapeno, Doom-shroom)
score near zero because they cannot hold a level alone. [user] Those are left
out of the ranking too (sim_data kind "instant"), so they stay where fill put
them rather than being handed out early as "weak".
"""

import base64
import zlib
from typing import Dict, List, Optional, Sequence

try:
    from . import power_table as _T
except ImportError:          # a checkout before the offline run: nothing to rank by
    _T = None
from .sim_data import SIM_DATA

BANDS = 4                    # [user] the tiered mode's split, weakest to strongest

_SCORES: Optional[Dict[str, float]] = None


def strength_scores() -> Dict[str, float]:
    """Attacker name -> mean best break-even rung over every tabled level."""
    global _SCORES
    if _SCORES is None:
        out: Dict[str, float] = {}
        if _T is not None and _T.TABLE:
            np_, na, nu = len(_T.PRODUCER_AXIS), len(_T.ATTACKERS), len(_T.UTILITY_AXIS)
            totals = [0] * na
            for blob in _T.TABLE.values():
                row = zlib.decompress(base64.b64decode(blob))
                for a in range(na):
                    totals[a] += max(max(row[(p * na + a) * nu:(p * na + a + 1) * nu])
                                     for p in range(np_))
            n = len(_T.TABLE)
            plants = SIM_DATA["plants"]
            out = {name: totals[i] / n for i, name in enumerate(_T.ATTACKERS)
                   if plants.get(name, {}).get("k") != "instant"}
        _SCORES = out
    return _SCORES


def item_bands(names: Sequence[str], mode: str, rng) -> List[int]:
    """A band per name (0 weakest), for the items being ordered.

    tiered: BANDS equal bands by rank, so every plant in a band precedes
    every plant in a stronger band, with order random inside
    a band. Equal scores share a band. strict: every plant its own band, ties
    broken at random.
    """
    scores = strength_scores()
    n = len(names)
    order = sorted(range(n), key=lambda i: (scores[names[i]], rng.random()))
    bands = [0] * n
    first: Dict[float, int] = {}
    for rank, i in enumerate(order):
        if mode == "strict":
            bands[i] = rank
        else:
            bands[i] = first.setdefault(scores[names[i]], rank) * BANDS // max(n, 1)
    return bands


def order_player(player: int, sphere_of: Dict[object, int], filled: Sequence[object],
                 mode: str, rng, state) -> int:
    """Permute `player`'s rankable useful plants by sphere. Returns how many
    items changed location (0 when nothing moved or the assignment fell back)."""
    scores = strength_scores()
    locs = [loc for loc in filled
            if loc.item is not None and loc.item.player == player
            and loc.item.name in scores and not loc.item.advancement
            and not getattr(loc, "locked", False) and loc in sphere_of]
    if len(locs) < 2:
        return 0
    items = [loc.item for loc in locs]
    bands = item_bands([it.name for it in items], mode, rng)
    pending = sorted(range(len(items)), key=lambda i: (bands[i], rng.random()))
    targets = sorted(locs, key=lambda loc: (sphere_of[loc], rng.random()))

    plan = []
    for loc in targets:
        pick = next((k for k, i in enumerate(pending)
                     if loc.can_fill(state, items[i], False)), None)
        if pick is None:
            return 0         # a rule blocks the greedy match: keep fill's placement
        plan.append((loc, items[pending.pop(pick)]))

    moved = 0
    for loc, it in plan:
        if loc.item is not it:
            moved += 1
        loc.item = it
        it.location = loc
    return moved


def sphere_index(multiworld) -> Dict[object, int]:
    """Location -> sphere number, reachable locations only."""
    out: Dict[object, int] = {}
    for n, sphere in enumerate(multiworld.get_spheres()):
        if not sphere:
            break            # what follows is the unreachable remainder
        for loc in sphere:
            out[loc] = n
    return out
