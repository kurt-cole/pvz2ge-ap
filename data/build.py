"""Build the whole dataset, then the site bundle.

    python data/build.py                 # structure only, or measured if a
                                         #   checkout is found automatically
    python data/build.py --game "PATH"   # point at a pvzge_web checkout
    python data/build.py --limit 2000    # read only N asset files (a smoke run)

TWO TIERS, and the artifacts always say which they are:

  STRUCTURE  buildable from this repo alone -- every level, its world, its
             stretch, the region graph and its real access rules, the side
             paths and what reveals them, the zombie threat tags, the plant
             classes. No game checkout needed.
  MEASURED   needs a checkout: wave tables, zombie HP, plant damage, level
             modules. This is what turns "Dark Ages has a Jester" into "dark22
             demands 340 HP/s across 5 lanes and a Jester answer".

Every consumer treats MEASURED as optional. A missing measurement shows as
"unmeasured" in the site, never as a zero -- a zero would rank an unmeasured
level as the easiest in the game.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import paths                                    # noqa: E402
from data.model import classify, logic, pressure, requirements  # noqa: E402

CLIENT_SRC = os.path.join(paths.REPO_ROOT, "pvz2gardendless", "build_pvzge_ap.py")
_LOC_LEVEL_RE = re.compile(r"^\s*'([^']+)'\s*:\s*'([^']+)'\s*,\s*$")


def loc_levels():
    """AP location name -> game level codename, read out of the client source.

    LOC_LEVELS is the client's own table and the only place the mapping exists;
    parsing it here rather than restating it is the same rule the rest of the
    repo follows about the client/world contract.
    """
    with open(CLIENT_SRC, "r", encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("const LOC_LEVELS = {")
    end = text.index("};", start)
    out = {}
    for line in text[start:end].splitlines()[1:]:
        m = _LOC_LEVEL_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def structure_only_zombies():
    """Threat tags with no HP, from zombie_data.py's tier keys.

    The tier key already carries the mechanic partition, so a structure-only
    run still knows which worlds field a Jester or an ice-block carrier -- it
    just cannot say how much HP that is.
    """
    from data.apworld import Z
    ZOMBIE_TIERS = Z.ZOMBIE_TIERS
    out = {}
    for tier, members in ZOMBIE_TIERS.items():
        parts = tier.split("-")
        tags = [p for p in parts[2:]] + (["water"] if "water" in parts else [])
        for cns in members:
            out[cns] = {"codename": cns, "effective_hp": None, "hitpoints": None,
                        "cross_seconds": None, "wave_cost": None,
                        "tier": tier, "tags": sorted(set(tags)), "missing": ["hp"]}
    return out


def structure_only_levels(logic_data, level_map, hazards):
    """A level record per AP location, with world hazards and no waves."""
    world_tokens = hazards["world_tokens"]
    out = {}
    for lvl in logic_data["levels"]:
        if lvl["kind"] in ("shop",):
            continue
        cns = level_map.get(lvl["name"], lvl["name"])
        tokens = list(world_tokens.get(lvl["world"], []))
        if lvl["kind"] == "dangerroom":
            tokens.append("endless")
        out[cns] = {
            "codename": cns, "selection": "chooser", "starting_sun": None,
            "sun_drop": True, "grid": {}, "modules": [],
            "tokens": sorted(set(tokens)), "zombies": [], "waves": [],
            "wave_count": 0, "total_hp": None, "total_points": None,
            "duration": 0.0,
            "source": "structure",   # NOT extracted: world-level guess only
        }
    return out


def sidepath_analysis(logic_data, pressures, level_map):
    """The steep-side-path question, answered.

    For each path: the pressure of every stage, and the MAIN-PATH LEVEL each
    stage plays like. A path whose stage 2 plays like a level twenty ahead of
    the one that reveals it is exactly the case the current flat-region model
    gets wrong -- one gate on the branch level, then a cliff.
    """
    # PROGRESSION order: the world order constants.py declares, then play
    # order inside a world. Sorting by world NAME would put Aerial Fortress
    # first and make every path report "plays like sky3".
    from data.apworld import C
    world_rank = {w: i for i, w in enumerate(C.WORLD_REGIONS)}
    main = []
    for lvl in sorted((l for l in logic_data["levels"] if l["kind"] == "level"),
                      key=lambda l: (world_rank.get(l["world"], 99), l["order"] or 0)):
        cns = level_map.get(lvl["name"], lvl["name"])
        main.append((lvl["name"], (pressures.get(cns) or {}).get("index")))

    out = []
    for path in logic_data["sidepaths"]:
        unlock = path["unlock_level"]
        unlock_index = (pressures.get(level_map.get(unlock, unlock or "")) or {}).get("index")
        stages = []
        for name in path["stages"]:
            cns = level_map.get(name, name)
            p = pressures.get(cns) or {}
            stages.append({
                "name": name,
                "index": p.get("index"),
                "peak": p.get("peak"),
                "plays_like": pressure.equivalent_level(p.get("index"), main),
                "spike_over_unlock": (round(p["index"] - unlock_index, 2)
                                      if p.get("index") is not None
                                      and unlock_index is not None else None),
            })
        spikes = [s["spike_over_unlock"] for s in stages
                  if s["spike_over_unlock"] is not None]
        out.append({
            **path,
            "unlock_index": unlock_index,
            "stages_detail": stages,
            "max_spike": max(spikes) if spikes else None,
            # The suggestion, not a change: where the HARDEST stage belongs,
            # which is not the last one listed -- stage order is AP location
            # order and a path's difficulty is not always monotonic. Gating the
            # whole flat region there would be too strict; the real fix is to
            # split the path, and this says how far the far end reaches.
            "hardest_stage": (max((s for s in stages if s["index"] is not None),
                                  key=lambda s: s["index"], default={}) or {}).get("name"),
            "suggested_deep_gate": (max((s for s in stages if s["index"] is not None),
                                        key=lambda s: s["index"],
                                        default={}) or {}).get("plays_like"),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", help="path to a pvzge_web checkout")
    ap.add_argument("--limit", type=int, help="read only N asset files")
    ap.add_argument("--no-site", action="store_true", help="skip site/bundle.js")
    args = ap.parse_args(argv)

    os.makedirs(paths.GENERATED_DIR, exist_ok=True)
    with open(paths.curated("hazards.json"), "r", encoding="utf-8") as fh:
        hazards = json.load(fh)
    with open(paths.curated("threat_answers.json"), "r", encoding="utf-8") as fh:
        answers = json.load(fh)

    logic_data = logic.build()
    level_map = loc_levels()

    game_root = paths.find_game_root(args.game)
    coverage = {"game_root": game_root, "tier": "structure"}
    if game_root:
        from data.extract import levels as ex_levels
        from data.extract import plants as ex_plants
        from data.extract import rton
        from data.extract import zombies as ex_zombies
        print(f"reading game assets from {game_root} ...", flush=True)
        index = rton.ObjectIndex().load_tree(paths.find_resource_dir(game_root),
                                             limit=args.limit)
        zombie_recs = ex_zombies.extract(index)
        plant_recs = ex_plants.extract(index)
        level_recs = ex_levels.extract(index, zombie_recs)
        coverage.update(index.report())
        coverage["tier"] = "measured"
        coverage["zombies"] = len(zombie_recs)
        coverage["plants_measured"] = len(plant_recs)
        coverage["levels_with_waves"] = sum(1 for r in level_recs.values() if r["waves"])
    else:
        print("no game checkout found -- building STRUCTURE ONLY.\n"
              "  pass --game <path to pvzge_web> to add measurements.", flush=True)
        zombie_recs = structure_only_zombies()
        plant_recs = {}
        level_recs = {}

    # Levels the extractor did not produce (or all of them, structure-only)
    # still need a record, or they vanish from every view.
    for cns, rec in structure_only_levels(logic_data, level_map, hazards).items():
        level_recs.setdefault(cns, rec)

    plants, gaps = classify.build(plant_recs)
    coverage["plant_class_gaps"] = gaps

    pressures = {cns: pressure.measure(rec, zombie_recs)
                 for cns, rec in level_recs.items()}
    baseline = pressure.calibrate(pressures)
    coverage["pressure_baseline_per_lane"] = baseline
    coverage["levels_measured"] = sum(1 for p in pressures.values() if p["measured"])

    reqs = {cns: requirements.requirement_vector(level_recs[cns], pressures[cns],
                                                 answers, plants)
            for cns in level_recs}
    coverage["unanswerable_tokens"] = sorted(
        {t for r in reqs.values() for t in r["unanswerable"]})

    sidepaths = sidepath_analysis(logic_data, pressures, level_map)

    artifacts = {
        "coverage.json":     coverage,
        "logic.json":        logic_data,
        "plants.json":       plants,
        "zombies.json":      zombie_recs,
        "levels.json":       level_recs,
        "pressure.json":     pressures,
        "requirements.json": reqs,
        "sidepaths.json":    sidepaths,
        "level_map.json":    level_map,
    }
    for name, blob in artifacts.items():
        with open(paths.generated(name), "w", encoding="utf-8") as fh:
            json.dump(blob, fh, indent=1)
        print(f"  wrote generated/{name}")

    if not args.no_site:
        bundle = {k.replace(".json", ""): v for k, v in artifacts.items()}
        bundle["answers"] = answers
        os.makedirs(paths.SITE_DIR, exist_ok=True)
        with open(os.path.join(paths.SITE_DIR, "bundle.js"), "w",
                  encoding="utf-8") as fh:
            # A .js assignment rather than a .json fetch, so the page works
            # opened straight off disk -- fetch() is blocked on file://.
            fh.write("window.DATA = ")
            json.dump(bundle, fh, separators=(",", ":"))
            fh.write(";\n")
        print(f"  wrote site/bundle.js  ({os.path.getsize(os.path.join(paths.SITE_DIR, 'bundle.js')) // 1024} KB)")

    print(f"\ntier: {coverage['tier']}   "
          f"levels measured: {coverage.get('levels_measured', 0)}/{len(level_recs)}")
    if coverage["unanswerable_tokens"]:
        print("  hard tokens NOTHING in the pool answers: "
              f"{coverage['unanswerable_tokens']}")
    if gaps:
        print(f"  plants with no class seed: {len(gaps)} -> {gaps[:6]}")
    print("\nopen data/site/index.html, or run: python data/serve.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
