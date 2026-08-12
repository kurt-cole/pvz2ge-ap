"""
Static world-shape data shared across items.py, locations.py, regions.py and
rules.py: identifiers, world lists, and the plant sets used for logic gating.
"""

from typing import Dict, List

GAME_NAME = "PvZ2 Gardendless"
BASE_ID   = 0xD1A2B3C4

# Worlds that need a key item to access (Ancient Egypt is always free).
# ORDER IS LOAD-BEARING: items.py derives each World Key's item ID from this
# list's index, so reordering or inserting renumbers keys for every existing
# seed. Append only.
KEYED_WORLDS = [
    "Pirate Seas", "Wild West", "Far Future", "Dark Ages",
    "Big Wave Beach", "Frostbite Caves", "Lost City",
    "Kongfu Temple", "Neon Mixtape Tour", "Jurassic Marsh", "Modern Day", "Aerial Fortress",
]

# ── Main worlds ───────────────────────────────────────────────────────────────
# Every main world mapped to the regions that make it up, in game order.
# Ancient Egypt is the only multi-region entry: it is split into sequential
# checkpoints so its 35 levels are not all flatly reachable (see regions.py).
# Regions NOT listed here -- Tutorial, the side paths, Shop -- are not part of
# any world and are always built.
WORLD_REGIONS: Dict[str, List[str]] = {
    "Ancient Egypt":     ["Ancient Egypt", "Ancient Egypt Mid1",
                          "Ancient Egypt Mid2", "Ancient Egypt Late"],
    "Pirate Seas":       ["Pirate Seas"],
    "Wild West":         ["Wild West"],
    "Far Future":        ["Far Future"],
    "Dark Ages":         ["Dark Ages"],
    "Big Wave Beach":    ["Big Wave Beach"],
    "Frostbite Caves":   ["Frostbite Caves"],
    "Lost City":         ["Lost City"],
    "Kongfu Temple":     ["Kongfu Temple"],
    "Neon Mixtape Tour": ["Neon Mixtape Tour"],
    "Jurassic Marsh":    ["Jurassic Marsh"],
    "Aerial Fortress":   ["Aerial Fortress"],
    "Modern Day":        ["Modern Day"],
}

ALL_WORLD_REGIONS = {r for regions in WORLD_REGIONS.values() for r in regions}

# ── Sphere depth ──────────────────────────────────────────────────────────────
# A world key used to open all 44-53 of its levels at once, so a whole world
# landed in one sphere and fill had no reason to spread progression through it.
# regions.py now cuts each world into these three sequential stretches, in the
# order its levels are defined, and rules.py gates the later two on how many
# progression plants are held.
#
# Counted against the 58 plants that are progression items (see LOGIC_PLANTS) --
# "useful" plants are not tracked in CollectionState, so they cannot be counted.
# 12 of 58 for the deepest stretch of any world leaves a wide margin; the point
# is to layer the fill, not to make late levels a grind.
WORLD_STRETCHES = ("", " Mid", " Late")
STRETCH_PLANTS = {" Mid": 6, " Late": 12}

# Ancient Egypt is not cut up by that code. It carries a bespoke four-region
# split declared in locations.py, gated on holding a sun producer and a cheap
# attacker, and it is the one world reachable with no items at all -- so its
# opening stretch has to stay ungated or a seed has nowhere to begin. What it
# lacked was any escalation: all three of its gates asked for the same thing,
# which put its 44 levels in one sphere behind that single rule. These add a
# plant count to the later two, on top of the sun-and-attacker requirement.
EGYPT_STRETCH_PLANTS = {"Ancient Egypt Mid2": 3, "Ancient Egypt Late": 6}

# Worlds every seed keeps, whatever the world-selection options say. Ancient
# Egypt is the only world reachable with no items at all, so it is what
# sphere 1 is made of; Modern Day holds the victory location. A seed missing
# either has no opening or no ending.
ALWAYS_ENABLED_WORLDS = ["Ancient Egypt", "Modern Day"]

# The worlds enabled_worlds / world_count actually choose between. Modern Day
# is not offered -- it is the goal world, and it is gated by the world-goal
# count rather than by being in or out of the pool.
SELECTABLE_WORLDS = [w for w in WORLD_REGIONS if w != "Modern Day"]
OPTIONAL_WORLDS   = [w for w in SELECTABLE_WORLDS if w not in ALWAYS_ENABLED_WORLDS]

