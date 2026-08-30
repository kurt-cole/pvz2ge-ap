"""What a level DEMANDS, and which plants supply it.

Two halves, kept apart on purpose:

  TOKENS      the qualitative demands -- a Jester, deep water, tombstones. Each
              is answered or not; a hard token that is unanswered makes the
              level unwinnable no matter how much damage you have. These are
              what an access rule should be made of.
  PRESSURE    the quantitative demand, in HP/second (see pressure.py). This is
              NOT a good access rule -- "enough damage" is a loadout question,
              not an item question -- but it is what tells you WHERE a rule
              belongs: the point on the curve where the game stops carrying a
              player is the point a stretch should be cut.

The supply side is deliberately crude and deliberately honest. `afford_curve`
answers "with this loadout and this level's sun, what DPS can be on the lawn by
time t", by buying the best damage-per-sun plant it can afford as sun arrives.
It ignores placement, targeting, overkill and plant food. Use it to compare
loadouts against each other on one level, never to predict whether a human
clears it.
"""
import re

from . import taxonomy
from .classify import EXPOSED_LISTS

_ATOM = re.compile(r"^(role|element|flag|name|list):([^><=]+?)(?:\s*>=\s*(b[1-5]))?$")


def _atom_holds(atom, plant):
    m = _ATOM.match(atom.strip())
    if not m:
        raise ValueError(f"unparsable predicate atom: {atom!r}")
    kind, value, band = m.group(1), m.group(2).strip(), m.group(3)
    if kind == "role":
        have = plant["roles"].get(value)
        if not have:
            return False
        if band and taxonomy.BANDS.index(have) < taxonomy.BANDS.index(band):
            return False
        return True
    if kind == "element":
        return value in plant["elements"]
    if kind == "flag":
        return value in plant["flags"]
    if kind == "name":
        return plant["name"] == value
    if kind == "list":
        if value not in EXPOSED_LISTS:
            raise ValueError(f"predicate names a list that is not exposed: {value}")
        return plant["name"] in set(EXPOSED_LISTS[value])
    return False


def holds(predicate, plant):
    """Evaluate a threat_answers.json predicate against one plant record."""
    if isinstance(predicate, str):
        return _atom_holds(predicate, plant)
    if "any" in predicate:
        return any(holds(p, plant) for p in predicate["any"])
    if "all" in predicate:
        return all(holds(p, plant) for p in predicate["all"])
    if "not" in predicate:
        return not holds(predicate["not"], plant)
    return False


def answerers(token, answers, plants):
    """Every plant that answers a token, sorted. [] means nothing does."""
    spec = answers["tokens"].get(token)
    if not spec:
        return []
    return sorted(name for name, plant in plants.items()
                  if holds(spec["answer"], plant))


def requirement_vector(level, pressure, answers, plants):
    """The full demand record for one level.

    `must` is the list a hard access rule would be built from: one group per
    unanswered-is-fatal token, each group being every plant that answers it.
    That is exactly the shape WORLD_ENTRY_PLANTS already uses -- a list of
    groups, any-of within a group, all-of across them -- so a proposal here
    drops straight into constants.py without reshaping.
    """
    tokens = level.get("tokens") or []
    # A level the player does not pick plants for cannot be gated on a plant.
    # This is the single most important guard in the file: 'conveyor' means the
    # belt decides, so every plant requirement on such a level is a rule the
    # player can satisfy and still not be able to use.
    # `conveyor` in the tokens counts too, not only SelectionMethod: some
    # levels carry a ConveyorBelt module while their seed bank still says
    # "chooser", and on those the belt is what actually decides.
    gateable = (level.get("selection", "chooser") == "chooser"
                and "conveyor" not in tokens)

    must, soft, unanswerable, detail = [], [], [], []
    for token in tokens:
        spec = answers["tokens"].get(token)
        if not spec:
            detail.append({"token": token, "severity": "unknown", "answers": []})
            continue
        who = answerers(token, answers, plants)
        detail.append({
            "token": token,
            "severity": spec["severity"],
            "why": spec.get("why"),
            "current_rule": spec.get("current_rule"),
            "answers": who,
        })
        if spec["severity"] == "hard" and gateable:
            if who:
                must.append({"token": token, "any_of": who})
            else:
                unanswerable.append(token)
        elif spec["severity"] == "soft":
            soft.append(token)

    return {
        "codename": level.get("codename"),
        "gateable": gateable,
        "selection": level.get("selection"),
        "tokens": detail,
        "must": must,
        "soft": soft,
        # A hard token nothing in the item pool answers is a real hole in the
        # logic: the level demands something the multiworld cannot send.
        "unanswerable": unanswerable,
        "required_dps": (pressure or {}).get("peak"),
        "required_dps_per_lane": (pressure or {}).get("per_lane"),
        "index": (pressure or {}).get("index"),
    }


