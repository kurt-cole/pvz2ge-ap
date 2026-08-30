"""Build the plant records: curated seed, overwritten by anything measurable.

Precedence, strongest first:

  1. constants.py's DERIVED lists. They are what generation actually reads, so
     if this file disagreed with them the site would be lying about the logic.
     A flag that constants.py can decide is never taken from anywhere else.
  2. Extracted game stats, when a checkout is available: sun cost, recharge,
     dps, burst, warming radius, jester safety, aquatic-ness.
  3. curated/plant_classes.json, for elements and for every role band the
     numbers cannot decide.

Every field carries its provenance, so the site can show a curated band and a
derived one differently and nobody mistakes an opinion for a measurement.
"""
import json

from . import taxonomy
from ..apworld import C
from ..paths import curated

# constants.py lists a threat_answers.json predicate may name with "list:NAME".
# Only DERIVED lists are exposed: naming a curated one would let this side
# claim generation asks for something it does not.
EXPOSED_LISTS = {
    "SUN_PRODUCER_PLANTS":   C.SUN_PRODUCER_PLANTS,
    "CHEAP_ATTACKER_PLANTS": C.CHEAP_ATTACKER_PLANTS,
    "JESTER_COUNTER_PLANTS": C.JESTER_COUNTER_PLANTS,
    "FIRE_AURA_PLANTS":      C.FIRE_AURA_PLANTS,
    "GRAVE_CLEAR_PLANTS":    C.GRAVE_CLEAR_PLANTS,
    "SINGLE_USE_PLANTS":     C.SINGLE_USE_PLANTS,
    "NON_DAMAGING_PLANTS":   C.NON_DAMAGING_PLANTS,
    "STARTER_PLANTS":        C.STARTER_PLANTS,
}

# AP item name -> game codename. Only where the obvious squash-and-lowercase
# rule fails; everything else is derived, so this stays short.
NAME_TO_CNS = {
    "A.K.E.E.": "akee", "E.M. Peach": "empea", "Jack O' Lantern": "jackolantern",
    "Melon-Pult": "melonpult", "Cherry Bomb": "cherry_bomb",
    "Iceberg Lettuce": "iceburg", "Shooting Starfruit": "shootingstarfruit",
    "Primal Potato Mine": "primalpotatomine", "Cantaloupe-pult": "cantaloupe",
    "Apple Mortar": "applemortar", "Goo Peashooter": "poisonpeashooter",
    "Banana Launcher": "banana", "Flower Pot": "floawerPot",
}


def codename(name):
    return NAME_TO_CNS.get(name) or "".join(
        ch for ch in name.lower() if ch.isalnum())


def _parse_spec(spec):
    parts = [p.strip() for p in spec.split(";")]
    parts += [""] * (3 - len(parts))
    elements = [e.strip() for e in parts[0].split(",") if e.strip()]
    roles = {}
    for chunk in parts[1].split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        role, _, band = chunk.partition(":")
        roles[role.strip()] = band.strip() or "b3"
    flags = [f.strip() for f in parts[2].split(",") if f.strip()]
    return elements, roles, flags


def _derived_flags(name):
    """Flags constants.py already decides. Nothing else may set these."""
    flags = set()
    if name in set(C.JESTER_COUNTER_PLANTS):
        flags.add("jester_safe")
    if name in set(C.SINGLE_USE_PLANTS):
        flags.add("consumable")
    if name in {"Ghost Pepper"}:          # Lifetime, not IsConsumable
        flags.add("timed")
    if name in {"Scaredy-shroom", "Vamporcini", "Skyshooter"}:
        flags.add("no_data")
    return flags


def _reband(records, extracted):
    """Re-band the DPS-ish roles against measured numbers, where we have them.

    Quintiles of the measured distribution, so a band keeps meaning the same
    thing relative to the roster after a balance patch. Plants the extractor
    could not measure keep their curated band and say so.
    """
    dps_roles = ("dps_single", "dps_aoe", "dps_pierce", "dps_lob", "burst")
    for role in dps_roles:
        field = "burst" if role == "burst" else "dps"
        values = sorted(v for r in records.values()
                        if role in r["roles"]
                        for v in [(extracted.get(r["cns"]) or {}).get(field)]
                        if isinstance(v, (int, float)) and v > 0)
        if len(values) < 8:
            continue  # too little measured to make quintiles mean anything
        cuts = [values[int(len(values) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
        for rec in records.values():
            if role not in rec["roles"]:
                continue
            val = (extracted.get(rec["cns"]) or {}).get(field)
            if isinstance(val, (int, float)) and val > 0:
                rec["roles"][role] = taxonomy.band_of(val, cuts)
                rec["provenance"][f"role:{role}"] = "derived"


def build(extracted_plants=None):
    """name -> plant record. `extracted_plants` may be None or empty."""
    extracted = extracted_plants or {}
    with open(curated("plant_classes.json"), "r", encoding="utf-8") as fh:
        seed = json.load(fh)["plants"]

    from ..apworld import I
    ap_names = [p.name for p in I.PLANT_ITEMS]

    records = {}
    for name in ap_names:
        spec = seed.get(name)
        elements, roles, flags = _parse_spec(spec) if spec else ([], {}, [])
        prov = {"elements": "curated" if spec else "missing"}
        for role in roles:
            prov[f"role:{role}"] = "curated"

        cns = codename(name)
        stats = extracted.get(cns) or {}
        flag_set = set(flags) | _derived_flags(name)
        if stats.get("is_water_plant"):
            flag_set.add("aquatic_only")
        if stats.get("warming_radius"):
            roles.setdefault("warmth", "b4")
            prov["role:warmth"] = "derived"
        if stats:
            prov["jester_safe"] = "derived"
            if stats.get("jester_safe"):
                flag_set.add("jester_safe")

        rec = {
            "name": name,
            "cns": cns,
            "elements": elements,
            "roles": roles,
            "flags": sorted(flag_set),
            "sun_cost": stats.get("sun_cost"),
            "recharge": stats.get("recharge"),
            "dps": stats.get("dps"),
            "burst": stats.get("burst"),
            "measured": bool(stats),
            "provenance": prov,
            "ap_lists": sorted(k for k, v in EXPOSED_LISTS.items() if name in set(v)),
        }
        taxonomy.validate(rec)
        records[name] = rec

    _reband(records, extracted)

    # A plant with no seed entry is a real gap, not a shrug: it can answer no
    # threat and satisfy no requirement, so it would quietly vanish from every
    # candidate set. Reported rather than raised so a game update that adds a
    # plant does not break the build.
    gaps = sorted(n for n, r in records.items() if not r["elements"])
    return records, gaps