# World Key item name -> world, so the pool builder can drop the keys of
# worlds this slot did not enable. Built from KEYED_WORLDS rather than by
# slicing " Key" off the item names, which would break on a world whose name
# ever ends in "Key".
KEY_NAME_TO_WORLD = {f"{world} Key": world for world in KEYED_WORLDS}

# Sequential sphere-1 gating for Ancient Egypt (see checkpoint split in
# regions.py): each checkpoint requires at least one of these sun producers
# and one of these cheap attackers to be held, so generation logic doesn't
# treat the whole 35-level world as reachable with zero items. Sourced from
# the game's own PlantProperties data (Family + SunCost).
# Only genuine passive sun producers. The game's Family=="Sun" tag is wider
# than that and would let the gate pass on a plant that generates no usable
# sun: Magnifying Grass consumes sun to fire, Sun Bean / Moon Bean / Toadstool
# only convert damage or eaten zombies into sun, Plantern just reveals fog,
# and Gold Bloom is a 0-cost conveyor-only plant.
SUN_PRODUCER_PLANTS = [
    "Sunflower", "Sun-Shroom", "Twin Sunflower", "Primal Sunflower",
    "Solar Tomato", "Solar Sage",
]

# SunCost <= 150 among damage-dealing Family types. Excludes a handful of
# 0-cost/utility plants the game misclassifies as attackers (Iceberg
# Lettuce, Hot Potato, Sea-shroom, Puff-shroom, Garlic, Grimrose) and
# Tangle Kelp, which is water-only and unusable on Ancient Egypt's terrain.
CHEAP_ATTACKER_PLANTS = [
    "E.M. Peach", "Potato Mine", "Scaredy-shroom", "Celery Stalker",
    "Chili Bean", "Escape Root", "Explode-O-Nut", "Moonflower",
    "Primal Potato Mine", "Shadow-shroom", "Shrinking Violet", "Squash",
    "Ghost Pepper", "Lava Guava", "Nightshade", "Cabbage-pult",
    "Intensive Carrot", "Kernel-pult", "Peashooter", "Spikeweed",
    "Vamporcini", "Fume-Shroom", "Gloom Vine", "Guacodile", "Hypno-shroom",
    "Jalapeno", "Lightning Reed", "Pea Pod", "Pea Vine", "Split Pea",
    "Blooming Heart", "Bonk Choy", "Cherry Bomb", "Chomper", "Dusk Lobber",
    "Electric Blueberry", "Electric Currant", "Grapeshot", "Iceweed",
    "Parsnip", "Phat Beet", "Red Stinger", "Skyshooter", "Snap Dragon",
    "Snow Pea", "Spore-shroom", "Star Fruit",
]

# Plants a world needs on top of its key item. rules.py ANDs one has_any()
# per entry onto that world's key requirement, so adding a world here is all
# it takes to gate it -- and its plants are picked up by LOGIC_PLANTS below
# automatically.
# Plants that do not stay on the lawn: consumed when they go off, or gone on a
# timer. They are perfectly good attackers, which is why they stay in
# CHEAP_ATTACKER_PLANTS for the Ancient Egypt logic gate -- but they are a poor
# GUARANTEED STARTING PLANT, which exists so a player always has something that
# can hold a lane. A run whose only plant is Potato Mine has to replant on
# every single zombie.
#
# DERIVED FROM GAME DATA, not judgement. Every plant here is one the game's own
# _PLANTPROPERTIES sheet marks `IsConsumable` (consumed on use) or gives a
# `Lifetime` (expires on its own -- this is what catches Ghost Pepper, which is
# not consumable but does vanish). Peashooter has neither; Squash has
# IsConsumable; Ghost Pepper has Lifetime.
#
# To regenerate after a game update, read
# assets/resources/import/3d/3d9ce08d-*.json (the _PLANTPROPERTIES table) and
# intersect those two flags with CHEAP_ATTACKER_PLANTS. Three of the plants
# below have no sheet at all -- Scaredy-shroom, Vamporcini and Skyshooter --
# and are treated as persistent, which matches what they do.
SINGLE_USE_PLANTS = [
    "Cherry Bomb", "Chili Bean", "E.M. Peach", "Escape Root", "Ghost Pepper",
    "Grapeshot", "Hypno-shroom", "Jalapeno", "Lava Guava", "Potato Mine",
    "Primal Potato Mine", "Shadow-shroom", "Shrinking Violet", "Squash",
]

