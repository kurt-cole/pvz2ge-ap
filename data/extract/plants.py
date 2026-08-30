"""Plant stats, for the supply half of the model.

Read out of `PlantTypes` -> `PlantProps`, with two supporting tables:

    ProjectileProps   the Damage a shot carries, and the flag that says the
                      Jester cannot turn it round
    PlantAlmanac      the game's own displayed DAMAGE / RECHARGE ratings,
                      used only where the sheet gives nothing

DPS IS A LOWER BOUND, and the pipeline is built around that being true rather
than around pretending otherwise. A plant whose damage lives in its behaviour
module rather than its sheet measures nothing here; `missing` says so, and
classify.py keeps that plant's curated band instead of re-banding it to the
floor. Ranking Gloom-shroom last because its sheet is quiet would be worse than
admitting we did not measure it.

Two traps this repo has already fallen into, both encoded here:

  - An almanac DAMAGE rating is a DISPLAY value, not a rate. It is recorded as
    `almanac_damage` and never used as dps.
  - `CannotBeReversedByJester` on its own is not a Jester answer. Sap-fling's
    projectile carries the flag and no Damage at all -- an unreversible shot
    that deals no damage does not answer him, it only declines to arm him. So
    jester_safe here is two conditions: the damage must REACH him, and it must
    BE damage.
"""

_DAMAGE_FIELDS = ("Damage", "ChewDamage", "ContactDamage", "ExplodeDamage",
                  "StabDamage", "SmashDamage", "ButterDamage", "SpikeDamage",
                  "BiteDamage", "BurnDamage")
_INTERVAL_FIELDS = ("ShootInterval", "AttackInterval", "ChewInterval",
                    "FireInterval", "AttackRate")
_PROJECTILE_FIELDS = ("PeaType", "ProjectileType", "PeaTypePlantfood")
_STATUS_HINTS = {
    "chill": "slow", "slow": "slow", "freeze": "freeze", "frozen": "freeze",
    "stun": "stun", "butter": "stun", "burn": "burn", "ignite": "burn",
    "poison": "poison", "hypno": "hypno", "knockback": "push",
}


def _num(obj, *fields, default=None):
    for f in fields:
        v = obj.get(f)
        if isinstance(v, (int, float)):
            return float(v)
    return default


def _projectile(index, props):
    """(name, propsdict) of the plant's FIRST/normal projectile, or (None, {}).

    The first one, deliberately: Guacodile's ordinary shot is reversible and
    only the child it leaves behind is flagged, and Iceweed's flagged
    projectile is its plant food. Checking any projectile admits both wrongly.
    """
    doc = index.group("ProjectileProps")
    for field in _PROJECTILE_FIELDS[:2]:          # not the plantfood variant
        name = props.get(field)
        if isinstance(name, str):
            data = (doc.by_alias.get(name) if doc else None) or index.resolve(name)
            if isinstance(data, dict):
                return name, data
            return name, {}
    return None, {}


def _almanac(index, alias):
    doc = index.group("PlantAlmanac")
    entry = doc.by_alias.get(alias) if doc else None
    out = {}
    for element in (entry or {}).get("Elements") or []:
        if isinstance(element, dict) and "TYPE" in element:
            out[element["TYPE"]] = element.get("VALUE")
    return out


def _status(props, projectile_props):
    blob = (repr(props) + repr(projectile_props)).lower()
    return sorted({tag for hint, tag in _STATUS_HINTS.items() if hint in blob})


def extract(index):
    """codename -> record, over PlantTypes."""
    types_doc = index.group("PlantTypes")
    props_doc = index.group("PlantProps")
    out = {}
    if not types_doc:
        return out

    for alias, entry in types_doc.by_alias.items():
        props = index.resolve(entry.get("Properties"), types_doc)
        if props is None and props_doc:
            props = props_doc.by_alias.get(alias)
        if props is None:
            # No sheet at all. Six plants are in this state and the record has
            # to SAY so -- treating it as zero damage is how Scaredy-shroom
            # ends up classified as harmless.
            out[alias] = {"codename": alias, "sun_cost": None, "recharge": None,
                          "dps": None, "burst": None, "missing": ["no sheet"],
                          "jester_safe": None, "status": [],
                          "warming_radius": None, "is_consumable": False,
                          "lifetime": None, "is_water_plant": False,
                          "almanac_damage": None, "toughness": None,
                          "projectile": None, "family": None}
            continue

        proj_name, proj = _projectile(index, props)
        almanac = _almanac(index, alias)
        interval = _num(props, *_INTERVAL_FIELDS)
        hit = _num(props, *_DAMAGE_FIELDS)
        if hit is None and proj:
            hit = _num(proj, *_DAMAGE_FIELDS)
        dps = (hit / interval) if (hit and interval) else None

        # Two conditions, both required. See the module docstring.
        if proj_name:
            jester_safe = bool(proj.get("CannotBeReversedByJester")) and bool(hit)
        else:
            jester_safe = bool(hit)

        missing = [f for f, v in (("sun_cost", _num(props, "SunCost")),
                                  ("dps", dps)) if v is None]
        out[alias] = {
            "codename": alias,
            "sun_cost": _num(props, "SunCost", "Cost"),
            "recharge": _num(props, "Cooldown", "PacketCooldown", "Recharge"),
            "toughness": _num(props, "Toughness"),
            "hit": hit,
            "interval": interval,
            "dps": round(dps, 2) if dps else None,
            "burst": hit,
            "almanac_damage": almanac.get("DAMAGE"),
            "family": props.get("Family"),
            "projectile": proj_name,
            "warming_radius": _num(props, "WarmingRadius"),
            "is_consumable": bool(props.get("IsConsumable")),
            "lifetime": _num(props, "Lifetime"),
            "is_water_plant": bool(props.get("IsZenGardenWaterPlant")
                                   or props.get("IsAquatic")),
            "jester_safe": jester_safe,
            "status": _status(props, proj),
            "missing": missing,
        }
    return out
