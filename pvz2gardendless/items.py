"""
PvZ2 Gardendless — item definitions and item pool construction.
"""

import dataclasses
from typing import Dict, List, TYPE_CHECKING

from BaseClasses import Item, ItemClassification

from .constants import BASE_ID, KEYED_WORLDS, LOGIC_PLANTS

if TYPE_CHECKING:
    from . import PvZ2GardendlessWorld


@dataclasses.dataclass
class PvZ2Item:
    name: str
    classification: ItemClassification
    code: int


PLANT_ITEMS: List[PvZ2Item] = []
_plants = [
    # Progression (required for specific world rules)
    ("Lily Pad",            ItemClassification.progression),   # Big Wave Beach
    ("Hot Potato",          ItemClassification.progression),   # Frostbite Caves
    ("Perfume-shroom",      ItemClassification.progression),   # Jurassic Marsh
    # Game starting plants (always given by BASEUNLOCKLIST — but included
    # here so AP can track and send them; behavior TBD based on testing)
    ("Peashooter",          ItemClassification.useful),
    ("Sunflower",           ItemClassification.useful),
    ("Wall-nut",            ItemClassification.useful),
    ("Potato Mine",         ItemClassification.useful),
    # Useful plants
    ("Cabbage-pult",        ItemClassification.useful),
    ("Bloomerang",          ItemClassification.useful),
    ("Iceberg Lettuce",     ItemClassification.useful),
    ("Grave Buster",        ItemClassification.useful),
    ("Twin Sunflower",      ItemClassification.useful),
    ("Bonk Choy",           ItemClassification.useful),
    ("Repeater",            ItemClassification.useful),
    ("Iceweed",             ItemClassification.useful),
    ("Snowdrop",            ItemClassification.useful),
    ("Squash",              ItemClassification.useful),
    ("Dandelion",           ItemClassification.useful),
    ("Pea Vine",            ItemClassification.useful),
    ("Kernel-pult",         ItemClassification.useful),
    ("Snap Dragon",         ItemClassification.useful),
    ("Spikeweed",           ItemClassification.useful),
    ("Coconut Cannon",      ItemClassification.useful),
    ("Cherry Bomb",         ItemClassification.useful),
    ("Spring Bean",         ItemClassification.useful),
    ("Spikerock",           ItemClassification.useful),
    ("Threepeater",         ItemClassification.useful),
    ("Buttercup",           ItemClassification.useful),
    ("Split Pea",           ItemClassification.useful),
    ("Chili Bean",          ItemClassification.useful),
    ("Lightning Reed",      ItemClassification.useful),
    ("Pea Pod",             ItemClassification.useful),
    ("Tall-nut",            ItemClassification.useful),
    ("Jalapeno",            ItemClassification.useful),
    ("Melon-Pult",          ItemClassification.useful),
    ("Winter Melon",        ItemClassification.useful),
    ("Imitater",            ItemClassification.useful),
    ("Electric Peashooter", ItemClassification.useful),
    ("Sap-fling",           ItemClassification.useful),
    ("Electric Currant",    ItemClassification.useful),
    ("Laser Bean",          ItemClassification.useful),
    ("Blover",              ItemClassification.useful),
    ("Citron",              ItemClassification.useful),
    ("E.M. Peach",          ItemClassification.useful),
    ("Star Fruit",          ItemClassification.useful),
    ("Shooting Starfruit",  ItemClassification.useful),
    ("Infi-nut",            ItemClassification.useful),
    ("Magnifying Grass",    ItemClassification.useful),
    ("Tile Turnip",         ItemClassification.useful),
    ("Apple Mortar",        ItemClassification.useful),
    ("Solar Tomato",        ItemClassification.useful),
    ("Hypno-shroom",        ItemClassification.useful),
    ("Sun-Shroom",          ItemClassification.useful),
    ("Puff-shroom",         ItemClassification.useful),
    ("Fume-Shroom",         ItemClassification.useful),
    ("Sun Bean",            ItemClassification.useful),
    ("Pea-nut",             ItemClassification.useful),
    ("Magnet-shroom",       ItemClassification.useful),
    ("Scaredy-shroom",      ItemClassification.useful),
    ("Plantern",            ItemClassification.useful),
    ("Vamporcini",          ItemClassification.useful),
    ("Ice-shroom",          ItemClassification.useful),
    ("Doom-shroom",         ItemClassification.useful),
    ("Tangle Kelp",         ItemClassification.useful),
    ("Bowling Bulb",        ItemClassification.useful),
    ("Homing Thistle",      ItemClassification.useful),
    ("Guacodile",           ItemClassification.useful),
    ("Banana Launcher",     ItemClassification.useful),
    ("Sea-shroom",          ItemClassification.useful),
    ("Chomper",             ItemClassification.useful),
    ("Missile Toe",         ItemClassification.useful),
    ("Ghost Pepper",        ItemClassification.useful),
    ("Parsnip",             ItemClassification.useful),
    ("Hurrikale",           ItemClassification.useful),
    ("Pepper-pult",         ItemClassification.useful),
    ("Chard Guard",         ItemClassification.useful),
    ("Fire Peashooter",     ItemClassification.useful),
    ("Stunion",             ItemClassification.useful),
    ("Rotobaga",            ItemClassification.useful),
    ("Jack O' Lantern",     ItemClassification.useful),
    ("Sweet Potato",        ItemClassification.useful),
    ("Hot Date",            ItemClassification.useful),
    ("Gatling Pea",         ItemClassification.useful),
    ("Torchwood",           ItemClassification.useful),
    ("Lava Guava",          ItemClassification.useful),
    ("Red Stinger",         ItemClassification.useful),
    ("A.K.E.E.",            ItemClassification.useful),
    ("Endurian",            ItemClassification.useful),
    ("Toadstool",           ItemClassification.useful),
    ("Stallia",             ItemClassification.useful),
    ("Gold Leaf",           ItemClassification.useful),
    ("Skyshooter",          ItemClassification.useful),
    ("Moon Bean",           ItemClassification.useful),
    ("Strawburst",          ItemClassification.useful),
    ("Fire Gourd",          ItemClassification.useful),
    ("Snow Pea",            ItemClassification.useful),
    ("Bamboo Shoot",        ItemClassification.useful),
    ("Resistant Radish",    ItemClassification.useful),
    ("Heavenly Peach",      ItemClassification.useful),
    ("Power Lily",          ItemClassification.useful),
    ("Lychee",              ItemClassification.useful),
    ("Solar Sage",          ItemClassification.useful),
    ("Cantaloupe-pult",     ItemClassification.useful),
    ("Bamboozle",           ItemClassification.useful),
    ("Phat Beet",           ItemClassification.useful),
    ("Cactus",              ItemClassification.useful),
    ("Celery Stalker",      ItemClassification.useful),
    ("Thyme Warp",          ItemClassification.useful),
    ("Electric Blueberry",  ItemClassification.useful),
    ("Garlic",              ItemClassification.useful),
    ("Spore-shroom",        ItemClassification.useful),
    ("Intensive Carrot",    ItemClassification.useful),
    ("Blooming Heart",      ItemClassification.useful),
    ("Grapeshot",           ItemClassification.useful),
    ("Primal Peashooter",   ItemClassification.useful),
    ("Primal Wall-nut",     ItemClassification.useful),
    ("Cold Snapdragon",     ItemClassification.useful),
    ("Primal Sunflower",    ItemClassification.useful),
    ("Primal Potato Mine",  ItemClassification.useful),
    ("Meteor Flower",       ItemClassification.useful),
    ("Explode-O-Nut",       ItemClassification.useful),
    ("Shrinking Violet",    ItemClassification.useful),
    ("Moonflower",          ItemClassification.useful),
    ("Dragon Fruit",        ItemClassification.useful),
    ("Nightshade",          ItemClassification.useful),
    ("Shadow-shroom",       ItemClassification.useful),
    ("Dusk Lobber",         ItemClassification.useful),
    ("Grimrose",            ItemClassification.useful),
    ("Gold Bloom",          ItemClassification.useful),
    ("Escape Root",         ItemClassification.useful),
    ("Gloom Vine",          ItemClassification.useful),
    ("Gloom-shroom",        ItemClassification.useful),
    ("Umbrella Leaf",       ItemClassification.useful),
    ("Pumpkin",             ItemClassification.useful),
    ("Cran-Jelly",          ItemClassification.useful),
]

