"""The apworld's CURRENT logic, read out of the apworld itself.

Nothing here is a second copy of anything: constants.py and locations.py are
imported and asked. That is deliberate and it is the point -- the site's job is
to show what generation really does, and a hand-kept mirror of the rules would
be wrong within a week.

What it produces:

  levels[]     every AP location that is a level, with the world, the stretch
               it lands in, its play order, and whether it is a goal level
  regions[]    the region graph rules.py builds, as nodes and edges, each edge
               carrying the requirement text it is actually gated on
  sidepaths[]  each path, its owning world, the level that reveals it, and its
               own ordered stages

Rule text is assembled from the same tables rules.py reads. Where a rule is
per-slot (the cheap-attacker draw, the Jester draw) the edge says so and names
the pool it is drawn from, because there is no single answer.
"""
from ..apworld import C, L   # imported offline through test/apstub.py


def _world_of_region(region):
    for world, regions in C.WORLD_REGIONS.items():
        if region in regions:
            return world
    return region


def build():
    world_of = {}
    for loc in L.ALL_LOCATIONS:
        world_of[loc.name] = _world_of_region(loc.region)

    # Stretch assignment, exactly as regions.py does it: ask locations.py.
    stretch_of, order_of = {}, {}
    for world, regions in C.WORLD_REGIONS.items():
        names = [l.name for l in L.ALL_LOCATIONS if l.region in regions]
        early = C.EGYPT_SUN_CUT if world == "Ancient Egypt" else None
        suffixes = C.stretch_suffixes(world)
        for suffix, bucket in zip(suffixes, L.world_stretches(names, early)):
            for name in bucket:
                stretch_of[name] = f"{world}{suffix}"
    for loc in L.ALL_LOCATIONS:
        order_of[loc.name] = L._play_order(loc.name)

    goal_sets = {
        "world_key":   set(L.WORLD_KEY_LOCS),
        "zomboss":     set(L.WORLD_ZOMBOSS_LOCS),
        "completion":  set(L.WORLD_COMPLETION_LOCS),
    }

    levels = []
    for loc in L.ALL_LOCATIONS:
        region = loc.region
        is_side = region in set(C.SIDE_PATH_REGIONS)
        levels.append({
            "name": loc.name,
            "region": region,
            "world": world_of[loc.name],
            # Tutorial and the side paths are single regions with no stretch
            # cut of their own, so they ARE their stretch. Falling back to the
            # region keeps every location in exactly one node of the graph.
            "stretch": stretch_of.get(loc.name, region),
            "order": order_of.get(loc.name),
            "kind": ("shop" if loc.is_shop else
                     "victory" if loc.is_victory else
                     "sidepath" if is_side else
                     "dangerroom" if loc.name in C.DANGER_ROOM_LOCATIONS else
                     "level"),
            "goal_for": sorted(g for g, s in goal_sets.items() if loc.name in s),
            "unreachable": loc.name in C.UNREACHABLE_LOCATIONS,
        })

    edges = _edges()
    sidepaths = _sidepaths(levels)
    return {
        "levels": levels,
        "edges": edges,
        "sidepaths": sidepaths,
        "worlds": list(C.WORLD_REGIONS),
        "keyed_worlds": list(C.KEYED_WORLDS),
        "goal_types": {"world_key": C.GOAL_WORLD_KEY, "zomboss": C.GOAL_ZOMBOSS,
                       "completion": C.GOAL_COMPLETION},
    }


def _req(kind, text, plants=(), per_slot=False, source=""):
    return {"kind": kind, "text": text, "plants": sorted(plants),
            "per_slot": per_slot, "source": source}


def _edges():
    """The region graph with the requirement each entrance really carries."""
    edges = [{"from": "Menu", "to": "Tutorial", "name": None, "requires": []},
             {"from": "Tutorial", "to": "Ancient Egypt", "name": None,
              "requires": []}]

    sun = _req("plants", "a sun producer", C.SUN_PRODUCER_PLANTS,
               source="rules.py sun rule")
    for suffix in C.EGYPT_STRETCH_PLANTS:
        name = f"Ancient Egypt{suffix}"
        reqs = [sun]
        need = C.progressive_need("Ancient Egypt", suffix)
        if need:
            reqs.append(_req("item", f"{C.progressive_item_name('Ancient Egypt')} x{need}",
                             source="rules.py progressive rule"))
        for group in C.STRETCH_ENTRY_PLANTS.get("Ancient Egypt", {}).get(suffix, []):
            reqs.append(_req("plants", "one of", group, source="STRETCH_ENTRY_PLANTS"))
        edges.append({"from": "Ancient Egypt" if suffix else "Tutorial",
                      "to": name, "name": f"Enter {name}", "requires": reqs})

    for world in C.KEYED_WORLDS:
        for i, suffix in enumerate(C.stretch_suffixes(world)):
            reqs = []
            need = C.progressive_need(world, suffix)
            if need:
                reqs.append(_req("item", f"{C.progressive_item_name(world)} x{need}",
                                 source="rules.py progressive rule"))
            if not suffix:
                reqs.append(sun)
                for group in C.WORLD_ENTRY_PLANTS.get(world, []):
                    per_slot = len(group) > 3
                    reqs.append(_req("plants",
                                     "one of (one drawn per slot)" if per_slot else "one of",
                                     group, per_slot=per_slot,
                                     source="WORLD_ENTRY_PLANTS"))
            for group in C.STRETCH_ENTRY_PLANTS.get(world, {}).get(suffix, []):
                reqs.append(_req("plants", "one of", group,
                                 source="STRETCH_ENTRY_PLANTS"))
            src = "Tutorial" if i == 0 else f"{world}{C.stretch_suffixes(world)[i - 1]}"
            edges.append({"from": src, "to": f"{world}{suffix}",
                          "name": f"Enter {world}{suffix}", "requires": reqs})

    for path, unlock in C.SIDE_PATH_UNLOCK.items():
        edges.append({"from": C.SIDE_PATH_WORLD.get(path, "Tutorial"), "to": path,
                      "name": None,
                      "requires": [_req("location", f"clear {unlock}",
                                        source="SIDE_PATH_UNLOCK")]})
    for path, parent in C.SIDE_PATH_CHAIN.items():
        edges.append({"from": parent, "to": path, "name": None,
                      "requires": [_req("region", f"reach {parent}",
                                        source="SIDE_PATH_CHAIN")]})
    return edges


def _sidepaths(levels):
    by_region = {}
    for lvl in levels:
        if lvl["kind"] == "sidepath":
            by_region.setdefault(lvl["region"], []).append(lvl["name"])
    out = []
    for path in C.SIDE_PATH_REGIONS:
        out.append({
            "name": path,
            "world": C.SIDE_PATH_WORLD.get(path),
            "unlock_level": C.SIDE_PATH_UNLOCK.get(path),
            "chained_from": C.SIDE_PATH_CHAIN.get(path),
            "stages": by_region.get(path, []),
        })
    return out
