#!/usr/bin/env python3
"""Generate pvz2gardendless/plant_data.py from a PvZ2 Gardendless checkout.

    python tools/gen_plant_power.py --game-root <checkout>/docs/assets/resources

Companion to gen_zombie_tiers.py, and built on its Bundle/find_table readers.
Where that tool answers "which zombies may trade places", this one answers
"is the lawn the player can field able to kill what this level sends", which is
what the plant-power access rules in rules.py are built on.

TWO DERIVED NUMBERS, both from the game's own tables:

  plant LAWN DPS -- the damage per second a player can have on the board from
      one kind of plant:

          dps  = hit_damage * spread / cycle
          lawn = dps * min(MAX_COPIES, SUN_BUDGET // sun)

      hit_damage is the damage of the plant's NORMAL attack and nothing else:
      the first non-secondary projectile/explode/special action it declares,
      resolved through the projectile tables. Taking the largest damage number a
      plant states ANYWHERE reads its plant-food figure instead and inflates
      half the roster (Laser Bean 1800, Fume-Shroom 1500), and the almanac grade
      medians inflate the fast tickers the other way (Spikeweed 10 damage every
      half second is not the 60 its grade's median says). The grade median is
      the FALLBACK, for the plants whose damage the reimplementation keeps in
      code rather than in a table.

      spread is the almanac `range`/`area` tag -- how many zombies one shot can
      touch. cycle is the attack interval for a plant that stays on the lawn and
      the SEED PACKET RECHARGE for one that does not, because a consumable's
      real rate of fire is how fast the packet comes back.

      The copy count is what makes this comparable with a level: one Peashooter
      does not clear Ancient Egypt 3, ten of them do, and whether a player can
      field ten is decided by the card's price.

  level PRESSURE -- effective zombie HP per wave:

          pressure = (fixed roster HP + dynamic wave budget HP) / WaveCount

      The fixed roster is the one gen_zombie_tiers.py already measures (it is
      read back out of test/data/zombie_balance.json rather than recomputed, so
      the two tools cannot disagree about what a level sends). The dynamic half
      is the level's own DynamicZombies spending points, converted to HP at the
      HP-per-point of the pool each entry draws from.

THE TWO MEET IN THE SAME UNIT. pressure is HP the lawn must remove per wave and
a wave has to be gone before the next one lands, so

    required dps = pressure / WAVE_SECONDS

and a plant answers a level when its lawn dps reaches that. Both sides are
damage per second, so this is an arithmetic statement rather than a ranking
trick -- which is why the first version of this tool, which banded both axes by
quantile and compared the bands, was thrown away: quantiles gave the EASIEST
fifth of the levels no requirement at all, which is exactly where the failure
this exists to stop had happened.

Requirements are rounded UP onto a ladder of bands (BAND_BASE doubling
BAND_FACTOR-wise) so that a handful of plant lists covers every level instead of
one list per level. Rounding up rather than down is deliberate: it asks for
slightly more than the measurement does.

EXEMPT LEVELS. A level only gets a requirement if the player's own collection
is what they play it with. Levels whose SeedBank is `preset`, levels carrying a
ConveyorBelt module, and levels with no wave manager at all (the Zomboss
fights) hand the player their plants, so nothing they own can be required.

WHAT IS NOT MODELLED, deliberately: lane count, water lanes, specific threat
mechanics (those are WORLD_ENTRY_PLANTS' job), plant food, and the mowers. The
band mapping absorbs all of it -- which is why the checks in
test/plant_power_test.py are about ordering and satisfiability rather than about
any particular number being right.
"""

import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_zombie_tiers import Bundle, alias_map, find_table  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(REPO, "pvz2gardendless", "build_pvzge_ap.py")
BALANCE = os.path.join(REPO, "test", "data", "zombie_balance.json")
OUT_PY = os.path.join(REPO, "pvz2gardendless", "plant_data.py")
OUT_JSON = os.path.join(REPO, "test", "data", "plant_power.json")

RTID = re.compile(r"RTID\(([^@)]+)@")

# The fewest plants in the game that any one level's requirement may leave as
# answers. A requirement is clamped down to the lawn dps of the ANSWER_FLOOR-th
# best plant, for two reasons. The model is least reliable at its extremes --
# plant food, upgrades and mastery are not modelled at all, and the handful of
# plants at the very top of the ladder are there partly because their data
# flatters them (Magnifying Grass spends sun per shot; Cran-Jelly states a rate
# nothing else states). And a requirement only three plants can meet makes fill
# brittle for no gain: the point is to stop a seed leaving a player with nothing
# that works, not to prescribe which plant they use.
ANSWER_FLOOR = 12