# Plants that persist but deal no damage of their own -- support and defence.
# Also unfit as the sole starting plant for the same reason: the guarantee is
# meant to be something that can actually kill a zombie. Judgement rather than
# data; the game has no "deals no damage" flag.
NON_DAMAGING_PLANTS = [
    "Explode-O-Nut",    # a wall; only hurts what is already eating it
    "Moonflower",       # shadow support, powers other plants
]

# What generate_early() may hand a player for free. A cheap attacker that
# persists on the lawn and does damage on its own.
STARTER_PLANTS = [
    plant for plant in CHEAP_ATTACKER_PLANTS
    if plant not in set(SINGLE_USE_PLANTS) | set(NON_DAMAGING_PLANTS)
]

# Both lists must be drawn from CHEAP_ATTACKER_PLANTS -- a name that is not
# would filter nothing and quietly leave the plant it was meant to exclude in
# the starter pool.
_unknown_excluded = (set(SINGLE_USE_PLANTS) | set(NON_DAMAGING_PLANTS)) - set(CHEAP_ATTACKER_PLANTS)
if _unknown_excluded:
    raise ValueError("excluded starter plants are not cheap attackers: "
                     f"{sorted(_unknown_excluded)}")

# Plants that answer the Jester (dark_juggler), who returns projectiles at
# your own lawn. Two kinds qualify, and both come out of the game's data:
#
#  - anything that lobs. The projectile DamageFlags split every attack into
#    "shooter" (straight down the lane, which is what he reverses) and
#    "lobbed" (arcs over him). Lobbers are not in the reversible set at all.
#  - the handful of straight shooters the game explicitly marks
#    CannotBeReversedByJester on their projectile: electricpea and
#    magnifying_grass are the two with an Archipelago item.
#
# Only entries that exist as items are listed. Thirteen more qualify in the
# game -- Holly Knight, Tumbleweed, Turkey-pult and friends -- but they are
# not in the item pool, so naming them would gate on something unobtainable.
JESTER_COUNTER_PLANTS = [
    "A.K.E.E.", "Apple Mortar", "Banana Launcher", "Bloomerang",
    "Blooming Heart", "Bowling Bulb", "Buttercup", "Cabbage-pult",
    "Coconut Cannon", "Dandelion", "Dusk Lobber", "Electric Peashooter",
    "Escape Root", "Grapeshot", "Kernel-pult", "Magnifying Grass",
    "Melon-Pult", "Missile Toe", "Pepper-pult", "Sap-fling", "Spore-shroom",
    "Strawburst", "Winter Melon",
]

# Plants a world needs on top of its key, as a list of requirements: the
# player needs at least one plant from EACH list, so a world can ask for more
# than one thing at once. rules.py ANDs them onto that world's entrance.
WORLD_ENTRY_PLANTS = {
    "Big Wave Beach":  [["Lily Pad"]],
    "Frostbite Caves": [["Hot Potato", "Pepper-pult", "Fire Peashooter"]],
    "Jurassic Marsh":  [["Perfume-shroom"]],
    # Dark Ages is permanently night: no sun falls, so a sun producer is the
    # difference between playing the world and standing still. On top of that
    # the Jester returns straight-line shots, so something that gets round him
    # is needed too.
    "Dark Ages":       [SUN_PRODUCER_PLANTS, JESTER_COUNTER_PLANTS],
}

# Every plant named by an access rule anywhere in rules.py. items.py forces
# each of these to progression, because AP only tracks advancement items in
# CollectionState.prog_items -- state.has()/has_any() is permanently False for
# a "useful" item, so a rule naming one silently loses that option.
# This set is derived from the rule data rather than maintained by hand: the
# hand-maintained version is what left Pepper-pult and Fire Peashooter at
# "useful" while the Frostbite Caves rule named them, quietly collapsing that
# rule to "Hot Potato only".
LOGIC_PLANTS = (
    set(SUN_PRODUCER_PLANTS)
    | set(CHEAP_ATTACKER_PLANTS)
    | {plant
       for requirements in WORLD_ENTRY_PLANTS.values()
       for group in requirements
       for plant in group}
)

