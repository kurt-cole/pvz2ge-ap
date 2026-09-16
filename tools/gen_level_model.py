#!/usr/bin/env python3
"""Extract the wave-level model the budget zombie roll works from.

    python tools/gen_level_model.py --game-root ~/pvzge_ap_build/PVZGE-Electron

Writes pvz2gardendless/level_model.py: for every level the world has a
location for, what spawns, in which wave, from which source, and how many.
pvz2gardendless/zombie_roll.py rolls from it.

WHY NOT zombie_balance.json

That extract is a roster: {codename: count} per level. The budget roll needs
more than a roster. It has to know which spawn GROUP a zombie belongs to (a
jittered wave list, a spider rain, a raiding party), which wave that group
lands in, and whether its count is a list length or a number in a field. It
also has to price graves and see dino events. This file carries all of that.

It also reads levels the older tools never saw. 49 tracked levels (egypt1,
the random_* and bank_theft* sets, epic_beghouled*, shootingstarfruit* and
others) are stored inside Cocos pack files rather than as their own asset, and
Bundle.objects() cannot open a pack. PackedLevels below indexes them by name.

SCHEMA

LEVEL_MODEL["levels"][level id] =
    world       level id prefix ("egypt", "lod_", ...)
    stage       LevelDefinition StageModule name, or ""
    waves       WaveCount, or the length of Waves
    bespoke     a module matches BESPOKE_MODULES (the client skips the level)
    generated   waves come from a runtime generator (WaveGeneratorProperties
                or a DangerRoom* designer), so nothing static describes them
    own_plants  seed chooser and no conveyor
    tides       carries a TidalChangeWaveActionProps
    planks      PiratePlankProperties PlankRows, [] when the level has none
    sun         {sky, no_producers, max_sun}: the level's sun economy
    groups      [{w, k, id, z: [[codename, count]], f?, rows?, grid?, rep?}]
                w     1-based wave index
                k     source kind, see KINDS
                id    the object's alias in the level
                z     who spawns and how many
                f     for a count-field source, the field that holds the count
                rows  distinct fixed rows, when every entry names one
                grid  grid item types a grave spawner releases from
                rep   WaveSchedulerProps Repeat.Max around the group, if any
    dynamic     [{w, p, inc, pool}] from WaveManagerModuleProperties
    dinos       [[wave, dino type, row]]
    portals     [[wave, portal type]]
    graves      {"initial": {type: n}, "random_initial": n,
                 "spawned": [[wave, {type: n}]]}
    events      other wave objclasses, for reference

LEVEL_MODEL["zombies"][codename] = {hp, cost, tier, excluded}
LEVEL_MODEL["grave_hp"][grid item type] = Toughness
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from gen_zombie_tiers import (BESPOKE_MODULES, RTID, Bundle, Zombies,  # noqa: E402
                              alias_map, find_table)
from gen_plant_power import tracked_levels  # noqa: E402

OUT_PY = os.path.join(REPO, "pvz2gardendless", "level_model.py")

# objclass -> kind. Every class here spawns zombies; the extraction for each is
# in Level._group.
KINDS = {
    "SpawnZombiesJitteredWaveActionProps": "jittered",
    "SpawnZombiesFromGroundSpawnerProps": "ground",
    "StormZombieSpawnerProps": "storm",
    "QigongStrikeWaveActionProps": "qigong",
    "RaidingPartyZombieSpawnerProps": "raid",
    "BeachStageEventZombieSpawnerProps": "beach",
    "SpiderRainZombieSpawnerProps": "spider",
    "ParachuteRainZombieSpawnerProps": "parachute",
    "DropShipZombieSpawnerProps": "dropship",
    "SpawnZombiesFromGridItemSpawnerProps": "grave_spawn",
}

# A raiding party with no ZombieType. 61 of 165 omit it. The game's own preview
# (WaveEventsStatistic) reads `n.ZombieType ? n.ZombieType : "swashbuckler"`.
RAID_DEFAULT = "swashbuckler"

GENERATORS = re.compile(r"^(WaveGeneratorProperties|DangerRoom\w+)$")


def rt(value):
    """RTID(name@table) -> name; a bare string passes through."""
    if not isinstance(value, str):
        return None
    match = RTID.match(value.strip())
    return match.group(1) if match else value.strip()


def as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# ── reading levels, packed ones included ─────────────────────────────────────

class PackedLevels:
    """{level id: objects} for levels stored inside Cocos pack files."""

    def __init__(self, root):
        with open(os.path.join(root, "config.json"), encoding="utf8") as fh:
            cfg = json.load(fh)
        paths = {int(k): v[0] for k, v in cfg["paths"].items()}
        self.levels = {}
        for pack, members in cfg.get("packs", {}).items():
            if not any((paths.get(i) or "").startswith("levels/") for i in members):
                continue
            path = os.path.join(root, "import", pack[:2], pack + ".json")
            with open(path, encoding="utf8") as fh:
                self._walk(json.load(fh))

    def _walk(self, node):
        if isinstance(node, list):
            if (len(node) >= 3 and isinstance(node[1], str)
                    and isinstance(node[2], dict) and "objects" in node[2]):
                self.levels[node[1]] = node[2]["objects"]
            for item in node:
                self._walk(item)


def level_objects(bundle, packed, level_id):
    uuid = bundle.by_path.get("levels/" + level_id)
    objects = []
    if uuid:
        try:
            objects = bundle.objects(uuid)
        except (OSError, ValueError):
            objects = []
    return objects or packed.levels.get(level_id, [])


# ── one level ────────────────────────────────────────────────────────────────

class Level:
    def __init__(self, level_id, objects):
        self.id = level_id
        self.objects = objects
        self.by_alias = {}
        for obj in objects:
            for alias in obj.get("aliases") or []:
                self.by_alias[alias] = obj
        self.groups, self.dinos, self.portals = [], [], []
        self.spawned_graves, self.events = [], Counter()

    def of_class(self, name):
        return [o for o in self.objects if o.get("objclass") == name]

    def data(self, name):
        found = self.of_class(name)
        return (found[0].get("objdata") or {}) if found else {}

    def manager(self):
        module = self.data("WaveManagerModuleProperties")
        target = rt(module.get("WaveManagerProps"))
        obj = self.by_alias.get(target) if target else None
        if obj and obj.get("objclass") == "WaveManagerProperties":
            return obj.get("objdata") or {}
        return self.data("WaveManagerProperties")

    def build(self):
        classes = [o.get("objclass") or "" for o in self.objects]
        definition = self.data("LevelDefinition")
        manager = self.manager()
        waves = manager.get("Waves") or []
        count = manager.get("WaveCount")
        seedbank = self.data("SeedBankProperties")
        conveyor = any("Conveyor" in str(rt(m))
                       for m in definition.get("Modules") or [])
        for index, wave in enumerate(waves):
            if isinstance(wave, list):
                for ref in wave:
                    self._event(index + 1, ref, None, set())
        return {
            "world": re.match(r"[a-z]+_?", self.id).group(0),
            "stage": rt(definition.get("StageModule")) or "",
            # module_SetWaveProperties runs `WaveCount = Waves.length`: the
            # authored WaveCount is overwritten, and sky3 (12 listed, 8 authored)
            # plays all 12.
            "waves": len(waves) or (count if isinstance(count, int) else 0),
            "bespoke": any(BESPOKE_MODULES.search(c) for c in classes),
            "generated": any(GENERATORS.match(c) for c in classes),
            "own_plants": seedbank.get("SelectionMethod") == "chooser" and not conveyor,
            "tides": "TidalChangeWaveActionProps" in classes,
            # Pirate Seas lanes that start with planks; the rest are open sea.
            # [data] the game can add or remove planks mid-level.
            "planks": sorted(self.data("PiratePlankProperties").get("PlankRows") or []),
            "sun": self._sun(definition, seedbank),
            "groups": self.groups,
            "dynamic": self._dynamic(),
            "dinos": self.dinos,
            "portals": self.portals,
            "graves": self._graves(),
            "events": dict(sorted(self.events.items())),
        }

    def _sun(self, definition, seedbank):
        """The level's sun economy, as the budget logic prices plants against it.

        sky    sky sun falls: a SunDropper module, no SuppressSunSpawn, and not a
               ListenToLawn dropper on a night stage (module_SetSunDropper stops
               only that combination at night)
        no_producers   the seed bank bans sun producers
        max_sun        the smallest StarChallengeSunUsedProps cap, 0 for none
        """
        def truthy(value):
            return value is True or str(value).strip().lower() == "true"

        modules = [str(rt(m)) for m in definition.get("Modules") or []]
        dropper = [m for m in modules if "SunDropper" in m]
        night = "Night" in (rt(definition.get("StageModule")) or "")
        listens = any("ListenToLawn" in m for m in dropper)
        caps = [as_int((o.get("objdata") or {}).get("MaximumSun"))
                for o in self.of_class("StarChallengeSunUsedProps")]
        caps = [c for c in caps if c > 0]
        return {
            "sky": bool(dropper) and not truthy(definition.get("SuppressSunSpawn"))
                   and not (listens and night),
            "no_producers": truthy(seedbank.get("ExcludeListSunProducers")),
            "max_sun": min(caps) if caps else 0,
        }

    def _event(self, wave, ref, repeat, seen):
        alias = rt(ref)
        if not alias or alias in seen:
            return
        obj = self.by_alias.get(alias)
        if obj is None:
            return
        seen = seen | {alias}
        cls = obj.get("objclass") or ""
        data = obj.get("objdata") or {}
        if cls == "WaveSchedulerProps":
            rep = as_int((data.get("Repeat") or {}).get("Max"), 1)
            for inner in data.get("Events") or []:
                self._event(wave, inner, rep, seen)
            return
        if cls in KINDS:
            group = self._group(KINDS[cls], alias, data)
            if group["z"]:
                group = {"w": wave, **group}
                if repeat and repeat > 1:
                    group["rep"] = repeat
                self.groups.append(group)
            return
        if cls == "DinoWaveActionProps":
            self.dinos.append([wave, data.get("DinoType"), as_int(data.get("DinoRow"), -1)])
        elif cls == "SpawnModernPortalsWaveActionProps":
            self.portals.append([wave, data.get("PortalType")])
        elif cls == "SpawnGravestonesWaveActionProps":
            self.spawned_graves.append([wave, self._grave_pool(data)])
        else:
            self.events[cls] += 1

    @staticmethod
    def _list_entries(entries, key="Type"):
        counts = Counter()
        rows = set()
        all_rows = bool(entries)
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            name = rt(entry.get(key))
            if not name:
                continue
            counts[name] += 1
            if "Row" in entry and str(entry["Row"]).strip().isdigit():
                rows.add(int(str(entry["Row"]).strip()))
            else:
                all_rows = False
        return counts, (sorted(rows) if all_rows and rows else None)

    def _group(self, kind, alias, data):
        out = {"k": kind, "id": alias}
        if kind in ("jittered", "ground", "storm", "grave_spawn", "qigong"):
            counts, rows = self._list_entries(data.get("Zombies"))
            out["z"] = sorted([n, c] for n, c in counts.items())
            if rows is not None:
                out["rows"] = rows
            if kind == "grave_spawn":
                out["grid"] = sorted(rt(t) for t in data.get("GridTypes") or [])
        elif kind == "raid":
            name = rt(data.get("ZombieType")) or RAID_DEFAULT
            out["z"] = [[name, as_int(data.get("SwashbucklerCount"))]]
            out["f"], out["p"] = "SwashbucklerCount", name
        elif kind == "beach":
            out["z"] = [[data.get("ZombieName"), as_int(data.get("ZombieCount"))]]
            out["f"], out["p"] = "ZombieCount", data.get("ZombieName")
        elif kind in ("spider", "parachute"):
            primary = data.get("SpiderZombieName")
            out["z"] = [[primary, as_int(data.get("SpiderCount"))]] if primary else []
            if kind == "parachute":
                # What each pilot carries down. Kept apart from the primary
                # entry: only the primary's type and count live in fields.
                brought, _ = self._list_entries(data.get("ZombiesToBringWith"))
                out["bring"] = sorted([n, c] for n, c in brought.items())
            out["f"], out["p"] = "SpiderCount", primary
        elif kind == "dropship":
            shifted = data.get("DropShipShiftedProperties") or {}
            imps = shifted.get("ImpCount") or {}
            out["z"] = [[data.get("DropShipType"), 1],
                        [shifted.get("ImpType"), as_int(imps.get("Max"))]]
            out["z"] = [e for e in out["z"] if e[0]]
            out["f"] = "DropShipShiftedProperties.ImpCount"
        out["z"] = [e for e in out.get("z", []) if e[1] > 0]
        return out

    def _dynamic(self):
        out = []
        module = self.data("WaveManagerModuleProperties")
        for entry in module.get("DynamicZombies") or []:
            pool = [rt(z) for z in entry.get("ZombiePool") or []]
            out.append({
                "w": as_int(entry.get("StartingWave"), 0),
                "p": as_int(entry.get("StartingPoints"), 0),
                "inc": as_int(entry.get("PointIncrementPerWave"), 0),
                "pool": [z for z in pool if z],
            })
        return out

    @staticmethod
    def _grave_pool(data):
        pool = Counter()
        for entry in data.get("GravestonePool") or []:
            if isinstance(entry, dict) and rt(entry.get("Type")):
                pool[rt(entry["Type"])] += as_int(entry.get("Count"))
        # 18 objects state their pool as RTID-named fields instead of a list.
        for key, value in data.items():
            if key.startswith("RTID("):
                pool[rt(key)] += as_int(value)
        return {k: v for k, v in sorted(pool.items()) if v > 0}

    def _graves(self):
        initial = Counter()
        random_initial = 0
        for props in self.of_class("GravestoneProperties"):
            data = props.get("objdata") or {}
            for entry in data.get("ForceSpawnData") or []:
                if isinstance(entry, dict) and entry.get("TypeName"):
                    initial[entry["TypeName"]] += 1
            random_initial += as_int(data.get("GravestoneCount"))
        return {
            "initial": dict(sorted(initial.items())),
            "random_initial": random_initial,
            "spawned": [s for s in self.spawned_graves if s[1]],
        }


# ── output ───────────────────────────────────────────────────────────────────

HEADER = '''"""
PvZ2 Gardendless: the wave-level model for the budget zombie roll.