# A consumable plant is priced at ONE copy however cheap its card is: each use
# removes the plant, so its damage never accumulates on the lawn the way a
# shooter's does. Potato Mine at 25 sun would otherwise read as twelve copies
# and 3240 damage a second, which is not a thing that happens.
CONSUMABLE_COPIES = 1

# Seconds a level gives the lawn to clear one wave before the next lands. PvZ2
# releases a wave when the one before it is mostly dead or when this much time
# has passed, whichever comes first, so it is an upper bound on the time
# available and therefore a lower bound on the damage needed.
WAVE_SECONDS = 25.0

# Sun a player can reasonably have spent on attackers at once, with a sun
# producer running. What it is really standing in for is "how many copies can
# you afford", which is why it is paired with a cap: the number is only ever
# used as SUN_BUDGET // sun.
SUN_BUDGET = 1000.0

# ...and the cap. A 5-lane lawn is 45 tiles, and a real one spends some of them
# on sun and on a wall per lane, so no plant is ever fielded more than about a
# dozen times. Without this, a 25-sun plant reads as forty copies and every
# cheap plant lands at the top of the ladder.
MAX_COPIES = 12

# How many rungs the requirement ladder has. Five, as the zombie tiers' cost
# bands have: enough that an easy level is not asked what a hard one is, few
# enough that the per-slot draw in constants.py stays small.
#
# The rungs are QUANTILES of the requirements the levels actually come out with,
# not a fixed doubling. A doubling ladder was tried first and rounded far too
# hard at the top: 35 levels landed on a rung only three plants in the game
# could reach, because their real requirement sat just past a rung that 11
# could. Quantiles put a healthy number of answers on every rung by
# construction.
BAND_COUNT = 5

# The almanac `range`/`area` tag, as a count of zombies one shot can touch.
# Every value here appears in the game's own PlantStats; anything unlisted
# counts as single-target, which is the conservative reading.
SPREAD = {
    "single": 1, "straight": 1, "close": 1, "touch": 1, "lobbed": 1,
    "1by1": 1, "variable0": 1,
    "multihit": 2, "frontback": 2, "3tiles": 2, "1by4": 2,
    "3by3": 3, "3x3": 3, "square": 3, "multilane": 3, "5way": 3, "4way": 3,
    "lane": 3, "currant": 3,
    "fullboard": 5,
}

# The field naming a plant's normal attack projectile, in the order tried.
PRIMARY_PROJECTILE = ("PeaType", "CabbageType", "ProjectileType", "BoomerangType",
                      "ButterType", "BananaType", "SawType", "ShroomType",
                      "SporeType", "TornadoType", "SummonType")
# A sheet marks its plant-food action with a comment key rather than a field.
PLANT_FOOD = re.compile(r"[Pp]lant ?[Ff]ood")
# Damage fields that are a real per-hit number, in the order they are trusted.
HIT_FIELDS = ("Damage", "StabDamage", "AttackDamage", "DamagePerHit",
              "HeadDamage", "ExplodeDamage", "ExplosionDamage")
SHEET_HIT_FIELDS = ("ChewDamage", "MeleeDamage", "SlapDamage",
                    "NormalTongueSlapDamage", "ExplosionDamage",
                    "DeathExplosionDamage")
INTERVALS = ("ShootInterval", "ThrowInterval", "AttackInterval",
             "StabInterval", "RayInterval")
# Projectile-naming fields whose projectile is NOT the normal attack.
NOT_NORMAL = re.compile(r"Plantfood|PlantFood|PF|Mint|Mega|Giant|Ultra|Upgraded")


