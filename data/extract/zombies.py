"""Zombie stats: what a level's HP is actually made of.

Read out of the game's own two tables, `ZombieTypes` (codename -> properties)
and `ZombieProps` (the properties), plus `ArmorProps` for what they arrive
wearing.

The three fields that matter, and their real names -- each of which is a thing
this repo has already had to learn once:

    Toughness       body HP. NOT "Hitpoints"; nothing in this data is called
                    that.
    StartingArmors  a list of ArmorProps aliases. mummy_armor2 has Toughness
                    190 and an egypt_armor2 worth 1100, so reading the body
                    alone understates it by six times. This is why a t3 zombie
                    is not "a bit tougher" -- it is a different problem.
    WalkSPS         squares per second, so it needs NO calibration constant:
                    the lawn is nine columns and a 0.185 SPS mummy takes 48.6
                    seconds to cross it. Everything downstream is in real
                    seconds because of this.

`WavePointCost` is the game's OWN price for fielding one, and levels.py spends
it against each wave's stated budget, so the dynamic half of a wave is priced
by the game rather than by us.
"""
from ..model.taxonomy import ZOMBIE_TAGS

# Columns from the spawn edge to the house. The standard PvZ2 lawn.
LANE_COLUMNS = 9.0

# Used only where WalkSPS is absent, which is a handful of scripted types.
DEFAULT_SPS = 0.19


def _num(obj, *fields, default=None):
    for f in fields:
        v = obj.get(f)
        if isinstance(v, (int, float)):
            return float(v)
    return default


def _armor_hp(index, props):
    """Total Toughness of everything the zombie arrives wearing."""
    armor_doc = index.group("ArmorProps")
    total, unknown = 0.0, []
    names = props.get("StartingArmors") or []
    if isinstance(names, str):
        names = [names]
    for name in names:
        data = None
        if isinstance(name, str):
            data = (armor_doc.by_alias.get(name) if armor_doc else None) \
                or index.resolve(name)
        elif isinstance(name, dict):
            data = name
        if isinstance(data, dict):
            total += _num(data, "Toughness", default=0.0)
        else:
            unknown.append(str(name))
    return total, unknown


def _tags(props):
    """Threat tokens, from the fields that state the mechanic outright.

    The same partition zombie_data.py's tier suffixes are built on; data's
    test_data.py asserts the two still agree.
    """
    tags = set()
    sort = props.get("ZombieSort")
    if sort == "Gargantuar":
        tags.add("garg")
    if sort == "Zomboss":
        tags.add("zomboss")
    if props.get("LivesInDeepWater"):
        tags.add("water")
    if props.get("MoveSpeedMultiplierWhileJuggling") is not None:
        tags.add("jester")
    if props.get("NumberOfIceblocksToSpawnWith"):
        tags.add("iceblock")
    if any(props.get(k) is not None for k in
           ("BalloonToughness", "FlyDuration", "FlyingSpeedScale",
            "IsSpawnedFlying", "JetpackProps")):
        tags.add("air")
    if props.get("PlantBlockers") or props.get("ZombieBlockers"):
        tags.add("blocker")
    if props.get("HurdleProps") or props.get("CanJumpOverPlants"):
        tags.add("hurdle")
    if props.get("BurrowProps") or props.get("DiggerProps"):
        tags.add("burrow")
    if props.get("SummonProps") or props.get("SpawnZombiesProps") \
            or props.get("PharaohTypes") or props.get("ImpType"):
        tags.add("summoner")
    if "camel" in str(props.get("ZombieBasedOn", "")).lower():
        tags.add("camel")
    return sorted(tags & set(ZOMBIE_TAGS))


def extract(index):
    """codename -> record, over ZombieTypes."""
    types_doc = index.group("ZombieTypes")
    props_doc = index.group("ZombieProps")
    out = {}
    if not types_doc:
        return out

    for alias, entry in types_doc.by_alias.items():
        props = index.resolve(entry.get("Properties"), types_doc)
        if props is None and props_doc:
            props = props_doc.by_alias.get(alias)
        if props is None:
            props = entry
        hp = _num(props, "Toughness")
        armor, unknown_armor = _armor_hp(index, props)
        sps = _num(props, "WalkSPS", "MoveSpeed")
        cost = _num(props, "WavePointCost")
        effective_sps = sps or DEFAULT_SPS
        missing = [f for f, v in (("toughness", hp), ("walk_sps", sps),
                                  ("wave_cost", cost)) if v is None]
        out[alias] = {
            "codename": alias,
            "hitpoints": hp,
            "armor_hp": armor or None,
            "effective_hp": (hp or 0.0) + armor,
            "walk_sps": sps,
            "cross_seconds": round(LANE_COLUMNS / effective_sps, 1),
            "wave_cost": cost,
            "eat_dps": _num(props, "EatDPS"),
            "sort": props.get("ZombieSort"),
            "based_on": entry.get("ZombieBasedOn") or props.get("ZombieBasedOn"),
            "armors": props.get("StartingArmors") or [],
            "tags": _tags(props),
            "missing": missing + (["armor:" + ",".join(unknown_armor)]
                                  if unknown_armor else []),
        }
    return out
