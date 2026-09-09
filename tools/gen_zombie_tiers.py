#!/usr/bin/env python3
"""Regenerate the zombie swap tiers from the game's own data.

    python tools/gen_zombie_tiers.py --game-root ~/pvzge_ap_build/PVZGE-Electron

Writes two files:

    pvz2gardendless/zombie_data.py   the tier table, the HP table and the
                                     exclusion lists the world ships
    test/data/zombie_balance.json    an offline extract -- every shipped
                                     level's zombie roster plus each zombie's
                                     cost and HP -- that test/balance_test.py
                                     replays the client's roll against

Nothing else reads the game source, and neither generation nor the test suite
needs a checkout: this script is the one door between the two, and both of its
outputs are committed.

WHAT IS READ

Three tables out of the Cocos asset bundle, found through resources/config.json
rather than by hardcoding UUIDs, so a game update moves them without breaking
this:

    ZombieTypes    codename -> Properties RTID
    ZombieProps    the properties every decision below is made from
    ArmorProps     the toughness a StartingArmors entry adds
    levels/*       every shipped level, for the rosters and the bespoke flag

HOW A TIER KEY IS BUILT

Every axis is a property the game states outright. See ZOMBIE_RANDO_DEV.md for
why each one is there; in short, a swap may only trade zombies that cost the
same, die in the same lane, take about the same killing, and need the same
plant to answer them.

    t{1..5}          WavePointCost band -- the game's own price
    land | water     LivesInDeepWater: a land zombie drowns in a deep lane
    garg             ZombieSort == Gargantuar
    threat tags      jester / iceblock / air / blocker / shield / summon --
                     mechanics that need a specific plant or that field extra
                     zombies, partitioned so a shuffle can neither create nor
                     destroy one
    h{n}             effective HP band, floor(log(hp) / log(HP_BAND))

WHAT IS DROPPED

A dropped codename has no tier, and the client reads "no tier" as "leave this
one exactly as the level had it" -- so a level that ships one still gets it,
and no other level can gain one. Zomboss and the camels were already dropped
(see the module docstring this writes); this adds three families that were
being traded as though they were ordinary walkers.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Geometric width of an HP band. 1.35 caps the intra-tier HP ratio at 1.33
# while still leaving 90% of the table somebody to trade with; 1.75 buys 2%
# more swappability for a 1.67x spread, and tighter bands start stranding
# zombies alone in a tier. See ZOMBIE_RANDO_DEV.md.
HP_BAND = 1.35

# Levels a module drives structurally rather than merely spawning from. The
# client applies this same regex to the level's own object list at runtime;
# it is repeated here only to mark the rosters the balance extract must not
# hold the shuffle responsible for.
BESPOKE_MODULES = re.compile(r"Minigame|Beghouled|Rhythm")

RTID = re.compile(r"^RTID\(([^@()]+)@([^()]*)\)$")


# ── reading the bundle ───────────────────────────────────────────────────────

BASE64_KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64 = {c: i for i, c in enumerate(BASE64_KEYS)}
_HEX = "0123456789abcdef"


def decode_uuid(compressed: str) -> str:
    """Cocos' compressed asset UUID -> the dashed one the file is named by."""
    if len(compressed) != 22:
        return compressed
    out = [compressed[0], compressed[1]]
    for i in range(2, 22, 2):
        lhs, rhs = _B64[compressed[i]], _B64[compressed[i + 1]]
        out += [_HEX[lhs >> 2], _HEX[((lhs & 3) << 2) | (rhs >> 4)], _HEX[rhs & 0xF]]
    h = "".join(out)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


class Bundle:
    """The resources bundle, addressed by asset path rather than by UUID."""

    def __init__(self, root: str):
        self.root = root
        with open(os.path.join(root, "config.json"), encoding="utf8") as fh:
            cfg = json.load(fh)
        uuids = cfg["uuids"]
        self.by_path = {}
        for idx, entry in cfg["paths"].items():
            self.by_path[entry[0]] = decode_uuid(uuids[int(idx)])

    def objects(self, uuid: str):
        """The `objects` list out of one PvZ2 JSON asset, or []."""
        path = os.path.join(self.root, "import", uuid[:2], uuid + ".json")
        with open(path, encoding="utf8") as fh:
            asset = json.load(fh)
        # The asset is a Cocos JsonAsset: [ver, ..., [[0, name, payload]]].
        for group in asset:
            if isinstance(group, list):
                for item in group:
                    if (isinstance(item, list) and len(item) >= 3
                            and isinstance(item[2], dict)
                            and "objects" in item[2]):
                        return item[2]["objects"]
        return []