def num(value):
    """A damage field as a float. Some are lists (one entry per upgrade)."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        nums = [v for v in value if isinstance(v, (int, float))]
        return float(max(nums)) if nums else 0.0
    return 0.0


def rt(value):
    match = RTID.match(value) if isinstance(value, str) else None
    return match.group(1) if match else value


def js_block(src: str, pattern: str) -> str:
    """One brace-balanced JS object literal out of the client string."""
    match = re.search(pattern, src)
    if not match:
        raise SystemExit(f"could not find {pattern} in {CLIENT}")
    start = src.index("{", match.start())
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise SystemExit(f"unterminated object for {pattern}")


def ap_name_to_codename():
    """{Archipelago item name: game codename} for every plant item.

    Read out of the injected client rather than restated here: ITEM_PLANT and
    ID_TO_CN are what the running game uses to turn an item into a plant, so
    they are the only mapping that cannot be wrong.
    """
    src = open(CLIENT, encoding="utf8").read()
    ids = {m.group(1): int(m.group(2))
           for m in re.finditer(r"(\w+)\s*:\s*(\d+)",
                                js_block(src, r"const P *= *\{"))}
    codename = {int(m.group(1)): m.group(2)
                for m in re.finditer(r"(\d+)\s*:\s*'([^']+)'",
                                     js_block(src, r"const ID_TO_CN *= *\{"))}
    out = {}
    for m in re.finditer(r"'([^']+)'\s*:\s*P\.(\w+)",
                         js_block(src, r"const ITEM_PLANT *= *\{")):
        pid = ids.get(m.group(2))
        if pid is None:
            raise SystemExit(f"ITEM_PLANT names P.{m.group(2)}, which P lacks")
        out[m.group(1)] = codename.get(pid)
    return out


def tracked_levels():
    """{level id} for every level the world has a location for.

    LOC_LEVELS in the client, again: the world's location names ARE level ids,
    and this is the table the client gates them through.
    """
    src = open(CLIENT, encoding="utf8").read()
    return {m.group(2) for m in re.finditer(
        r"'([^']+)'\s*:\s*'([^']+)'", js_block(src, r"const LOC_LEVELS *= *\{"))}


class Game:
    """Every table this tool reads, addressed by name."""

    def __init__(self, root):
        self.root = root
        self.bundle = Bundle(root)
        self.plant_props = alias_map(find_table(root, "PlantProps"))
        self.proj_props = alias_map(self._objects("json/Objects/ProjectileProps"))
        self.proj_types = alias_map(self._objects("json/Objects/ProjectileTypes"))
        # The `_`-prefixed tables are the original PvZ2 sheets the reimplement-
        # ation keeps beside its own. They carry the almanac PlantStats and a
        # BaseDamage for every projectile, neither of which the runtime tables
        # have, so they are the source for the grade and the fallback for
        # damage.
        self.sheets = self._aliased("json/_Objects/_PLANTPROPERTIES")
        self.legacy_proj = self._aliased("json/_Objects/_PROJECTILETYPES")
        self.by_norm = {self._norm(a.replace("Default", "")): d
                        for a, d in self.sheets.items()}

    @staticmethod
    def _norm(name):
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def _objects(self, path):
        return self.bundle.objects(self.bundle.by_path[path])

    def _aliased(self, path):
        out = {}
        for obj in self._objects(path):
            for alias in obj.get("aliases") or []:
                out[alias] = obj.get("objdata") or {}
        return out

    def sheet(self, codename):
        return self.by_norm.get(self._norm(codename)) or {}

    def projectile_damage(self, name, seen=None):
        """Per-hit damage of a projectile, runtime table first."""
        seen = seen or set()
        name = rt(name)
        if not isinstance(name, str) or name in seen:
            return 0.0
        seen.add(name)
        props = self.proj_props.get(name)
        if props:
            damage = num(props.get("Damage")) + num(props.get("SplashDamage"))
            if damage:
                return damage
        types = self.proj_types.get(name)
        if types:
            for key in ("ProjectileBasedOn", "Props"):
                based = rt(types.get(key))
                if isinstance(based, str) and based != name:
                    damage = self.projectile_damage(based, seen)
                    if damage:
                        return damage
        legacy = self.legacy_proj.get(name)
        if legacy:
            damage = num(legacy.get("BaseDamage")) + num(legacy.get("SplashDamage"))
            if damage:
                return damage
            based = legacy.get("ProjectileBasedOn")
            if based and based != name:
                return self.projectile_damage(based, seen)
        return 0.0

    def stats(self, codename):
        """(damage grade, spread tag) from the almanac PlantStats."""
        grade = spread = None
        for stat in self.sheet(codename).get("PlantStats") or []:
            if not isinstance(stat, dict):
                continue
            if stat.get("Type") == "damage":
                grade = stat.get("Value")
            elif stat.get("Type") in ("range", "area") and spread is None:
                spread = stat.get("Value")
        return grade, spread

    def interval(self, codename):
        """Seconds between normal attacks, or None for a plant that has none."""
        props = self.plant_props.get(codename) or {}
        for key in INTERVALS:
            value = props.get(key)
            if isinstance(value, (int, float)) and value > 0:
                extra = props.get(key + "Additional")
                return value + (extra / 2 if isinstance(extra, (int, float)) else 0)
        for action in self.sheet(codename).get("Actions") or []:
            if isinstance(action, dict) and action.get("Type") == "projectile":
                cooldown = action.get("CooldownTimeMin") or action.get("CooldownTimeMax")
                if isinstance(cooldown, (int, float)) and cooldown > 0:
                    return float(cooldown)
        return None

    def normal_damage(self, codename):
        """(damage, where from) for this plant's NORMAL attack only.

        The first action it declares that is not a secondary or a plant-food
        one, resolved through the projectile tables. Scanning for the largest
        damage number a plant states anywhere reads its plant-food figure
        instead, which inflates half the roster.
        """
        props = self.plant_props.get(codename) or {}
        for key in PRIMARY_PROJECTILE:
            if key in props and not NOT_NORMAL.search(key):
                damage = self.projectile_damage(props[key])
                if damage:
                    return damage, "props:" + key
        sheet = self.sheet(codename)
        for action in sheet.get("Actions") or []:
            if not isinstance(action, dict) or action.get("SecondaryAction"):
                continue
            # The sheets mark plant food with a comment key rather than a field.
            if PLANT_FOOD.search(json.dumps(action)):
                continue
            if action.get("Type") not in ("projectile", "explode", "special"):
                continue
            if action.get("Projectile"):
                damage = self.projectile_damage(action["Projectile"])
                if damage:
                    return damage, "sheet:projectile"
            damage = num(action.get("Damage"))
            if damage:
                return damage, "sheet:" + str(action.get("Type"))
            # The first real action had no damage of its own: stop rather than
            # walk on into the plant-food ones behind it.
            break
        for key in HIT_FIELDS:
            damage = num(props.get(key))
            if damage:
                return damage, "props:" + key
        for key in SHEET_HIT_FIELDS:
            damage = num(sheet.get(key))
            if damage:
                return damage, "sheet:" + key
        # A plant whose sheet states damage per second instead of per hit.
        for key in ("DPS", "PoisonDPS"):
            rate = num(props.get(key))
            if rate:
                return rate * (self.interval(codename) or 1.0), "props:" + key
        return 0.0, None

    def sun_cost(self, codename):
        props = self.plant_props.get(codename) or {}
        sun = props.get("SunCost")
        if isinstance(sun, (int, float)):
            return float(sun)
        costs = props.get("SunCostList")
        if isinstance(costs, list) and costs and isinstance(costs[0], (int, float)):
            return float(costs[0])
        return None

    def recharge(self, codename):
        props = self.plant_props.get(codename) or {}
        cooldown = props.get("Cooldown")
        return float(cooldown) if isinstance(cooldown, (int, float)) else None

    def water_only(self, codename):
        """A plant that can only be placed on water, in either table."""
        for table in (self.plant_props.get(codename) or {}, self.sheet(codename)):
            if table.get("IsZenGardenWaterPlant"):
                return True
            if table.get("PlantGridType") == "water":
                return True
        return False


def grade_damage(game, bridge):
    """{almanac grade: representative per-hit damage}, measured.

    The median normal-attack damage of every plant carrying that grade. Used
    only as a fallback, for plants whose damage the reimplementation keeps in
    code rather than in a table -- but measured rather than guessed, and it
    comes out monotone in the grade, which is what makes it usable at all.
    """
    by_grade = defaultdict(list)
    for codename in bridge.values():
        grade, _ = game.stats(codename)
        damage, _ = game.normal_damage(codename)
        if grade and damage:
            by_grade[grade].append(damage)
    return {g: statistics.median(v) for g, v in sorted(by_grade.items())}


def plant_lawn_dps(game, bridge, single_use, non_damaging):
    """{name: (dps, lawn dps, how)} and {name: why} for everything excluded."""
    reps = grade_damage(game, bridge)
    kept, excluded = {}, {}
    for name, codename in sorted(bridge.items()):
        if name in non_damaging:
            excluded[name] = "no attack"
            continue
        if game.water_only(codename):
            # A water plant cannot answer a dry level, and most levels are dry.
            # Left out rather than terrain-tagged: there are two of them and
            # neither is anyone's damage plan.
            excluded[name] = "water only"
            continue
        if codename not in game.plant_props:
            excluded[name] = "no PlantProps entry"
            continue
        damage, how = game.normal_damage(codename)
        grade, spread_tag = game.stats(codename)
        if not damage:
            damage, how = reps.get(grade, 0.0), "almanac grade median"
        if not damage:
            excluded[name] = "no damage stated"
            continue
        if name in single_use:
            cycle = game.recharge(codename)
        else:
            cycle = game.interval(codename) or game.recharge(codename)
        if not cycle:
            excluded[name] = "no attack rate stated"
            continue
        sun = game.sun_cost(codename)
        if sun is None:
            excluded[name] = "no sun cost"
            continue
        # A free plant is priced as the cheapest card in the game rather than at
        # zero: its reach is finite in play, and dividing by zero is not.
        sun = sun or 25.0
        dps = damage * SPREAD.get(spread_tag, 1) / cycle
        if name in single_use:
            copies = CONSUMABLE_COPIES
        else:
            copies = max(1, min(MAX_COPIES, int(SUN_BUDGET // sun)))
        kept[name] = (round(dps, 2), round(dps * copies, 1), how)
    return kept, excluded


def level_pressure(game, balance):
    """{level id: effective zombie HP per wave} for every level that has waves."""
    hp = {k: v["hp"] for k, v in balance["zombies"].items()}
    cost = {k: v["cost"] for k, v in balance["zombies"].items()}
    out = {}
    for path, uuid in sorted(game.bundle.by_path.items()):
        if not path.startswith("levels/"):
            continue
        try:
            objects = game.bundle.objects(uuid)
        except (OSError, ValueError):
            continue
        waves = manager = None
        dynamic = []
        seedbank = None
        conveyor = False
        for obj in objects:
            cls = obj.get("objclass")
            data = obj.get("objdata") or {}
            if cls == "WaveManagerProperties":
                manager = data
            elif cls == "WaveManagerModuleProperties":
                dynamic = data.get("DynamicZombies") or []
            elif cls == "SeedBankProperties":
                seedbank = data
            elif cls == "LevelDefinition":
                conveyor = any("Conveyor" in str(rt(m))
                               for m in data.get("Modules") or [])
        if manager:
            waves = manager.get("WaveCount") or len(manager.get("Waves") or [])
        level = path.split("/", 1)[1]
        if not isinstance(waves, int) or waves <= 0:
            continue
        roster = balance["levels"].get(level, {}).get("zombies", {})
        total = sum(hp.get(z, 0) * n for z, n in roster.items())
        for entry in dynamic:
            start = entry.get("StartingPoints")
            step = entry.get("PointIncrementPerWave")
            first = entry.get("StartingWave")
            pool = [rt(z) for z in entry.get("ZombiePool") or []]
            ratios = [hp[z] / cost[z] for z in pool if hp.get(z) and cost.get(z)]
            if not isinstance(start, (int, float)) or not isinstance(first, (int, float)):
                continue
            if not ratios:
                continue
            if not isinstance(step, (int, float)):
                step = 0
            ratio = statistics.mean(ratios)
            for wave in range(int(first), waves + 1):
                points = start + step * (wave - first)
                if points > 0:
                    total += points * ratio
        method = (seedbank or {}).get("SelectionMethod")
        out[level] = {
            "pressure": round(total / waves, 1),
            # Only a level the player brings their own plants to can require
            # anything of them.
            "own_plants": method == "chooser" and not conveyor,
        }
    return out


# The level-id prefix of each world, in game order -- the order a player meets
# them, which is the order WORLD_REGIONS in constants.py lists them in. Used only
# to replay the BASE GAME's own plant unlocks in order, which is the one external
# check available on this model: whatever plants the base game has handed a
# player by the time it puts a level in front of them, at least one of them has
# to clear it. test/plant_power_test.py asserts exactly that.
WORLD_ORDER = ("egypt", "pirate", "cowboy", "future", "dark", "beach", "iceage",
               "lostcity", "kongfu", "eighties", "dino", "sky", "modern")
LEVEL_ID = re.compile(r"([a-z]+)(\d+)$")


def vanilla_progression(game, bridge):
    """[(level, [plant names unlocked before it])], in the base game's order.

    A level's FirstRewardParam names the plant beating it unlocks, and
    BASEUNLOCKLIST names what a new save starts with, so walking the worlds in
    order reproduces what a base-game player owns at every point.
    """
    order = {prefix: i for i, prefix in enumerate(WORLD_ORDER)}
    codename = {cn: name for name, cn in bridge.items()}
    unlocks = {}
    for path, uuid in sorted(game.bundle.by_path.items()):
        if not path.startswith("levels/"):
            continue
        try:
            objects = game.bundle.objects(uuid)
        except (OSError, ValueError):
            continue
        for obj in objects:
            if obj.get("objclass") != "LevelDefinition":
                continue
            data = obj.get("objdata") or {}
            if data.get("FirstRewardType") == "unlock_plant":
                unlocks[path.split("/", 1)[1]] = data.get("FirstRewardParam")

    def sequence(level):
        match = LEVEL_ID.match(level)
        if not match or match.group(1) not in order:
            return None
        return (order[match.group(1)], int(match.group(2)))

    held = [codename[cn] for cn in game.base_unlocks() if cn in codename]
    out = []
    for _, level in sorted((s, l) for l in unlocks | {k: None for k in unlocks}
                           if (s := sequence(l))):
        out.append((level, sorted(held)))
        gained = codename.get(unlocks.get(level))
        if gained:
            held.append(gained)
    return out


def draw_rungs(requirements):
    """The lawn dps a per-slot draw has to cover, hardest rung last.

    The requirements are cut into BAND_COUNT equal buckets and each rung is the
    HARDEST requirement in its bucket, so a plant drawn for a rung answers every
    level in it. This is the only thing bands are still used for: the rule a
    level carries names every plant that clears that level exactly, with no
    rounding at all (see plants_for in constants.py).
    """
    ordered = sorted(requirements)
    if not ordered:
        return []
    rungs = []
    for i in range(BAND_COUNT):
        end = len(ordered) * (i + 1) // BAND_COUNT
        if end:
            rungs.append(round(ordered[end - 1], 1))
    # Buckets can tie at the bottom of the range, where many levels share a
    # requirement. Keep one rung per distinct value.
    return sorted(set(rungs))


HEADER = '''"""
PvZ2 Gardendless -- what each plant can kill, and what each level needs killed.