# Shop commodities, taken verbatim from the game's store data. Only the
# one-time purchases are usable as checks -- the Gem/Coin/Zen bundles in the
# same table are repeatable, so they can be bought over and over and would
# not be valid locations. Codenames are used as-is so the location name the
# client builds from CommodityName always matches exactly.
# Deliberately excluded: imitater, darkmatterdragonfruit, snappea and
# shootingstarfruit are priced in tickets (1000 each). Tickets only come from
# Pinata prizes and in-level drops worth 10 apiece, there is no ticket bundle
# in the store, and Archipelago has no ticket item -- so those four would be
# ~400 pickups of pure grind. Everything kept below is priced in gems, which
# AP's filler actually supplies.
SHOP_PLANT_COMMODITIES = [
    'iceweed', 'snowdrop', 'jalapeno', 'starfruit', 'mirrornut',
    'pinkstarfruit', 'asparagus', 'hypnoshroom', 'peanut', 'homingthistle',
    'chomper', 'hurrikale', 'lavaguava', 'toadstool', 'powerlily',
    'bamboozle', 'firepeashooter', 'cactus', 'electricblueberry',
    'caulipower', 'jackolantern', 'grapeshot', 'escaperoot', 'explodeonut',
    'applemortar', 'wasabiwhip', 'floawerPot', 'coldsnapdragon',
    'missiletoe', 'electricpeashooter', 'zoybeanpod', 'shrinkingviolet',
    'pyrevine', 'cranjelly',
]  # 34, all gem-priced

SHOP_UPGRADE_COMMODITIES = [
    'upgrade_sunshovel_lvl3', 'upgrade_8_slots', 'upgrade_pf_slots_lvl2',
    'upgrade_starting_sun_lvl2', 'upgrade_manual_mowers_2',
]  # 5, all gem-priced

SHOP_COMMODITIES = SHOP_PLANT_COMMODITIES + SHOP_UPGRADE_COMMODITIES
SHOP_REGION = "Shop"

# ── Permanent upgrades ────────────────────────────────────────────────────────
# The game's fourteen permanent upgrades, as (item name, game codename), in
# the game's own UpgradeEnum order. The codenames are what the save file keys
# currentPlayer.upgradeProps by, and what unlockUpgrade() takes.
#
# ORDER IS LOAD-BEARING for the same reason as KEYED_WORLDS: items.py numbers
# these from the end of the trap block. Append only.
#
# Nine are level rewards and five are store purchases, which is only about
# where their *location* is -- every one of them is an item either way.
#
# Grouped as (item name, [codenames granted in this order]). The multi-level
# ones are PROGRESSIVE rather than one item per level, because the game's
# upgrade loop simply sums whatever is held:
#   starting sun +25 each   plant food slots +1 each, base 3 cap 5
#   seed slots   +1 each, base 6 cap 8
#   sun shovel   +0.25 rate each   manual mower +1 each
# lvl1 and lvl2 have identical effects, so receiving "Sun Shovel III" first
# would be indistinguishable from receiving "Sun Shovel I" first -- separate
# items would imply an ordering the game does not have, and would show up on
# a tracker as holding III while missing I and II. The last three are one-shot
# flags with nothing to progress through, so they stay single items.
UPGRADE_GROUPS = [
    ("Progressive Starting Sun",    ["upgrade_starting_sun_lvl1",
                                     "upgrade_starting_sun_lvl2"]),
    ("Progressive Plant Food Slot", ["upgrade_pf_slots_lvl1",
                                     "upgrade_pf_slots_lvl2"]),
    ("Progressive Seed Slot",       ["upgrade_7_slots", "upgrade_8_slots"]),
    ("Progressive Sun Shovel",      ["upgrade_sunshovel_lvl1",
                                     "upgrade_sunshovel_lvl2",
                                     "upgrade_sunshovel_lvl3"]),
    ("Progressive Manual Mower",    ["upgrade_manual_mowers_1",
                                     "upgrade_manual_mowers_2"]),
    ("Wall-nut First Aid",          ["upgrade_wallnut_firstaid"]),
    ("Plant Food Refresh",          ["upgrade_pf_refresh"]),
    ("Sky Shield",                  ["upgrade_sky_shield"]),
]

# Total upgrade items in a shuffled pool: 8 distinct names, 14 copies.
UPGRADE_ITEM_COUNT = sum(len(cns) for _, cns in UPGRADE_GROUPS)


def shop_location_name(commodity: str) -> str:
    return f"Shop: {commodity}"