# ---- supply -----------------------------------------------------------

SUN_PER_DROP = 25.0
DROP_INTERVAL = 10.0
GRID_SLOTS = 45


def afford_curve(level, loadout, plants, horizon=None, step=5.0):
    """[(t, best_dps_on_lawn)] for a loadout, under this level's sun rules.

    Greedy: at every step spend all available sun on the best available
    damage-per-sun plant, up to the grid. Producers are bought first while they
    still pay for themselves within the level's remaining time, which is what
    makes a sun-producer requirement show up as a REAL constraint here rather
    than an assumption.
    """
    horizon = horizon or (level.get("duration") or 300.0)
    sun = float(level.get("starting_sun") or 50.0)
    drops = bool(level.get("sun_drop", True)) and "no_sun_drop" not in (level.get("tokens") or [])

    attackers = sorted(
        (p for p in (plants[n] for n in loadout if n in plants)
         if p.get("dps") and p.get("sun_cost")),
        key=lambda p: -(p["dps"] / max(p["sun_cost"], 1)))
    producers = [plants[n] for n in loadout
                 if n in plants and "sun_econ" in plants[n]["roles"]]
    producer = min(producers, key=lambda p: p.get("sun_cost") or 999, default=None)

    out, dps, planted, income = [], 0.0, 0, 0.0
    t = 0.0
    while t <= horizon:
        if drops:
            sun += SUN_PER_DROP / DROP_INTERVAL * step
        sun += income * step
        # Buy a producer while it can still pay back before the level ends.
        if producer and producer.get("sun_cost") and planted < GRID_SLOTS:
            payback = producer["sun_cost"] / 2.5
            if sun >= producer["sun_cost"] and (horizon - t) > payback * 2:
                sun -= producer["sun_cost"]
                planted += 1
                income += 2.5  # sun/sec, a Sunflower's nominal rate
                t += step
                out.append((round(t, 1), round(dps, 1)))
                continue
        for plant in attackers:
            if sun >= plant["sun_cost"] and planted < GRID_SLOTS:
                sun -= plant["sun_cost"]
                planted += 1
                dps += plant["dps"]
                break
        out.append((round(t, 1), round(dps, 1)))
        t += step
    return out


def clears(level, pressure, loadout, plants, answers):
    """Does this loadout satisfy the level -- tokens first, then damage?

    Tokens are checked before damage on purpose. A loadout that out-damages a
    Frostbite Caves level and brings no warmth does not clear it, and reporting
    that as a near miss on DPS would be exactly the wrong diagnosis.
    """
    vector = requirement_vector(level, pressure, answers, plants)
    missing = [group["token"] for group in vector["must"]
               if not (set(group["any_of"]) & set(loadout))]
    if missing:
        return {"clears": False, "reason": "tokens", "missing_tokens": missing}
    if not (pressure or {}).get("measured"):
        return {"clears": None, "reason": "unmeasured",
                "missing_tokens": [], "note": "tokens satisfied; no wave data to check damage"}

    supply = afford_curve(level, loadout, plants)
    curve = pressure.get("curve") or []
    if not curve:
        return {"clears": None, "reason": "unmeasured", "missing_tokens": []}
    step = pressure.get("curve_step_s") or 1.0
    worst, worst_t = None, None
    for i, need in enumerate(curve):
        t = i * step
        have = next((d for tt, d in reversed(supply) if tt <= t), 0.0)
        margin = have - need
        if worst is None or margin < worst:
            worst, worst_t = margin, t
    return {
        "clears": worst >= 0,
        "reason": "damage",
        "missing_tokens": [],
        "worst_margin": round(worst, 1),
        "worst_at": round(worst_t, 1),
    }