GENERATED by tools/gen_plant_power.py from the game's own data. Do not hand
edit: rerun the generator against a game checkout instead. It also writes
test/data/plant_power.json, which test/plant_power_test.py checks this table
against, so the two cannot describe different models.

WHAT THIS IS FOR. rules.py puts one requirement on every level the player
brings their own plants to: hold an attacker whose LAWN DPS reaches the band
that level needs. Without it a seed can leave a player holding nothing that can
kill what a level sends -- the Ancient Egypt 3/4 failure Kurt hit, where the
run's only attacker was slow and expensive and no rule had asked for better.

LAWN DPS, per plant: the damage per second a player can have on the board from
one kind of plant.

    dps  = hit_damage * spread / cycle
    lawn = dps * min({copies}, {budget:.0f} // sun)

  hit_damage  the plant's NORMAL attack and nothing else -- the first action it
              declares that is not a secondary or a plant-food one. Taking the
              largest damage number a plant states anywhere reads its plant-food
              figure instead (Laser Bean 1800, Fume-Shroom 1500). The almanac
              `damage` grade's measured median is the fallback, for the plants
              whose damage the reimplementation keeps in code.
  spread      the almanac `range`/`area` tag as a count of zombies one shot can
              touch -- 1 for straight/lobbed/close, 2 for multihit/frontback,
              3 for 3by3/multilane/lane, 5 for fullboard.
  cycle       the attack interval, or the SEED PACKET RECHARGE for a plant that
              does not stay on the lawn: a consumable's real rate of fire is how
              fast its packet comes back.
  copies      how many the player can afford, capped at {copies}. A 5-lane lawn is
              45 tiles and a real one spends some on sun and a wall per lane.
              The copy count is what makes a plant comparable with a level: one
              Peashooter does not clear Ancient Egypt 3, ten of them do, and
              whether ten is affordable is what the card's price decides.

REQUIRED DPS, per level: the HP a wave brings, over the time there is to remove
it.

    pressure     = (fixed roster HP + dynamic wave budget HP) / WaveCount
    required dps = pressure / {wave:.0f}

  The fixed roster is read back out of test/data/zombie_balance.json, which
  gen_zombie_tiers.py writes, so the two tools cannot disagree about what a
  level sends. The dynamic half is the level's own DynamicZombies spending
  points at the HP-per-point of the pool each entry draws from. {wave:.0f} seconds is
  what a PvZ2 wave gets before the next one lands.

BOTH SIDES ARE DAMAGE PER SECOND, which is the point: the comparison is
arithmetic rather than a ranking trick. An earlier version of this table banded
both axes by quantile and compared the bands; it was thrown away because
quantiles give the easiest fifth of the levels no requirement at all, which is
exactly where the failure this exists to stop had happened.

A CEILING. No level asks for more than the {floor}th best plant in the game can do.
The model is least reliable at its extremes -- plant food, upgrades and mastery
are not modelled, and some of the plants at the very top are there because their
data flatters them -- and a requirement only three plants can meet makes fill
brittle for no gain. The point is to stop a seed leaving a player with nothing
that works, not to prescribe which plant they use.

NO ROUNDING. Every level keeps its own requirement, and the rule it carries
names exactly the plants whose lawn dps reaches it. Two earlier versions banded
the requirements first and both were wrong in the same place: rounding a band UP
left 35 levels asking for something only three plants in the game could do,
and rounding DOWN gave Ancient Egypt 3 -- the level this table exists because of
-- a requirement of 36 damage a second when it needs 136.

Bands survive in one place only, DRAW_RUNGS, because the per-slot draw that
decides which of these plants become PROGRESSION items has to name a bounded
number of them (see slot_power_plants in constants.py). A rung is the hardest
requirement in its bucket, so a plant drawn for a rung answers every level in
that bucket, and the rule each level carries is still its own exact list.

A CONSUMABLE COUNTS AS ONE COPY however cheap its card is. Each use removes the
plant, so its damage never accumulates on the lawn the way a shooter's does:
Potato Mine at 25 sun would otherwise read as twelve copies and 3240 damage a
second, which is not a thing that happens. This is the same distinction
STARTER_PLANTS draws, priced rather than flagged.

EXCLUSIONS. A plant with no lawn dps is not an answer to anything and is left
out of every requirement list, which is the conservative direction: a rule can
only ask for a plant the model is sure about. Support, defence and sun state no
damage; water plants are out because most levels are dry; a few real attackers
are out because the reimplementation keeps their damage in code.

LEVELS WITH NO REQUIREMENT. A level whose SeedBank is `preset`, one carrying a
ConveyorBelt module, and one with no wave manager at all (the Zomboss fights)
hand the player their plants, so nothing they own can be required of them. Those
levels are absent from LEVEL_POWER_NEED entirely, and so are the levels no
location tracks.

NOT MODELLED, deliberately: lane count, plant food, the mowers, and specific
threat mechanics -- Jester, ice blocks and the rest stay WORLD_ENTRY_PLANTS'
job. test/plant_power_test.py therefore checks ordering, satisfiability and the
one external fact available (that the plants the base game has handed a player
by level N always satisfy level N), not that any single number is right.

{summary}
"""

from typing import Dict, List, Tuple

'''


def render(plants, excluded, required, rungs, summary):
    """The generated module, as text."""
    out = [HEADER.format(copies=MAX_COPIES, budget=SUN_BUDGET, wave=WAVE_SECONDS,
                         floor=ANSWER_FLOOR, summary=summary)]

    out.append("# The model's own constants, restated so a reader of this file\n"
               "# does not have to open the generator. Changing one means\n"
               "# regenerating, not editing below.\n")
    out.append(f"WAVE_SECONDS = {WAVE_SECONDS}\n")
    out.append(f"SUN_BUDGET = {SUN_BUDGET}\n")
    out.append(f"MAX_COPIES = {MAX_COPIES}\n")
    out.append(f"CONSUMABLE_COPIES = {CONSUMABLE_COPIES}\n")
    out.append(f"ANSWER_FLOOR = {ANSWER_FLOOR}\n")

    out.append("\n# The lawn dps a per-slot draw has to cover, hardest last: the\n"
               "# levels' requirements cut into equal buckets, each rung the\n"
               "# hardest requirement in its bucket. Only the DRAW is banded --\n"
               "# the rule a level carries names exactly the plants that clear\n"
               "# it, with no rounding.\n"
               "DRAW_RUNGS: Tuple[float, ...] = (%s)\n"
               % ", ".join(str(r) for r in rungs))

    out.append("\n# Damage per second one plant of each kind does.\n"
               "PLANT_DPS: Dict[str, float] = {\n")
    for name in sorted(plants):
        out.append(f"    {name!r}: {plants[name][0]},\n")
    out.append("}\n")

    out.append("\n# ...and what a lawn's worth of them does, which is the figure\n"
               "# a level's requirement is compared with. A plant missing here\n"
               "# has no lawn dps the model is sure of and answers nothing; see\n"
               "# PLANT_POWER_EXCLUSIONS.\n"
               "PLANT_LAWN_DPS: Dict[str, float] = {\n")
    for name in sorted(plants):
        out.append(f"    {name!r}: {plants[name][1]},\n")
    out.append("}\n")

    out.append("\n# Where each plant's damage figure came from, kept for the\n"
               "# next person to audit one of these numbers.\n"
               "PLANT_DAMAGE_SOURCE: Dict[str, str] = {\n")
    for name in sorted(plants):
        out.append(f"    {name!r}: {plants[name][2]!r},\n")
    out.append("}\n")

    out.append("\n# Plants with no lawn dps, and why. Never named by a\n"
               "# requirement: the model only asks for plants it is sure about.\n"
               "PLANT_POWER_EXCLUSIONS: Dict[str, str] = {\n")
    for name in sorted(excluded):
        out.append(f"    {name!r}: {excluded[name]!r},\n")
    out.append("}\n")

    out.append("\n# Damage per second each level needs on the board. A level\n"
               "# absent here asks nothing of the player's collection, either\n"
               "# because it hands them their plants or because no location\n"
               "# tracks it.\nLEVEL_REQUIRED_DPS: Dict[str, float] = {\n")
    for level in sorted(required):
        out.append(f"    {level!r}: {required[level]},\n")
    out.append("}\n")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-root", required=True,
                    help="<checkout>/docs/assets/resources")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # constants.py, loaded without running the package's __init__.py -- that
    # needs Archipelago on the path and this tool deliberately runs without it.
    # A stub package module carrying only __path__ is enough for constants.py's
    # own `from .plant_data import ...` to resolve.
    #
    # That import is why plant_data.py has to EXIST before this tool can
    # regenerate it. Nothing it reads out of constants.py depends on the table,
    # so a stale one is fine; a missing one is not, and the fix is to check the
    # last generated copy out of git.
    import importlib.util
    import types
    package = types.ModuleType("pvz2gardendless")
    package.__path__ = [os.path.join(REPO, "pvz2gardendless")]
    sys.modules.setdefault("pvz2gardendless", package)
    spec = importlib.util.spec_from_file_location(
        "pvz2gardendless.constants",
        os.path.join(REPO, "pvz2gardendless", "constants.py"))
    constants = importlib.util.module_from_spec(spec)
    sys.modules["pvz2gardendless.constants"] = constants
    spec.loader.exec_module(constants)
    game = Game(args.game_root)
    balance = json.load(open(BALANCE, encoding="utf8"))
    bridge = ap_name_to_codename()

    # The levels first: the rungs of the ladder are quantiles of what the levels
    # turn out to need, so the requirements have to be measured before the plants
    # can be banded against them.
    pressure = level_pressure(game, balance)
    tracked = tracked_levels()
    required = {}
    for level, data in pressure.items():
        if data["own_plants"] and level in tracked:
            required[level] = round(data["pressure"] / WAVE_SECONDS, 1)
    plants, excluded = plant_lawn_dps(
        game, bridge, set(constants.SINGLE_USE_PLANTS),
        set(constants.NON_DAMAGING_PLANTS))

    # Clamp: no level may ask for more than the ANSWER_FLOOR-th best plant can
    # do. See ANSWER_FLOOR for why.
    ladder = sorted((v[1] for v in plants.values()), reverse=True)
    ceiling = ladder[min(ANSWER_FLOOR, len(ladder)) - 1]
    clamped = sum(1 for r in required.values() if r > ceiling)
    required = {lvl: min(r, ceiling) for lvl, r in required.items()}
    rungs = draw_rungs(required.values())

    answers = {rung: sum(1 for v in plants.values() if v[1] >= rung)
               for rung in rungs}
    unanswerable = [lvl for lvl, req in required.items()
                    if not any(v[1] >= req for v in plants.values())]
    if unanswerable:
        raise SystemExit("no plant in the game clears these levels, so a rule "
                         f"for them could never be met: {sorted(unanswerable)}")
    summary = (
        "As generated against this checkout: %d plants have a lawn dps figure and\n"
        "%d do not. %d of the %d levels the world tracks are ones the player\n"
        "brings their own plants to, and they need %.0f to %.0f damage a second.\n"
        "Plants that clear each draw rung, easiest first: %s.\n"
        "%d levels asked for more than the %dth best plant can do and were\n"
        "clamped to its %.0f."
        % (len(plants), len(excluded), len(required), len(tracked),
           min(required.values()), max(required.values()),
           ", ".join(f"{r:.0f}dps:{answers[r]}" for r in rungs),
           clamped, ANSWER_FLOOR, ceiling))

    text = render(plants, excluded, required, rungs, summary)
    blob = {
        "note": ("Generated by tools/gen_plant_power.py. Checked by "
                 "test/plant_power_test.py against "
                 "pvz2gardendless/plant_data.py."),
        "wave_seconds": WAVE_SECONDS,
        "sun_budget": SUN_BUDGET,
        "max_copies": MAX_COPIES,
        "consumable_copies": CONSUMABLE_COPIES,
        "answer_floor": ANSWER_FLOOR,
        "band_count": BAND_COUNT,
        "draw_rungs": rungs,
        "plants": {n: {"dps": v[0], "lawn": v[1], "from": v[2],
                       "codename": bridge[n], "sun": game.sun_cost(bridge[n])}
                   for n, v in sorted(plants.items())},
        "excluded": excluded,
        "levels": {lvl: {"required_dps": r} for lvl, r in sorted(required.items())},
    }
    print(summary)
    if args.dry_run:
        return 0
    open(OUT_PY, "w", encoding="utf8").write(text)
    json.dump(blob, open(OUT_JSON, "w", encoding="utf8"), indent=1, sort_keys=True)
    print(f"wrote {OUT_PY}\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
