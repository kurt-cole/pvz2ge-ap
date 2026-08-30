"""Offline checks for the data layer.

    python data/test_data.py

Needs no game checkout: every check is either about the vocabularies, about the
predicate language, or about this layer agreeing with the apworld. The checks
that need measurements are skipped with a note rather than passing vacuously.

The one rule worth stating outright: THIS LAYER MAY NEVER DISAGREE WITH
constants.py. It reads the apworld rather than mirroring it, and the checks
below are what keep that true -- a threat answer that names a plant generation
cannot send, or a curated flag that contradicts a derived list, is a bug here
and not a difference of opinion.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from data import paths                                        # noqa: E402
from data.apworld import C, I, Z                               # noqa: E402
from data.model import classify, logic, pressure, requirements, taxonomy  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}   {detail}")
        FAILURES.append(label)


def main():
    with open(paths.curated("threat_answers.json"), encoding="utf-8") as fh:
        answers = json.load(fh)
    with open(paths.curated("hazards.json"), encoding="utf-8") as fh:
        hazards = json.load(fh)
    plants, gaps = classify.build({})

    print("\nvocabularies")
    check("every plant classifies into the vocabularies", True)  # validate() raised or not
    check("no plant is missing a class seed", not gaps, gaps[:8])
    check("every AP plant item has a record",
          len(plants) == len({p.name for p in I.PLANT_ITEMS}))

    print("\nthreat answers")
    for token, spec in answers["tokens"].items():
        check(f"token '{token}' is in the taxonomy", token in taxonomy.TOKENS)
        check(f"token '{token}' has a severity",
              spec.get("severity") in ("hard", "soft", "flavour"))
        try:
            who = requirements.answerers(token, answers, plants)
        except ValueError as exc:
            check(f"token '{token}' predicate parses", False, str(exc))
            continue
        # A HARD token nothing answers is a level the multiworld can hand a
        # player no way through. Soft and flavour tokens are allowed to have
        # no answer -- that is what makes them soft.
        if spec["severity"] == "hard":
            check(f"hard token '{token}' has at least one answer", bool(who))

    print("\nthreat answers agree with generation")
    # Every plant a predicate can name must be a real AP item, or the rule it
    # inspires would name something no seed can contain.
    ap_names = {p.name for p in I.PLANT_ITEMS}
    for token, spec in answers["tokens"].items():
        named = _named_plants(spec["answer"])
        unknown = sorted(named - ap_names)
        check(f"'{token}' names only real AP items", not unknown, unknown)
    for name, plants_list in classify.EXPOSED_LISTS.items():
        unknown = sorted(set(plants_list) - ap_names)
        check(f"exposed list {name} is all real items", not unknown, unknown)

    print("\nthis layer matches the shipped rules")
    # The four worlds that carry an entry plant must each have a token whose
    # answer set covers the plants the rule really names. If they diverge, the
    # site is describing a rule the generator does not have.
    world_token = {"Dark Ages": "jester", "Frostbite Caves": "iceblock",
                   "Big Wave Beach": "water", "Jurassic Marsh": "raptor"}
    for world, token in world_token.items():
        rule_plants = {p for group in C.WORLD_ENTRY_PLANTS.get(world, [])
                       for p in group}
        answer_plants = set(requirements.answerers(token, answers, plants))
        missing = sorted(rule_plants - answer_plants)
        check(f"{world}: '{token}' answers cover the shipped rule", not missing,
              missing[:6])

    print("\nzombie tags match zombie_data tiers")
    tagged = {"jester": [], "iceblock": [], "air": [], "blocker": []}
    for tier, members in Z.ZOMBIE_TIERS.items():
        for tag in tagged:
            if tier.endswith("-" + tag):
                tagged[tag] += members
    for tag, members in tagged.items():
        check(f"tier tag '{tag}' has members ({len(members)})", bool(members))
        check(f"tier tag '{tag}' is a taxonomy token", tag in taxonomy.ZOMBIE_TAGS)

    print("\nlogic read-back")
    data = logic.build()
    check("every level lands in a stretch",
          all(l["stretch"] for l in data["levels"]
              if l["kind"] in ("level", "dangerroom")))
    check("every keyed world has an entrance edge",
          all(any(e["name"] == f"Enter {w}" for e in data["edges"])
              for w in C.KEYED_WORLDS))
    check("every side path with an unlock has an edge",
          all(any(e["to"] == p for e in data["edges"])
              for p in C.SIDE_PATH_UNLOCK))
    # Entrance names are load-bearing in rules.py; a graph that invented one
    # would draw a rule that does not exist.
    real = {f"Enter {w}{s}" for w in C.WORLD_REGIONS for s in C.stretch_suffixes(w)}
    named = {e["name"] for e in data["edges"] if e["name"]}
    check("no invented entrance names", named <= real, sorted(named - real)[:5])

    print("\nhazards table")
    check("every module token is in the taxonomy",
          set(hazards["module_tokens"].values()) <= set(taxonomy.TOKENS),
          sorted(set(hazards["module_tokens"].values()) - set(taxonomy.TOKENS)))
    check("every world in the hazard table is a real world",
          set(hazards["world_tokens"]) <= set(C.WORLD_REGIONS) | {"Tutorial"},
          sorted(set(hazards["world_tokens"]) - set(C.WORLD_REGIONS) - {"Tutorial"}))
    check("every world token is in the taxonomy",
          {t for ts in hazards["world_tokens"].values() for t in ts}
          <= set(taxonomy.TOKENS))

    print("\npressure model")
    stub = pressure.measure({"codename": "x", "waves": []}, {})
    check("an unmeasured level reports unmeasured, not zero",
          stub["measured"] is False and stub["peak"] is None)
    fake_z = {"z": {"effective_hp": 300.0, "cross_seconds": 30.0}}
    fake_l = {"codename": "y", "duration": 100.0, "grid": {"rows": 5},
              "tokens": [], "waves": [
                  {"index": 0, "at": 0.0, "flag": False, "zombies": {"z": 4},
                   "spawn_hp": 1200.0, "spawn_points": 0}]}
    m = pressure.measure(fake_l, fake_z)
    check("required DPS is HP over crossing time",
          abs(m["peak"] - 40.0) < 0.01, m["peak"])
    check("per-lane divides by usable rows",
          abs(m["per_lane"] - 8.0) < 0.01, m["per_lane"])

    print("\npredicate language")
    p = plants["Torchwood"]
    check("role atom", requirements.holds("role:warmth", p))
    check("banded role atom", requirements.holds("role:support>=b4", p))
    check("banded role atom rejects a lower band",
          not requirements.holds("role:support>=b5", plants["Peashooter"]))
    check("element atom", requirements.holds("element:fire", p))
    check("list atom", requirements.holds("list:FIRE_AURA_PLANTS", p))
    check("name atom", requirements.holds("name:Torchwood", p))
    check("any/all compose",
          requirements.holds({"all": ["element:fire", {"any": ["role:warmth"]}]}, p))
    try:
        requirements.holds("nonsense:thing", p)
        check("an unparsable atom raises", False)
    except ValueError:
        check("an unparsable atom raises", True)

    print("\nnon-gateable levels")
    conveyor = {"codename": "c", "selection": "conveyor", "tokens": ["graves"],
                "waves": []}
    vec = requirements.requirement_vector(conveyor, None, answers, plants)
    check("a conveyor level proposes no plant requirement",
          vec["gateable"] is False and not vec["must"])

    print(f"\n{'=' * 60}")
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED: {', '.join(FAILURES[:8])}")
        return 1
    print("ALL DATA CHECKS PASSED")
    return 0


def _named_plants(predicate):
    """Every literal plant name a predicate mentions."""
    out = set()
    if isinstance(predicate, str):
        if predicate.startswith("name:"):
            out.add(predicate[5:].strip())
    elif isinstance(predicate, dict):
        for value in predicate.values():
            for item in (value if isinstance(value, list) else [value]):
                out |= _named_plants(item)
    return out


if __name__ == "__main__":
    sys.exit(main())