def alias_map(objects):
    """PvZ2 objects -> {alias: objdata}."""
    out = {}
    for obj in objects:
        for alias in obj.get("aliases", []) or []:
            out[alias] = obj.get("objdata", {}) or {}
    return out


def find_table(root: str, table_name: str):
    """Locate a named PvZ2 table (ZombieProps, ArmorProps, ZombieTypes...).

    The tables carry their name inside the asset, and the asset filenames are
    UUIDs, so this scans import/ for the name. Cheap enough once: the match is
    made on the raw bytes before anything is parsed.
    """
    needle = f'"{table_name}"'.encode()
    imports = os.path.join(root, "import")
    for sub in sorted(os.listdir(imports)):
        d = os.path.join(imports, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(d, fn)
            # The name sits just past the asset header, well inside this.
            with open(path, "rb") as fh:
                head = fh.read(65536)
            if needle not in head:
                continue
            with open(path, encoding="utf8") as fh:
                asset = json.load(fh)
            for group in asset:
                if not isinstance(group, list):
                    continue
                for item in group:
                    if (isinstance(item, list) and len(item) >= 3
                            and item[1] == table_name
                            and isinstance(item[2], dict)
                            and "objects" in item[2]):
                        return item[2]["objects"]
    raise SystemExit(f"could not find the {table_name} table under {imports}")


# ── the zombie model ─────────────────────────────────────────────────────────

class Zombies:
    def __init__(self, types, props, armors):
        self.types = alias_map(types)
        self.props = alias_map(props)
        self.armors = alias_map(armors)

    def prop(self, codename: str) -> dict:
        """The property sheet a codename spawns from.

        Codenames alias each other freely -- `easter` spawns from `tutorial`'s
        sheet -- so this follows the Properties RTID rather than assuming the
        sheet is named after the zombie.
        """
        ref = self.types.get(codename, {}).get("Properties", "")
        match = RTID.match(ref) if isinstance(ref, str) else None
        return self.props.get(match.group(1) if match else codename, {})

    def hp(self, codename: str) -> int:
        """Effective HP: the body plus everything it walks on with.

        An armoured variant carries all of its extra HP in StartingArmors and
        none in Toughness -- mummy and mummy_armor1 are both 190 -- so a
        Toughness-only reading would call them equals.
        """
        prop = self.prop(codename)
        total = prop.get("Toughness") or 0
        for armor in prop.get("StartingArmors") or []:
            total += self.armors.get(armor, {}).get("Toughness") or 0
        return int(total)

    def cost(self, codename: str) -> int:
        return int(self.prop(codename).get("WavePointCost") or 0)

    def excluded(self, codename: str):
        """Why this zombie may not be traded, or None.

        Each of these is a zombie the wave data spawns but that is not an
        ordinary walker, so pricing it against one is meaningless.
        """
        prop = self.prop(codename)
        if prop.get("ZombieSort") == "Zomboss":
            return "zomboss"
        if "camel" in str(self.types.get(codename, {}).get("ZombieBasedOn", "")):
            return "camel"
        if not prop.get("WavePointCost"):
            return "unpriced"
        if not prop.get("WalkSPS"):
            # WalkSPS 0 is a prop, not a zombie: future_infinut_shield (10000
            # HP), future_protector_shield, sky_dropship. They sit still, so
            # the lane never clears and the level's whole shape changes.
            return "immobile"
        if prop.get("IgnoredInWaves"):
            # The game itself refuses to wave-spawn these -- imps and support
            # that arrive from a carrier. Fielding one directly is a thing the
            # game never does.
            return "ignored_in_waves"
        if "SkyCityShipDetectXOffset" in prop:
            # Sky City zombies act on the airship. In any other world there is
            # no ship for them to act on.
            return "skycity"
        return None

    def tier(self, codename: str) -> str:
        prop = self.prop(codename)
        cost = self.cost(codename)
        band = 1 if cost <= 150 else 2 if cost <= 350 else 3 if cost <= 650 \
            else 4 if cost <= 1000 else 5
        key = f"t{band}-" + ("water" if prop.get("LivesInDeepWater") else "land")
        if prop.get("ZombieSort") == "Gargantuar":
            key += "-garg"
        # Threat mechanics, each answered by a specific plant. Partitioning
        # them is what lets the option ship with no new access rule: a world's
        # threat footprint after a shuffle is the one it had before.
        if prop.get("MoveSpeedMultiplierWhileJuggling") is not None:
            key += "-jester"     # returns your own projectiles
        if prop.get("NumberOfIceblocksToSpawnWith") is not None:
            key += "-iceblock"   # arrives carrying ice blocks
        if (prop.get("ChooseToSpawnOnNonDeckRows")
                or prop.get("BalloonToughness") is not None
                or prop.get("BugToughness") is not None):
            # Flies over ground plants. NOT BalloonToughness alone: that
            # catches the three balloons and misses every jetpack, dodo, bug
            # rider, seagull and pelican, which is how 447 levels used to gain
            # an aerial threat they had none of.
            key += "-air"
        if (prop.get("PlantBlockers") is not None
                or prop.get("ZombieBlockers") is not None
                or prop.get("NumberOfArcadeCabinetsToSpawnWith") is not None):
            key += "-blocker"    # carries something specific plants alone stop
        if (prop.get("ShieldToughness") is not None
                or prop.get("ProjectileAbsorbingFactor") is not None):
            # Absorbs shots from the front, so straight shooters stop being an
            # answer and lobbed or melee plants start being the only one.
            key += "-shield"
        if any(prop.get(k) is not None for k in
               ("ZombiesToSummon", "ZombieCountToSummon",
                "ZombieTypesToSummonBecomingFlag")):
            # Fields zombies of its own. A swap that creates a summoner adds
            # spawns the level's wave budget never accounted for.
            key += "-summon"
        hp = max(self.hp(codename), 1)
        return key + f"-h{int(math.floor(math.log(hp) / math.log(HP_BAND)))}"


# ── level rosters ────────────────────────────────────────────────────────────

# Where a level names a zombie. Only Zombies[].Type is an actual spawn; the
# pool keys are candidates the wave generator may or may not draw, so they are
# collected (the client's plan has to map them) but counted as weight 0.
SPAWN_KEYS = ("Zombies",)
POOL_KEYS = ("ZombiePool", "MustContainZombie", "AddToZombiePool")


def roster(objects, known):
    """{codename: spawn count} for one level's objects.

    A count is what the level actually spawns -- Zombies[].Type entries, one
    zombie each. Codenames that appear only in a wave generator's pool are
    recorded at count 0: the client's plan still has to map them, but the
    generator may never draw one, so they cannot be weighed as spawns.

    `known` is the set of real codenames, because "Type" also names things
    that are not zombies at all (a storm spawner's Type is "sandstorm").
    """
    counts = Counter()

    def note(value, spawn):
        if not isinstance(value, str):
            return
        match = RTID.match(value)
        name = match.group(1) if match else value
        if name not in known:
            return
        counts[name] += 1 if spawn else 0

    def walk(node, in_pool):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in POOL_KEYS:
                    walk(value, True)
                elif key == "Type":
                    note(value, not in_pool)
                else:
                    walk(value, in_pool)
        elif isinstance(node, list):
            for value in node:
                if isinstance(value, str):
                    if in_pool:
                        note(value, False)
                else:
                    walk(value, in_pool)

    for obj in objects:
        walk(obj.get("objdata", {}) or {}, False)
    return counts


def level_rosters(bundle: Bundle, known):
    """{level id: {"bespoke": bool, "zombies": {codename: count}}}."""
    out = {}
    for path, uuid in sorted(bundle.by_path.items()):
        if not path.startswith("levels/"):
            continue
        try:
            objects = bundle.objects(uuid)
        except (OSError, ValueError):
            continue
        if not objects:
            continue
        counts = roster(objects, known)
        if not counts:
            continue
        out[path.split("/", 1)[1]] = {
            "bespoke": any(BESPOKE_MODULES.search(o.get("objclass", "") or "")
                           for o in objects),
            "zombies": dict(sorted(counts.items())),
        }
    return out


# ── output ───────────────────────────────────────────────────────────────────

HEADER = '''"""
PvZ2 Gardendless -- zombie swap tiers for the shuffle_zombies option.

GENERATED by tools/gen_zombie_tiers.py from the game's own data. Do not hand
edit: rerun the generator against a game checkout instead. It also writes
test/data/zombie_balance.json, which test/balance_test.py replays the client's
roll against, so the two cannot describe different tables.

DERIVED FROM GAME DATA, not judgement. Every zombie the shipped levels can
actually spawn is bucketed by properties the game states outright, and a
shuffle only ever trades a zombie for another in its own bucket. Nothing here
is inferred from a name or a world.

The tier key joins these with "-":

  1. `WavePointCost` band -- the game's OWN price for a zombie, what its
     dynamic wave generator spends to field one:
         t1 <= 150   t2 <= 350   t3 <= 650   t4 <= 1000   t5 > 1000
  2. land / water, from `LivesInDeepWater`. Keeping the two apart is what
     stops a swap from putting a zombie in a lane it drowns in.
  3. `garg`, from `ZombieSort == "Gargantuar"`.
  4. A special-mechanic tag, for the zombies that need a specific plant to
     answer them. These are partitioned so a mechanic can never move to a
     world that has no answer for it, and can never vanish from a world whose
     access rule is built on it:
         jester    `MoveSpeedMultiplierWhileJuggling` -- returns your own
                   projectiles. Answered by JESTER_COUNTER_PLANTS, which is
                   what gates Dark Ages.
         iceblock  `NumberOfIceblocksToSpawnWith` -- arrives carrying ice
                   blocks. Answered by FIRE_AURA_PLANTS, which gates
                   Frostbite Caves.
         air       `ChooseToSpawnOnNonDeckRows`, `BalloonToughness` or
                   `BugToughness` -- flies over ground plants. No counter list
                   models this yet, so it is pinned rather than gated.
         blocker   `PlantBlockers` / `ZombieBlockers` /
                   `NumberOfArcadeCabinetsToSpawnWith` -- drops something that
                   specific plants alone can clear.
         shield    `ShieldToughness` / `ProjectileAbsorbingFactor` -- absorbs
                   shots from the front, so a straight shooter stops being an
                   answer.
         summon    `ZombiesToSummon` and friends -- fields zombies of its own,
                   which a level's wave budget never accounted for.
  5. `h{{n}}`, an effective-HP band: floor(log(hp) / log({hp_band})), where hp is
     `Toughness` plus every `StartingArmors` entry's toughness.

     WavePointCost alone was the whole tier key until this band was added, and
     it is a budget price for a generator that re-prices what it fields, not a
     measure of how hard a zombie is to kill. Trading strictly on price held
     per-level cost inside 0.78-1.21 (p5-p95) while per-level HP ran
     0.56-2.51, with 34 levels at 3x or worse -- pirate1 fielded eighteen
     10000 HP shields in place of its basic pirates. With the band, HP lands
     at 0.95-1.05. See ZOMBIE_RANDO_DEV.md.

That fourth partition is the reason this option needs no new access rule.
Threat mechanics cannot be created or destroyed by a shuffle, so every world's
threat footprint after shuffling is exactly the one it had before, and the
plant requirements in WORLD_ENTRY_PLANTS stay exactly as true as they were.

Tiers with a single member simply never swap -- there is nothing comparable
to trade for -- which mirrors how randomize_conveyor_plants leaves a plant
alone when its group has no alternative.

EXCLUSIONS. A codename that is not in the table has no tier, and the client
reads that as "leave this one exactly as the level had it" -- so a level that
ships one still gets it, and no other level can ever gain one:

{exclusion_doc}
Levels a module drives structurally are skipped whole by the client rather
than being handled here: the camel matching games, the cannon levels,
Beghouled, bowling, Last Stand and the other set pieces. See
AP_BESPOKE_MODULES in build_pvzge_ap.py.

{summary}
"""

from collections import Counter
from typing import Dict, List
'''

EXCLUSION_DOC = {
    "zomboss": "`ZombieSort == \"Zomboss\"`. Every boss fight stays the fight\n"
               "            the level was built around.",
    "camel": "every type whose `ZombieBasedOn` contains \"camel\". A camel is\n"
             "            not a walker, it is a multi-segment chain driven by\n"
             "            CamelMinigameProperties, and in the three levels that carry\n"
             "            that module the camels ARE the game: you match them by hump\n"
             "            count. Kurt found this in play testing, on egypt7.",
    "immobile": "`WalkSPS` of 0 -- future_infinut_shield (10000 HP),\n"
                "            future_protector_shield, sky_dropship. These are props, not\n"
                "            walkers: they never advance, so the lane never clears, and\n"
                "            the dropship spawns imps for as long as it stands. Priced at\n"
                "            100-150, so they used to trade with a basic zombie.",
    "ignored_in_waves": "`IgnoredInWaves` -- imps and support the game itself\n"
                        "            refuses to wave-spawn, because they are meant to arrive from\n"
                        "            a carrier. Fielding one directly is a thing the game never\n"
                        "            does.",
    "skycity": "`SkyCityShipDetectXOffset` -- Sky City zombies act on the\n"
               "            airship. In any other world there is no ship to act on.",
    "unpriced": "no `WavePointCost`, so the game gives no answer to \"how hard\n"
                "            is this\" and there is nothing to trade on.",
}


def render(tiers, hp, excluded, summary) -> str:
    doc_lines = []
    for reason in ("zomboss", "camel", "immobile", "ignored_in_waves",
                   "skycity", "unpriced"):
        names = excluded.get(reason, [])
        if not names:
            continue
        doc_lines.append(f"  {reason:<9} {EXCLUSION_DOC[reason]}\n"
                         f"            {len(names)} type"
                         f"{'' if len(names) == 1 else 's'}.\n")
    out = [HEADER.format(hp_band=HP_BAND,
                         exclusion_doc="\n".join(doc_lines),
                         summary=summary)]

    out.append("\nZOMBIE_TIERS: Dict[str, List[str]] = {\n")
    for tier in sorted(tiers):
        members = sorted(tiers[tier])
        out.append(f"    {tier!r}: [\n")
        line = "       "
        for name in members:
            piece = f" {name!r},"
            if len(line) + len(piece) > 78:
                out.append(line + "\n")
                line = "       "
            line += piece
        out.append(line + "\n")
        out.append(f"    ],  # {len(members)}\n")
    out.append("}\n")

    out.append('''
# codename -> effective HP (Toughness plus every StartingArmors entry). Sent to
# the client as slot_data so its per-level budget guard can weigh a level's
# roster before and after a shuffle; see ZOMBIE_RANDO_DEV.md. Only the tiered
# zombies are here -- an untiered one never moves, so nothing needs to weigh
# it.
ZOMBIE_HP: Dict[str, int] = {
''')
    for name in sorted(hp):
        out.append(f"    {name!r}: {hp[name]},\n")
    out.append("}\n")

    out.append('''
# Why each dropped codename is dropped, kept so a test can assert the reasons
# still hold after a regeneration rather than trusting this file.
ZOMBIE_EXCLUSIONS: Dict[str, List[str]] = {
''')
    for reason in sorted(excluded):
        names = sorted(excluded[reason])
        out.append(f"    {reason!r}: [\n")
        line = "       "
        for name in names:
            piece = f" {name!r},"
            if len(line) + len(piece) > 78:
                out.append(line + "\n")
                line = "       "
            line += piece
        out.append(line + "\n")
        out.append(f"    ],  # {len(names)}\n")
    out.append("}\n")

    out.append('''
# codename -> tier key. The client is sent ZOMBIE_TIERS and inverts it the same
# way; this side needs it to answer "may these two zombies trade places".
ZOMBIE_TIER_OF: Dict[str, str] = {
    zombie: tier for tier, zombies in ZOMBIE_TIERS.items() for zombie in zombies
}

# A zombie may not appear in two tiers -- the dict comprehension above would
# silently keep the last one, and the client's swap pool would disagree with
# this side's about which trade is legal.
_seen = Counter(z for zombies in ZOMBIE_TIERS.values() for z in zombies)
_dupes = sorted(z for z, n in _seen.items() if n > 1)
if _dupes:
    raise ValueError(f"zombies listed in more than one tier: {_dupes}")

# Tiers whose special-mechanic tag means the game needs a specific plant to
# answer them. Kept as a name list rather than folded into the tier keys so a
# test can assert the partition still holds after a data regeneration.
THREAT_TAGS = ("jester", "iceblock", "air", "blocker", "shield", "summon")

# Geometric width of one HP band, as the generator used it. A test reads this
# to assert no tier spans more than one band's worth of HP.
HP_BAND = %s


def tier_of(zombie: str) -> str:
    """Tier key for a zombie codename, or "" if it is not shuffled at all."""
    return ZOMBIE_TIER_OF.get(zombie, "")


def swap_pool(zombie: str) -> List[str]:
    """Zombies this one may be traded for, itself included.

    Empty for a zombie outside the table -- a Zomboss, a camel, a prop, a type
    no shipped level spawns -- which the caller reads as "leave this one
    exactly as the level had it".
    """
    tier = ZOMBIE_TIER_OF.get(zombie)
    return list(ZOMBIE_TIERS[tier]) if tier else []
''' % HP_BAND)
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-root", required=True,
                    help="a PVZGE-Electron checkout, or its "
                         "pvzge_web/docs/assets/resources directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    args = ap.parse_args()

    root = os.path.expanduser(args.game_root)
    if not os.path.isdir(os.path.join(root, "import")):
        guess = os.path.join(root, "pvzge_web", "docs", "assets", "resources")
        if os.path.isdir(os.path.join(guess, "import")):
            root = guess
        else:
            raise SystemExit(f"no resources bundle under {root}")

    print(f"reading {root}")
    bundle = Bundle(root)
    zombies = Zombies(find_table(root, "ZombieTypes"),
                      find_table(root, "ZombieProps"),
                      find_table(root, "ArmorProps"))
    print(f"  {len(zombies.types)} zombie types, {len(zombies.props)} property "
          f"sheets, {len(zombies.armors)} armors")

    levels = level_rosters(bundle, set(zombies.types))
    bespoke = sum(1 for lv in levels.values() if lv["bespoke"])
    print(f"  {len(levels)} levels ({bespoke} bespoke)")

    # "Can actually spawn" means a shipped level names it. A type no level
    # fields is not something a shuffle should be able to introduce.
    spawnable = set()
    for level in levels.values():
        spawnable.update(level["zombies"])

    tiers, hp, excluded = defaultdict(list), {}, defaultdict(list)
    for codename in sorted(spawnable):
        if codename not in zombies.types:
            continue                      # lawn placeholders and the like
        reason = zombies.excluded(codename)
        if reason:
            excluded[reason].append(codename)
            continue
        tiers[zombies.tier(codename)].append(codename)
        hp[codename] = zombies.hp(codename)

    swappable = sum(len(v) for v in tiers.values() if len(v) > 1)
    total = sum(len(v) for v in tiers.values())
    worst = max((max(hp[z] for z in v) / max(min(hp[z] for z in v), 1)
                 for v in tiers.values()), default=1)
    summary = (f"{total} zombies over {len(tiers)} tiers, "
               f"{swappable} of them ({swappable * 100 // total}%) with somebody "
               f"to trade with.\nWorst intra-tier HP ratio {worst:.2f}. "
               f"{sum(len(v) for v in excluded.values())} codenames excluded.")
    print("  " + summary.replace("\n", "\n  "))

    source = render(tiers, hp, excluded, summary)
    extract = {
        "note": "Generated by tools/gen_zombie_tiers.py. Replayed by "
                "test/balance_test.py against the client's own roll.",
        "hp_band": HP_BAND,
        "zombies": {z: {"hp": zombies.hp(z), "cost": zombies.cost(z)}
                    for z in sorted(spawnable) if z in zombies.types},
        "levels": levels,
    }

    if args.dry_run:
        print("  (dry run, nothing written)")
        return 0

    out_py = os.path.join(REPO, "pvz2gardendless", "zombie_data.py")
    with open(out_py, "w", encoding="utf8") as fh:
        fh.write(source)
    print(f"wrote {os.path.relpath(out_py, REPO)}")

    out_json = os.path.join(REPO, "test", "data", "zombie_balance.json")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf8") as fh:
        json.dump(extract, fh, indent=1, sort_keys=True)
        fh.write("\n")
    size = os.path.getsize(out_json) / 1024
    print(f"wrote {os.path.relpath(out_json, REPO)} ({size:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