# Plants referenced by an access rule MUST be progression. AP only tracks
# advancement items in CollectionState.prog_items, so state.has_any() is
# always False for a "useful" item -- an access rule naming only useful items
# can never be satisfied, and fill responds by treating everything behind it
# as unreachable (verified in a spoiler log: zero progression items placed in
# any gated Ancient Egypt region, and no sun producer anywhere in sphere 1).
# LOGIC_PLANTS is assembled from the rule data itself, so a plant cannot be
# named by a rule without being promoted here. Promoting leaves the item IDs
# below unchanged.
for i, (name, cls) in enumerate(_plants):
    if name in LOGIC_PLANTS:
        cls = ItemClassification.progression
    PLANT_ITEMS.append(PvZ2Item(name, cls, BASE_ID + i))

# A rule naming a plant with no matching item is a rule that can never pass,
# and it would fail silently -- state.has() just returns False forever.
_unknown_logic_plants = LOGIC_PLANTS - {plant.name for plant in PLANT_ITEMS}
if _unknown_logic_plants:
    raise ValueError("access rules reference plants that have no item: "
                     f"{sorted(_unknown_logic_plants)}")

# World Key items — one per keyed world.
# Modern Day no longer uses a key (it unlocks purely on the world-goal
# requirement), but its entry is kept so every later item ID stays put.
# It is filtered out of the pool in create_item_pool() instead.
MODERN_DAY_KEY = "Modern Day Key"
KEY_ITEMS: List[PvZ2Item] = []
_key_base = BASE_ID + len(PLANT_ITEMS)
for i, world_name in enumerate(KEYED_WORLDS):
    KEY_ITEMS.append(PvZ2Item(f"{world_name} Key", ItemClassification.progression, _key_base + i))

