#!/usr/bin/env python3
"""Generate pvz2gardendless/sim_data.py: the inputs of the plant-power simulation.

    python tools/gen_sim_data.py --game-root <checkout>/pvzge_web/docs/assets/resources

Design: POWER_SIM.md. Three tables, each read from the game's own data:

  PLANTS   one behaviour record per plant item: what class of damage or effect it
           has and the numbers that drive it, taken from its PlantProps and the
           projectile it fires. Mechanics the props do not state are in SPECS
           below, each with its reason; `# [guess]` marks the ones not verified in
           play or in game code.
  ZOMBIES  hit points (the budget roll's own table, so the two agree), walk
           speed, eat DPS and the nullifier tags counter rules read.
  LEVELS   per level the player brings plants to: starting sun, the sky-sun
           dropper it actually uses, the wave timer inputs, lanes.

Record fields (absent means 0 / none):
  k   class: shooter short contact burst instant chomp sunburn producer
      utility none
  s   sun cost          cd  recharge (s)        cf  CooldownFrom (initial
                                                    charge fraction)
  d   damage per hit to the front target          x   splash damage to the rest
  t   zombies one hit can touch (front included)  i   seconds between hits/uses
  r   reach in tiles (0 = the whole lane)         b   1 if it also hits behind
  l   lanes one plant covers                      a   arm time before it acts
  life  seconds before the plant expires
  pv, pi, ps  sun produced, produce interval, first production
  hp  toughness as a wall (utility)
  ch  chill seconds per hit   fz  seconds a hit stops the zombie (expected)
  kb  tiles of knockback per hit
  sb  sun spent per shot (sunburn)
  tags: ice, instant, backward, ranged
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from gen_zombie_tiers import Bundle, Zombies, alias_map, find_table  # noqa: E402
from gen_plant_power import Game, ap_name_to_codename, tracked_levels  # noqa: E402
import gen_level_model as GLM  # noqa: E402

OUT_PY = os.path.join(REPO, "pvz2gardendless", "sim_data.py")

# Engine defaults read from the game's index.js [data].
DEFAULT_START_SUN = 50
DEFAULT_FIRST_WAVE = 15.0
DEFAULT_NEXT_HP = (0.5, 0.65)
DEFAULT_FLAG_INTERVAL = 1
DEFAULT_DROPPER = {"InitialSunDropDelay": 2, "SunCountdownBase": 6, "SunCountdownRange": 3,
                   "SunCountdownIncreasePerSun": 0.1, "SunCountdownMax": 12, "Value": 50}
DEFAULT_WALK = 0.185
DEFAULT_EAT = 100.0

# Nullifier families [user], by codename match. Checked against the zombie table
# at generation: a family matching nothing fails the tool.
NULLIFIERS = {
    "torch": lambda c, p: bool(p.get("FireDPS")),
    "wizard": lambda c, p: "wizard" in c,
    "garg": lambda c, p: p.get("ZombieSort") == "Gargantuar" or bool(p.get("SmashDamage")),
    "boombox": lambda c, p: bool(p.get("PlantFreezeRadius")),
    "skunk": lambda c, p: bool(p.get("FartStunDuration")),
    "excavator": lambda c, p: bool(p.get("ShovelDamage")),
    "bomb": lambda c, p: bool(p.get("ExplodeDamageToPlants")),
    "drone": lambda c, p: bool(p.get("PlantEatingRangeRadius")),
    "breakdancer": lambda c, p: bool(p.get("KickDistance")),
}


def f(value, default=0.0):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        nums = [v for v in value if isinstance(v, (int, float))]
        return float(nums[0]) if nums else default
    return default


def iv(p, key, default=0.0):
    """An interval with its random Additional part at its expected value."""
    if not isinstance(p.get(key), (int, float)):
        return default
    return f(p[key]) + f(p.get(key + "Additional")) / 2


class Plants:
    def __init__(self, game):
        self.g = game

    def proj(self, name):
        return self.g.proj_props.get(name) or {}

    def hit(self, name):
        """(damage, splash damage, chill s, stop s) of one projectile."""
        pr = self.proj(name)
        dmg = f(pr.get("Damage"))
        splash, chill, stop = 0.0, f(pr.get("ChillDuration")), f(pr.get("FreezeDuration"))
        for sp in pr.get("SplashDamage") or []:
            if isinstance(sp, dict):
                splash = max(splash, f(sp.get("Damage")))
                chill = max(chill, f(sp.get("ChillDuration")))
        stop = max(stop, f(pr.get("StunDuration")), f(pr.get("ButterDuration")))
        return dmg, splash, chill, stop


# Each spec: a function of (props, Plants) returning the class-specific fields.
# Common fields (s, cd, cf, life) are filled in afterwards from the props.
def shooter(proj_key="PeaType", interval="ShootInterval", count=1, t=1, r=0, b=0, l=1,
            tags=()):
    def spec(p, P):
        dmg, splash, chill, stop = P.hit(p.get(proj_key))
        out = {"k": "shooter", "d": dmg * count, "x": splash, "t": t,
               "i": iv(p, interval), "r": r, "b": b, "l": l}
        if chill:
            out["ch"] = chill
        if stop:
            out["fz"] = stop
        if tags:
            out["tags"] = list(tags)
        return out
    return spec


def fixed(**fields):
    return lambda p, P: dict(fields)


def butter_lobber(p, P):
    out = shooter("CabbageType", "ThrowInterval", t=1)(p, P)
    # Butter replaces the kernel on ChanceToButter of throws and stops the
    # zombie for its ButterDuration [data].
    _, _, _, stop = P.hit(p.get("ButterType"))
    out["fz"] = f(p.get("ChanceToButter")) * stop
    return out


SPECS = {
    # ── shooters: per-hit damage over the attack interval, whole lane ─────────
    "Peashooter": shooter(),
    "Pea Vine": shooter(),
    # Pea Pod grows up to five heads on one tile for more sun; priced as the
    # single head its card buys [guess].
    "Pea Pod": shooter(),
    "Repeater": shooter(count=2),
    "Gatling Pea": shooter(count=4),
    "Mega Gatling Pea": shooter(count=4),
    "Primal Peashooter": shooter(),
    "Fire Peashooter": shooter(),
    "Goo Peashooter": shooter(),
    "Snow Pea": shooter(tags=("ice",)),
    "Skyshooter": shooter(),
    "Shooting Starfruit": shooter(),
    "Seashooter": shooter(),
    "Guacodile": shooter(),
    "Homing Thistle": shooter(),
    "Scaredy-shroom": shooter("SporeType"),
    "Dragon Fruit": shooter(t=3),
    "Dark Matter Dragonfruit": shooter(t=3),
    # Two peas back for each one forward [data: PlantfoodPeaCountBack], normal
    # fire is one each way [guess].
    "Split Pea": fixed(k="shooter", d=20.0, t=1, i=1.425, r=0, b=1, l=1, tags=["backward"]),
    # Five directions, none of them straight ahead: two forward diagonals reach
    # the neighbouring lanes, one flies back [guess: geometry].
    "Star Fruit": fixed(k="shooter", d=20.0, t=1, i=1.425, r=0, b=1, l=1, tags=["backward"]),
    "Angel Starfruit": shooter(count=2, b=0),
    "Rotobaga": shooter(count=2),
    "Threepeater": shooter(l=3),
    "Electric Peashooter": shooter(l=3),
    "Dandelion": shooter(t=2, l=3),
    "Bowling Bulb": fixed(k="shooter", d=40.0, t=2, i=2.0, r=0, b=0, l=1),
    # Damage falls with distance: DamageScale 1 near, 0.33 mid, 0.2 far [data];
    # averaged over the lane [guess].
    "Red Stinger": fixed(k="shooter", d=15.0, t=1, i=1.875, r=0, b=0, l=1),
    "Pea Commando": shooter(count=2, interval="ShootInterval"),
    "Shadow Peashooter": shooter(),
    "Cactus": shooter(t=3),
    "Bloomerang": shooter("BoomerangType", t=3, count=2),
    "Laser Bean": fixed(k="shooter", d=40.0, t=3, i=2.775, r=0, b=0, l=1),
    "Lightning Reed": fixed(k="shooter", d=10.0, x=10.0, t=4, i=1.0, r=0, b=0, l=1),
    "Electric Currant": fixed(k="shooter", d=12.0, t=3, i=0.25, r=0, b=0, l=1),
    "Cabbage-pult": shooter("CabbageType", "ThrowInterval"),
    "Kernel-pult": butter_lobber,
    "Melon-Pult": shooter("CabbageType", "ThrowInterval", t=3),
    "Winter Melon": shooter("CabbageType", "ThrowInterval", t=3, tags=("ice",)),
    "Cantaloupe-pult": shooter("CabbageType", "ThrowInterval", t=3),
    "A.K.E.E.": shooter("CabbageType", "ThrowInterval", t=4),
    "Pepper-pult": shooter("CabbageType", "ThrowInterval", t=3),
    "Spore-shroom": shooter("CabbageType", "ShootInterval"),
    "Blooming Heart": shooter("CabbageType", "ThrowInterval"),
    "Apple Mortar": shooter("CabbageType", "ShootInterval", t=3),
    "Snowdrop": shooter("CabbageType", "ThrowInterval", tags=("ice",)),
    "Sling Pea": fixed(k="shooter", d=100.0, x=50.0, t=3, i=4.0, r=0, b=0, l=1),
    "Asparajet": fixed(k="shooter", d=20.0, t=1, i=1.825, r=0, b=0, l=1),
    "Dusk Lobber": shooter("CabbageType", "ThrowInterval", t=3),
    "Inferno": fixed(k="shooter", d=40.0, t=3, i=5.95, r=0, b=0, l=1),
    # One leaf per 2.7 s, reaching 1.5 tiles unless shadow-powered [data].
    "Nightshade": fixed(k="short", d=100.0, t=1, i=2.7, r=1.5, b=0, l=1),
    "Pea-nut": shooter(),
    "Ampereum": shooter("BoltType"),
    "Turkey-pult": fixed(k="none"),
    # ── short reach ─────────────────────────────────────────────────────────
    "Puff-shroom": shooter(r=3),
    "Fume-Shroom": fixed(k="short", d=40.0, t=3, i=2.5, r=5.5, b=0, l=1),
    "Bonk Choy": fixed(k="short", d=15.0, t=1, i=0.3, r=1, b=1, l=1, tags=["backward"]),
    "Bamboo Shoot": fixed(k="short", d=30.0, t=1, i=0.3, r=4, b=0, l=1),
    "Parsnip": fixed(k="short", d=70.0, t=2, i=0.8, r=1, b=0, l=1),
    # 15 damage a hit, 45 on every fourth to sixth [data], averaged [guess].
    "Phat Beet": fixed(k="short", d=21.0, t=3, i=1.0, r=1, b=1, l=1, tags=["backward"]),
    "Wasabi Whip": fixed(k="short", d=40.0, x=20.0, t=2, i=0.6, r=2.5, b=0, l=1),
    "Snap Dragon": fixed(k="short", d=30.0, t=3, i=1.925, r=2, b=0, l=1),
    "Cold Snapdragon": fixed(k="short", d=30.0, t=3, i=1.925, r=2, b=0, l=1, ch=10.0,
                             tags=["ice"]),
    "Celery Stalker": fixed(k="short", d=25.0, t=1, i=1.0, r=1, b=1, l=1, tags=["backward"]),
    "Snap Pea": shooter(),
    "Holly Knight": fixed(k="short", d=20.0, t=1, i=1.0, r=2, b=0, l=1),
    "Gloom-shroom": fixed(k="short", d=100.0, t=3, i=1.0, r=1, b=1, l=1, tags=["backward"]),
    "Gloom Vine": fixed(k="short", d=45.0, t=3, i=2.775, r=1, b=1, l=1, tags=["backward"]),
    "Pyre Vine": fixed(k="short", d=20.0, t=3, i=1.0, r=2, b=0, l=1),
    "Vamporcini": fixed(k="short", d=40.0, t=1, i=1.0, r=1, b=0, l=1),
    # AttackDPS 150 for 5 s, then 6 s reloading [data].
    "Fire Gourd": fixed(k="short", d=68.0, t=2, i=1.0, r=5, b=0, l=1),
    # ── contact: hurts what crosses its tile ─────────────────────────────────
    "Spikeweed": fixed(k="contact", d=10.0, t=3, i=0.5),
    "Spikerock": fixed(k="contact", d=20.0, t=3, i=0.5),
    "Iceweed": fixed(k="contact", d=10.0, t=3, i=0.5, ch=3.0, tags=["ice"]),
    # ── periodic big hits ─────────────────────────────────────────────────────
    "Coconut Cannon": fixed(k="burst", d=900.0, x=300.0, t=3, i=15.0, r=0, l=1),
    "Banana Launcher": fixed(k="burst", d=1200.0, x=1200.0, t=3, i=20.0, r=0, l=1),
    "Missile Toe": fixed(k="burst", d=1200.0, x=1200.0, t=3, i=20.0, r=0, l=1, fz=5.0,
                         tags=["ice"]),
    "Citron": fixed(k="burst", d=800.0, t=1, i=7.0, r=0, l=1),
    # Grows through three stages (7.5, 10, 15 s) to a 900 hit [data].
    "Strawburst": fixed(k="burst", d=900.0, x=900.0, t=3, i=32.5, r=0, l=1),
    "Electric Blueberry": fixed(k="burst", d=5000.0, t=1, i=12.0, r=0, l=1),
    "Meteor Flower": fixed(k="burst", d=200.0, x=100.0, t=3, i=7.0, r=0, l=1),
    # ── instants: a use per recharge, paid in sun ────────────────────────────
    "Cherry Bomb": fixed(k="instant", d=1800.0, t=99, r=1.5, l=3, tags=["instant"]),
    "Doom-shroom": fixed(k="instant", d=2700.0, t=99, r=3, l=3, tags=["instant"]),
    "Jalapeno": fixed(k="instant", d=1800.0, t=99, r=0, l=1, tags=["instant"]),
    "Chilly Pepper": fixed(k="instant", d=1200.0, t=99, r=0, l=1, fz=10.0,
                           tags=["instant", "ice"]),
    "Potato Mine": fixed(k="instant", d=1800.0, t=1, r=0.5, l=1, a=14.0, tags=["instant"]),
    "Primal Potato Mine": fixed(k="instant", d=2700.0, t=99, r=1.5, l=3, a=6.0,
                                tags=["instant"]),
    "Squash": fixed(k="instant", d=1800.0, t=1, r=1.5, l=1, tags=["instant"]),
    "Escape Root": fixed(k="instant", d=1800.0, t=1, r=0.5, l=1, a=10.0, tags=["instant"]),
    "Grapeshot": fixed(k="instant", d=1800.0, x=200.0, t=5, r=1.5, l=3, tags=["instant"]),
    "Grimrose": fixed(k="instant", d=1800.0, t=1, r=1.5, l=1, tags=["instant"]),
    "Hypno-shroom": fixed(k="instant", d=99999.0, t=1, r=0.5, l=1, tags=["instant"]),
    "Ice Bloom": fixed(k="instant", d=200.0, x=50.0, t=99, r=1.5, l=3, fz=10.0,
                       tags=["ice"]),
    "Ghost Pepper": fixed(k="instant", d=1050.0, t=3, r=1, l=1),
    "Lava Guava": fixed(k="instant", d=200.0, t=3, r=1, l=1),
    "Noctarine": fixed(k="instant", d=800.0, t=1, r=1, l=1),
    "Shadow-shroom": fixed(k="instant", d=900.0, t=1, r=0.5, l=1),
    # ── eat one zombie, then chew ────────────────────────────────────────────
    "Chomper": fixed(k="chomp", i=17.0, r=1, x=100.0, tags=["instant"]),
    "Toadstool": fixed(k="chomp", i=30.0, r=3.5, x=50.0, tags=["instant"]),
    # Turns one zombie into a Puff-shroom per cycle, anywhere in reach [guess].
    "Witch Hazel": fixed(k="chomp", i=17.75, r=0, x=1200.0, tags=["instant"]),
    "Caulipower": fixed(k="chomp", i=12.0, r=0, x=0.0),
    # ── sun paid per shot ────────────────────────────────────────────────────
    "Magnifying Grass": fixed(k="sunburn", d=550.0, t=1, i=0.333, r=0, l=1, sb=50.0),
    # ── producers ────────────────────────────────────────────────────────────
    "Sunflower": lambda p, P: produce(p, "SunValue"),
    "Twin Sunflower": lambda p, P: produce(p, "SunValue"),
    "Primal Sunflower": lambda p, P: produce(p, "SunValue"),
    "Moonflower": lambda p, P: produce(p, "SunValue"),
    "Shine Vine": lambda p, P: produce(p, "ProduceSunValue"),
    # 25 sun per 32-36 s by day; grows to more later [guess: growth unmodelled].
    "Sun-Shroom": lambda p, P: produce(p, "SunValue"),
    # ── utility ──────────────────────────────────────────────────────────────
    "Wall-nut": lambda p, P: wall(p),
    "Tall-nut": lambda p, P: wall(p),
    "Primal Wall-nut": lambda p, P: wall(p),
    "Pumpkin": lambda p, P: wall(p),
    "Spinapple": lambda p, P: wall(p),
    "Sweet Potato": lambda p, P: wall(p),
    "Resistant Radish": lambda p, P: wall(p),
    "Infi-nut": lambda p, P: wall(p),
    "Murkadamia Nut": lambda p, P: wall(p),
    "Endurian": lambda p, P: wall(p),
    "Lychee": lambda p, P: wall(p),
    "Mirror-nut": lambda p, P: wall(p),
    "Explode-O-Nut": lambda p, P: wall(p),
    "Bamboozle": lambda p, P: wall(p),
    "Hot Date": lambda p, P: wall(p),
    "Solar Tomato": lambda p, P: wall(p),
    "Gumnut": fixed(k="utility", hp=4000.0),
    "Chard Guard": fixed(k="utility", hp=1500.0, kb=3.0),
    "Stunion": fixed(k="utility", fz=12.0, r=1.5, i=0.0),
    "Iceberg Lettuce": fixed(k="utility", fz=10.0, r=0.5, i=0.0, tags=["ice"]),
    "Chili Bean": fixed(k="utility", fz=10.0, r=0.5, i=0.0),
    "Garlic": fixed(k="utility", fz=2.1, r=0.5, i=0.0),
    "Spring Bean": fixed(k="utility", kb=1.0, i=10.0, r=0.5),
    "Hurrikale": fixed(k="utility", kb=2.0, r=0, i=0.0),
    "Loquanado": fixed(k="utility", kb=1.5, r=0, i=0.0),
    # Sap halves walk speed [data: sapflingCD, *0.5]; lasts 15 s on the tile.
    "Sap-fling": fixed(k="utility", ch=15.0, i=2.925, r=0),
    "Shrinking Violet": fixed(k="utility", ch=10.0, r=1.5, i=0.0),
    "Stallia": fixed(k="utility", ch=12.0, r=1.5, i=0.0),
    "Thyme Warp": fixed(k="utility", fz=5.0, r=0, l=5, i=0.0),
    # Freezes every zombie on the board for FreezeDuration [data].
    "Ice-shroom": fixed(k="utility", fz=5.0, r=0, l=5, i=0.0, tags=["ice"]),
}

# No modelled effect, with the reason. Everything the bridge names and SPECS
# does not must be here, or the tool fails.
NONE = {
    "Buttercup": "butter only when eaten: reactive, not an attack [user]",
    "Cran-Jelly": "DPS 3000 is its jelly's, mechanic unverified [guess]",
    "Torchwood": "boosts peas; not an attack of its own",
    "Aloe": "heals", "Heavenly Peach": "heals", "Intensive Carrot": "revives",
    "Umbrella Leaf": "blocks lobbed projectiles", "Magnet-shroom": "removes metal",
    "Marigold": "coins", "Gold Bloom": "one-off sun, unmodelled", "Sun Bean": "sun from hits",
    "Solar Sage": "enlightens", "Plantern": "reveals", "Moon Bean": "shadow bomb",
    "Power Lily": "plant food", "Blover": "blows flyers (hazard rule)",
    "Perfume-shroom": "dino counter (hazard rule)", "Grave Buster": "graves",
    "Hot Potato": "melts ice", "Lily Pad": "water", "Tangle Kelp": "water only",
    "Sea-shroom": "water only", "E.M. Peach": "stuns machines only", "Zoybean Pod": "potions",
    "Floawer Pot": "pot", "Glowkengi": "unmodelled", "Gold Leaf": "gold tile",
    "Imitater": "copies a packet", "Tile Turnip": "power tile",
    "Atomic Bombegranate": "no props",
}


def produce(p, key):
    return {"k": "producer", "pv": f(p.get(key)), "pi": iv(p, "ProduceInterval"),
            "ps": iv(p, "ProduceCountdownStart")}


def wall(p):
    return {"k": "utility", "hp": f(p.get("Toughness")) + f(p.get("ArmorToughness"))}


def plant_records(game, bridge):
    P = Plants(game)
    out, problems = {}, []
    for name, cn in sorted(bridge.items()):
        p = game.plant_props.get(cn) or {}
        if name.endswith("-mint"):
            out[name] = {"k": "none", "why": "Plant Power mint, one-use family boost"}
            continue
        if name in NONE:
            out[name] = {"k": "none", "why": NONE[name]}
            continue
        spec = SPECS.get(name)
        if spec is None:
            problems.append(name)
            continue
        rec = spec(p, P)
        rec.setdefault("s", f(p.get("SunCost")))
        rec.setdefault("cd", f(p.get("Cooldown")))
        # Recharge left at level start is CooldownFrom * Cooldown (coolStart);
        # PlantProps defaults CooldownFrom to 0 [data].
        rec.setdefault("cf", f(p.get("CooldownFrom"), 0.0))
        life = f(p.get("LifeSpan")) or f(p.get("Lifespan"))
        if life:
            rec.setdefault("life", life)
        if game.water_only(cn):
            rec = {"k": "none", "why": "water only"}
        out[name] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()}
    if problems:
        raise SystemExit(f"plants with no SPECS or NONE entry: {problems}")
    unknown = (set(SPECS) | set(NONE)) - set(bridge)
    if unknown:
        raise SystemExit(f"SPECS/NONE name plants the bridge does not: {sorted(unknown)}")
    return out


# ── levels ───────────────────────────────────────────────────────────────────

def level_modules(root):
    """{alias: objdata} of the packed LevelModules table."""
    with open(os.path.join(root, "config.json"), encoding="utf8") as fh:
        cfg = json.load(fh)
    found = {}

    def walk(node):
        if isinstance(node, list):
            if (len(node) >= 3 and node[1] == "LevelModules" and isinstance(node[2], dict)
                    and "objects" in node[2]):
                for obj in node[2]["objects"]:
                    for alias in obj.get("aliases") or []:
                        found[alias] = obj.get("objdata") or {}
            for item in node:
                walk(item)
    for pack in cfg.get("packs", {}):
        path = os.path.join(root, "import", pack[:2], pack + ".json")
        if os.path.isfile(path):
            with open(path, encoding="utf8") as fh:
                text = fh.read()
            if '"LevelModules"' in text:
                walk(json.loads(text))
    if not found:
        raise SystemExit("LevelModules table not found in any pack")
    return found


RTID_FULL = re.compile(r"RTID\(([^@)]+)@([^)]*)\)")


def level_sim(level, modules):
    definition = level.data("LevelDefinition")
    manager = level.manager()
    dropper = None
    for mod in definition.get("Modules") or []:
        m = RTID_FULL.match(mod) if isinstance(mod, str) else None
        if not m or "SunDropper" not in m.group(1):
            continue
        src = modules if m.group(2) == "LevelModules" else {
            a: (o.get("objdata") or {}) for a, o in level.by_alias.items()}
        dropper = dict(DEFAULT_DROPPER)
        dropper.update({k: v for k, v in (src.get(m.group(1)) or {}).items()
                        if isinstance(v, (int, float, bool))})
    night = "Night" in (GLM.rt(definition.get("StageModule")) or "")
    suppress = str(definition.get("SuppressSunSpawn")).lower() == "true"
    if dropper and (suppress or (dropper.get("ListenToLawn") and night)):
        dropper = None
    drop = None
    if dropper:
        drop = [f(dropper["InitialSunDropDelay"]), f(dropper["SunCountdownBase"]),
                f(dropper["SunCountdownRange"]), f(dropper["SunCountdownIncreasePerSun"]),
                f(dropper["SunCountdownMax"]), f(dropper["Value"])]
    waves = manager.get("Waves") or []
    flag = manager.get("FlagWaveInterval")
    flag = min(len(waves), int(flag)) if isinstance(flag, (int, float)) and flag else \
        DEFAULT_FLAG_INTERVAL
    lo = f(manager.get("MinNextWaveHealthPercentage"), DEFAULT_NEXT_HP[0])
    hi = f(manager.get("MaxNextWaveHealthPercentage"), DEFAULT_NEXT_HP[1])
    return {
        "sun0": f(definition.get("StartingSun"), DEFAULT_START_SUN),
        "drop": drop,
        "first": f(manager.get("ZombieCountdownFirstWaveSecs"), DEFAULT_FIRST_WAVE),
        "flag": flag,
        "next": round((lo + hi) / 2, 3),
        "night": night,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.expanduser(args.game_root)

    game = Game(root)
    bridge = ap_name_to_codename()
    plants = plant_records(game, bridge)

    zombies_src = Zombies(find_table(root, "ZombieTypes"), find_table(root, "ZombieProps"),
                          find_table(root, "ArmorProps"))
    sys.path.insert(0, REPO)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "level_model", os.path.join(REPO, "pvz2gardendless", "level_model.py"))
    lm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lm)
    model = lm.load()
    zombies, family_hits = {}, {k: 0 for k in NULLIFIERS}
    for cn, z in sorted(model["zombies"].items()):
        p = zombies_src.prop(cn)
        tags = [k for k, test in NULLIFIERS.items() if test(cn, p)]
        if p.get("CannotBeSwallowedByChomper"):
            tags.append("noswallow")
        for k in tags:
            if k in family_hits:
                family_hits[k] += 1
        zombies[cn] = {"hp": z["hp"], "walk": f(p.get("WalkSPS"), DEFAULT_WALK),
                       "eat": f(p.get("EatDPS"), DEFAULT_EAT)}
        if tags:
            zombies[cn]["tags"] = tags
    # A family can match nothing when no tracked level spawns it (eighties_skunk
    # and sky_drone today); its rule then never fires. Reported, not fatal.
    empty = [k for k, n in family_hits.items() if not n]
    if empty:
        print(f"note: nullifier families no tracked level spawns: {empty}")

    modules = level_modules(root)
    bundle, packed = Bundle(root), GLM.PackedLevels(root)
    levels = {}
    for level_id, lv in sorted(model["levels"].items()):
        if not lv.get("own_plants") or lv.get("bespoke") or lv.get("generated"):
            continue
        objects = GLM.level_objects(bundle, packed, level_id)
        if not objects:
            continue
        levels[level_id] = level_sim(GLM.Level(level_id, objects), modules)

    blob = {"game": model.get("game"), "plants": plants, "zombies": zombies,
            "levels": levels}
    kinds = {}
    for rec in plants.values():
        kinds[rec["k"]] = kinds.get(rec["k"], 0) + 1
    no_sky = sum(1 for lv in levels.values() if not lv["drop"])
    summary = (f"{len(plants)} plants ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))}); "
               f"{len(zombies)} zombies, nullifiers {family_hits}; "
               f"{len(levels)} levels, {no_sky} without sky sun.")
    print(summary)
    if args.dry_run:
        return 0
    text = ('"""\nPvZ2 Gardendless: inputs of the plant-power simulation (POWER_SIM.md).\n\n'
            "GENERATED by tools/gen_sim_data.py; do not hand edit. Record fields are\n"
            "documented in that tool's docstring.\n\n" + summary + '\n"""\n\n'
            "from typing import Any, Dict\n\n"
            f"GAME_DATA_VERSION = {model.get('game')!r}\n\n"
            f"SIM_DATA: Dict[str, Any] = {json.dumps(blob, sort_keys=True, indent=1)}\n")
    text = text.replace(": true", ": True").replace(": false", ": False").replace(": null", ": None")
    with open(OUT_PY, "w", encoding="utf8") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT_PY, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