# Which world a side path is entered from. A side path is not a separate place
# you can walk to -- it branches off a specific level on a specific world map,
# so it is unreachable until that world is. These were all sitting in sphere 1,
# which meant logic thought a Far Future side path was enterable from Egypt.
#
# Read out of the game rather than guessed. Three sources, in order of
# authority: the world-map branch nodes (a map entry like [6,"25-1",
# ["conceal0"]] places that side path at level 25 of the map it appears on),
# the Epic Quest tables that group each side path's levels under an
# epic_<world> codename, and for Rhythm the level's own "#comment": "Iceage 1".
#
# Appease spans two worlds -- appease1_* branches from Ancient Egypt and
# appease2_* from Frostbite Caves -- and is tied to Egypt, the earlier of the
# two, so the whole side path opens when its first half does.
SIDE_PATH_WORLD = {
    "Aloe Sidepath":            "Lost City",
    "Appease Sidepath":         "Ancient Egypt",
    "Atombomb Sidepath":        "Kongfu Temple",
    "Bloominghearts Sidepath":  "Neon Mixtape Tour",
    "Buttercup Sidepath":       "Pirate Seas",
    "Conceal Sidepath":         "Modern Day",
    "Doomshroom Sidepath":      "Dark Ages",
    "Electriccurrant Sidepath": "Wild West",
    "Enlighten Sidepath":       "Lost City",
    "Ghostpepper Sidepath":     "Big Wave Beach",
    "Gloomshroom Sidepath":     "Modern Day",
    "Goldbloom Sidepath":       "Modern Day",
    "Hotdate Sidepath":         "Frostbite Caves",
    "Icebloom Sidepath":        "Big Wave Beach",
    "Iceshroom Sidepath":       "Dark Ages",
    "Meteorflower Sidepath":    "Jurassic Marsh",
    "Parsnip Sidepath":         "Big Wave Beach",
    "Plantern Sidepath":        "Dark Ages",
    "Reinforce Sidepath":       "Far Future",
    "Rhythm Sidepath":          "Frostbite Caves",
    "Sapfling Sidepath":        "Wild West",
    "Seashooter Sidepath":      "Big Wave Beach",
    "Solartomato Sidepath":     "Far Future",
    "Squash Sidepath":          "Ancient Egypt",
    "Strawburst Sidepath":      "Neon Mixtape Tour",
    "Sweetpotato Sidepath":     "Frostbite Caves",
    "Umbrellaleaf Sidepath":    "Modern Day",
    "Vamporcini Sidepath":      "Dark Ages",
}

# The seven side paths the game data ties to no world: Sandbox, the Bank Theft
# levels, Epic Beghouled, FloawerPot, the Mixed Danger Room, Reinforcemint and
# ShootingStarFruit. They are standalone content reached from the world
# chooser rather than from inside a world, so they stay reachable from the
# start -- which also keeps a guaranteed sphere-1 pool for fill to open with.
SIDE_PATH_REGIONS = [
    "Aloe Sidepath", "Appease Sidepath", "Atombomb Sidepath", "Bank Sidepath",
    "Bloominghearts Sidepath", "Buttercup Sidepath", "Conceal Sidepath",
    "Doomshroom Sidepath", "Electriccurrant Sidepath", "Enlighten Sidepath",
    "Epic Beghouled Sidepath", "Floawerpot Sidepath",
    "Ghostpepper Sidepath", "Gloomshroom Sidepath", "Goldbloom Sidepath",
    "Hotdate Sidepath", "Icebloom Sidepath", "Iceshroom Sidepath",
    "Meteorflower Sidepath", "Mixed Sidepath", "Parsnip Sidepath", "Plantern Sidepath",
    "Reinforce Sidepath", "Reinforcemint Sidepath", "Rhythm Sidepath",
    "Sandbox Sidepath", "Sapfling Sidepath", "Seashooter Sidepath",
    "Shootingstarfruit Sidepath", "Solartomato Sidepath", "Squash Sidepath",
    "Strawburst Sidepath", "Sweetpotato Sidepath", "Umbrellaleaf Sidepath",
    "Vamporcini Sidepath",
]

# Every side path named above has to be a real region, or its entry silently
# gates nothing.
_unknown_side_paths = set(SIDE_PATH_WORLD) - set(SIDE_PATH_REGIONS)
if _unknown_side_paths:
    raise ValueError(f"SIDE_PATH_WORLD names unknown side paths: {sorted(_unknown_side_paths)}")
_unknown_side_path_worlds = set(SIDE_PATH_WORLD.values()) - set(WORLD_REGIONS)
if _unknown_side_path_worlds:
    raise ValueError(f"side paths tied to unknown worlds: {sorted(_unknown_side_path_worlds)}")