# Filler items — coins and gems only
FILLER_ITEMS: List[PvZ2Item] = []
_filler_names = ["100 Coins", "500 Coins", "1000 Coins", "10 Gems", "20 Gems", "50 Gems"]
_filler_base = _key_base + len(KEY_ITEMS)
for i, name in enumerate(_filler_names):
    FILLER_ITEMS.append(PvZ2Item(name, ItemClassification.filler, _filler_base + i))

# Trap items. Appended after the filler block so every existing item keeps the
# ID it already had.
LAWN_MOWER_TRAP = "Lawn Mower Trap"
TRAP_ITEMS: List[PvZ2Item] = []
_trap_names = [LAWN_MOWER_TRAP]
_trap_base = _filler_base + len(FILLER_ITEMS)
for i, name in enumerate(_trap_names):
    TRAP_ITEMS.append(PvZ2Item(name, ItemClassification.trap, _trap_base + i))

ALL_ITEMS: List[PvZ2Item] = PLANT_ITEMS + KEY_ITEMS + FILLER_ITEMS + TRAP_ITEMS
ITEM_NAME_TO_ITEM: Dict[str, PvZ2Item] = {item.name: item for item in ALL_ITEMS}
ITEM_NAME_TO_ID: Dict[str, int]        = {item.name: item.code for item in ALL_ITEMS}

ITEM_NAME_GROUPS: Dict[str, set] = {
    "Plants":     {i.name for i in PLANT_ITEMS},
    "World Keys": {i.name for i in KEY_ITEMS},
    "Traps":      {i.name for i in TRAP_ITEMS},
}


def create_item_pool(world: "PvZ2GardendlessWorld", pool_size: int) -> List[Item]:
    """Build this slot's item pool. Does not touch multiworld.itempool --
    the caller decides how to merge it in, since that pool is shared by
    every player in the multiworld."""
    pool: List[Item] = []

    # One unique key per keyed world, minus Modern Day -- that world is
    # gated on the world-goal count alone, so shipping a key nobody needs
    # would just waste a location.
    for key_item in KEY_ITEMS:
        if key_item.name == MODERN_DAY_KEY:
            continue
        pool.append(world.create_item(key_item.name))

    # All progression + useful plants
    for plant in PLANT_ITEMS:
        if plant.classification in (ItemClassification.progression,
                                    ItemClassification.useful):
            pool.append(world.create_item(plant.name))

    # Everything left over is filler, of which trap_percentage becomes
    # traps. Traps only ever displace filler, never a plant or a key.
    remaining = pool_size - len(pool)
    trap_count = remaining * world.options.trap_percentage.value // 100
    for _ in range(trap_count):
        pool.append(world.create_item(LAWN_MOWER_TRAP))
    remaining -= trap_count

    filler_cycle = ["100 Coins", "500 Coins", "10 Gems",
                    "1000 Coins", "20 Gems", "50 Gems"]
    fi = 0
    while remaining > 0:
        name = filler_cycle[fi % len(filler_cycle)]
        pool.append(
            Item(name, ItemClassification.filler,
                 ITEM_NAME_TO_ID.get(name), world.player))
        fi += 1
        remaining -= 1

    return pool
