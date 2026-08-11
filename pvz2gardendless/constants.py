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
# Single-use plants: consumed the moment they go off (or, for Ghost Pepper,
# after a short timer). They are perfectly good attackers, which is why they
# stay in CHEAP_ATTACKER_PLANTS for the Ancient Egypt logic gate -- but they
# are a poor GUARANTEED STARTING PLANT, which exists so a player always has
# something that can hold a lane. A run whose only plant is Potato Mine has to
# replant on every single zombie.
# The game has no data flag for this: nothing in PlantProperties distinguishes
# a plant that dies on use, and Family does not track it either (Explode-O-Nut
# is Explosive but is a wall). So this is curated, like the lists above.
SINGLE_USE_PLANTS = [
    "Cherry Bomb", "Chili Bean", "E.M. Peach", "Electric Blueberry",
    "Escape Root", "Ghost Pepper", "Grapeshot", "Hypno-shroom",
    "Intensive Carrot", "Jalapeno", "Lava Guava", "Potato Mine",
    "Primal Potato Mine", "Shadow-shroom", "Squash",
]

# Plants that persist but deal no damage of their own -- support, defence and
# utility. Also unfit as the sole starting plant for the same reason: the
# guarantee is meant to be something that can actually kill a zombie.
NON_DAMAGING_PLANTS = [
    "Explode-O-Nut",    # a wall; only hurts what is already eating it
    "Moonflower",       # shadow support, powers other plants
    "Shrinking Violet", # shrinks zombies rather than damaging them
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

WORLD_ENTRY_PLANTS = {
    "Big Wave Beach":  ["Lily Pad"],
    "Frostbite Caves": ["Hot Potato", "Pepper-pult", "Fire Peashooter"],
    "Jurassic Marsh":  ["Perfume-shroom"],
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
    | {plant for plants in WORLD_ENTRY_PLANTS.values() for plant in plants}
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