GENERATED by tools/gen_level_model.py from {game}. Do not hand edit; rerun the
generator against a game checkout. The schema is in that tool's docstring, and
pvz2gardendless/zombie_roll.py is what reads it.

{summary}

The model is zlib-compressed JSON in base64, because as plain JSON it is
about 1.6 MB of repeated keys. Read it with load(), never by parsing _PACKED.
"""

import base64
import json
import zlib
from typing import Any, Dict

GAME_DATA_VERSION = {version!r}

_PACKED = """
'''

FOOTER = '''"""

_CACHE: Dict[str, Any] = {}


def load() -> Dict[str, Any]:
    """The model, decoded once. Only budget mode pays for this."""
    if not _CACHE:
        raw = zlib.decompress(base64.b64decode("".join(_PACKED.split())))
        _CACHE.update(json.loads(raw.decode("utf8")))
    return _CACHE
'''


def game_version(root):
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-root", required=True,
                    help="a PVZGE-Electron checkout, or its "
                         "pvzge_web/docs/assets/resources directory")
    ap.add_argument("--dry-run", action="store_true", help="write nothing")
    args = ap.parse_args()

    root = os.path.expanduser(args.game_root)
    if not os.path.isdir(os.path.join(root, "import")):
        guess = os.path.join(root, "pvzge_web", "docs", "assets", "resources")
        if not os.path.isdir(os.path.join(guess, "import")):
            raise SystemExit(f"no resources bundle under {root}")
        root = guess
    version = game_version(root)
    print(f"reading {root} ({version or 'unknown version'})")

    bundle = Bundle(root)
    packed = PackedLevels(root)
    zombies = Zombies(find_table(root, "ZombieTypes"),
                      find_table(root, "ZombieProps"),
                      find_table(root, "ArmorProps"))
    tombstones = alias_map(find_table(root, "TombstoneProps"))
    grid_types = alias_map(find_table(root, "GridItemTypes"))

    levels, missing = {}, []
    for level_id in sorted(tracked_levels()):
        objects = level_objects(bundle, packed, level_id)
        if not objects:
            missing.append(level_id)
            continue
        levels[level_id] = Level(level_id, objects).build()

    names, grave_types = set(), set()
    for level in levels.values():
        for group in level["groups"]:
            names.update(n for n, _ in group["z"])
            grave_types.update(group.get("grid", []))
        for entry in level["dynamic"]:
            names.update(entry["pool"])
        grave_types.update(level["graves"]["initial"])
        for _, pool in level["graves"]["spawned"]:
            grave_types.update(pool)

    table = {}
    for name in sorted(names):
        if name not in zombies.types:
            table[name] = {"hp": 0, "cost": 0, "tier": "", "excluded": "unknown"}
            continue
        reason = zombies.excluded(name)
        table[name] = {"hp": zombies.hp(name), "cost": zombies.cost(name),
                       "tier": "" if reason else zombies.tier(name),
                       "excluded": reason}
    # A grid item type names its sheet through GridItemTypes (`gravestone` is
    # gravestone_tutorial's). Sap, rails, sliders and tiles share the grid item
    # system but resolve to TileProps or TileLiquidProps: not graves, not priced.
    grave_hp, not_graves = {}, []
    for t in sorted(grave_types):
        sheet = rt((grid_types.get(t) or {}).get("Properties")) or t
        props = tombstones.get(sheet) or tombstones.get(t)
        if props is None:
            not_graves.append(t)
            continue
        grave_hp[t] = as_int(props.get("Toughness"))

    model = {"game": version, "levels": levels, "zombies": table, "grave_hp": grave_hp}
    raw = json.dumps(model, sort_keys=True, separators=(",", ":"))
    kinds = Counter(g["k"] for lv in levels.values() for g in lv["groups"])
    summary = (f"{len(levels)} tracked levels ({sum(lv['bespoke'] for lv in levels.values())} "
               f"bespoke, {sum(lv['generated'] for lv in levels.values())} generated at "
               f"runtime), {sum(kinds.values())} spawn groups, "
               f"{sum(len(lv['dinos']) for lv in levels.values())} dino events,\n"
               f"{len(table)} codenames, {len(grave_hp)} grave types. Groups by kind: "
               + ", ".join(f"{k} {n}" for k, n in kinds.most_common()) + ".")
    print("  " + summary.replace("\n", "\n  "))
    if missing:
        print(f"  {len(missing)} tracked levels have no data: {missing}")
    if not_graves:
        print(f"  grid item types that are not graves (unpriced): {not_graves}")
    packed_model = base64.b64encode(zlib.compress(raw.encode("utf8"), 9)).decode("ascii")
    print(f"  {len(raw) / 1024:.0f} KB of model, {len(packed_model) / 1024:.0f} KB embedded")

    if args.dry_run:
        return 0
    with open(OUT_PY, "w", encoding="utf8") as fh:
        fh.write(HEADER.format(game=f"game data {version}" if version else "game data",
                               summary=summary, version=version))
        for start in range(0, len(packed_model), 100):
            fh.write(packed_model[start:start + 100] + "\n")
        fh.write(FOOTER)
    print(f"wrote {os.path.relpath(OUT_PY, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
