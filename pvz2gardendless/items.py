"""
PvZ2 Gardendless — item definitions and item pool construction.
"""

import dataclasses
from typing import Dict, List, TYPE_CHECKING

from BaseClasses import Item, ItemClassification

from .constants import (
    BASE_ID, GAME_NAME, KEY_NAME_TO_WORLD, KEYED_WORLDS, LOGIC_PLANTS,
    UPGRADE_GROUPS,
)

if TYPE_CHECKING:
    from . import PvZ2GardendlessWorld


class PvZ2Item(Item):
    """Every item this world puts into the multiworld. Subclassing purely to
    carry `game`: a bare BaseClasses.Item reports game == "Generic", which is
    what trackers, the spoiler log and AP's own world tests read."""
    game: str = GAME_NAME


@dataclasses.dataclass
class PvZ2ItemData:
    """Static definition of an item -- name, classification and ID. Distinct
    from PvZ2Item, which is the live per-slot instance handed to AP."""
    name: str
    classification: ItemClassification
    code: int


PLANT_ITEMS: List[PvZ2ItemData] = []
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
    PLANT_ITEMS.append(PvZ2ItemData(name, cls, BASE_ID + i))

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
KEY_ITEMS: List[PvZ2ItemData] = []
_key_base = BASE_ID + len(PLANT_ITEMS)
for i, world_name in enumerate(KEYED_WORLDS):
    KEY_ITEMS.append(PvZ2ItemData(f"{world_name} Key", ItemClassification.progression, _key_base + i))

# Filler items — coins and gems only
FILLER_ITEMS: List[PvZ2ItemData] = []
_filler_names = ["100 Coins", "500 Coins", "1000 Coins", "10 Gems", "20 Gems", "50 Gems"]
_filler_base = _key_base + len(KEY_ITEMS)
for i, name in enumerate(_filler_names):
    FILLER_ITEMS.append(PvZ2ItemData(name, ItemClassification.filler, _filler_base + i))

# Trap items. Appended after the filler block so every existing item keeps the
# ID it already had.
LAWN_MOWER_TRAP = "Lawn Mower Trap"
TRAP_ITEMS: List[PvZ2ItemData] = []
_trap_names = [LAWN_MOWER_TRAP]
_trap_base = _filler_base + len(FILLER_ITEMS)
for i, name in enumerate(_trap_names):
    TRAP_ITEMS.append(PvZ2ItemData(name, ItemClassification.trap, _trap_base + i))

# Permanent upgrade items. Appended after the trap block so every existing
# item keeps the ID it already had. Classified useful, not progression: they
# make the run easier but no access rule names one, and marking them
# progression would have fill treat them as gating something they do not.
# One item per GROUP, not per level -- the progressive ones go into the pool
# once per level they cover (see create_item_pool).
UPGRADE_ITEMS: List[PvZ2ItemData] = []
_upgrade_base = _trap_base + len(TRAP_ITEMS)
for i, (name, _codenames) in enumerate(UPGRADE_GROUPS):
    UPGRADE_ITEMS.append(PvZ2ItemData(name, ItemClassification.useful, _upgrade_base + i))

# Item name -> the codenames it grants, in the order copies of it are applied.
# Sent in slot_data so the client does not carry a second copy of this mapping
# that could drift out of step with this one: the client grants the first N
# codenames of a group after receiving N copies of its item.
UPGRADE_ITEM_TO_CNS: Dict[str, List[str]] = {name: list(cns)
                                             for name, cns in UPGRADE_GROUPS}

ALL_ITEMS: List[PvZ2ItemData] = (PLANT_ITEMS + KEY_ITEMS + FILLER_ITEMS
                                 + TRAP_ITEMS + UPGRADE_ITEMS)
ITEM_NAME_TO_ITEM: Dict[str, PvZ2ItemData] = {item.name: item for item in ALL_ITEMS}
ITEM_NAME_TO_ID: Dict[str, int]        = {item.name: item.code for item in ALL_ITEMS}

# Two items sharing a name would collapse into one entry here, silently
# dropping whichever was defined first from every lookup that matters.
if len(ITEM_NAME_TO_ITEM) != len(ALL_ITEMS):
    _seen: Dict[str, int] = {}
    for item in ALL_ITEMS:
        _seen[item.name] = _seen.get(item.name, 0) + 1
    raise ValueError("duplicate item names: "
                     f"{sorted(n for n, c in _seen.items() if c > 1)}")

ITEM_NAME_GROUPS: Dict[str, set] = {
    "Plants":     {i.name for i in PLANT_ITEMS},
    "World Keys": {i.name for i in KEY_ITEMS},
    "Traps":      {i.name for i in TRAP_ITEMS},
    "Upgrades":   {i.name for i in UPGRADE_ITEMS},
}

# Order filler is dealt out in. It deliberately interleaves the two currencies
# instead of reusing FILLER_ITEMS order, which is grouped by type and would
# hand out a long run of coins followed by a long run of gems.
FILLER_CYCLE = ["100 Coins", "500 Coins", "10 Gems",
                "1000 Coins", "20 Gems", "50 Gems"]

# The two lists drifting apart would not raise: a name here that is not a real
# item reaches create_item() as an unknown, which builds it with code=None --
# and AP reads a None code as an event, not a pool item.
if set(FILLER_CYCLE) != {f.name for f in FILLER_ITEMS}:
    raise ValueError("FILLER_CYCLE and FILLER_ITEMS disagree: "
                     f"{sorted(set(FILLER_CYCLE) ^ {f.name for f in FILLER_ITEMS})}")


def create_item_pool(world: "PvZ2GardendlessWorld", pool_size: int) -> List[Item]:
    """Build this slot's item pool. Does not touch multiworld.itempool --
    the caller decides how to merge it in, since that pool is shared by
    every player in the multiworld."""
    pool: List[Item] = []

    # One unique key per keyed world, minus Modern Day -- that world is
    # gated on the world-goal count alone, so shipping a key nobody needs
    # would just waste a location. Worlds this seed left out are skipped for
    # the same reason: their regions hold no locations, so their key would
    # unlock nothing.
    for key_item in KEY_ITEMS:
        if key_item.name == MODERN_DAY_KEY:
            continue
        if KEY_NAME_TO_WORLD[key_item.name] not in world.enabled_worlds:
            continue
        pool.append(world.create_item(key_item.name))

    # All progression + useful plants
    for plant in PLANT_ITEMS:
        if plant.classification in (ItemClassification.progression,
                                    ItemClassification.useful):
            pool.append(world.create_item(plant.name))

    # Permanent upgrades, when the option has the game withhold them. With it
    # off the game hands them out itself, so shipping them as items too would
    # mean receiving something already owned.
    if world.options.shuffle_upgrades:
        # One copy per level the group covers: three Progressive Sun Shovels,
        # one Sky Shield. Sized off the codename list so adding a level to a
        # group is a constants.py edit alone.
        for name, codenames in UPGRADE_GROUPS:
            for _ in codenames:
                pool.append(world.create_item(name))

    # Everything left over is filler, of which trap_percentage becomes
    # traps. Traps only ever displace filler, never a plant or a key.
    remaining = pool_size - len(pool)
    # Keys and plants are a fixed block, so a seed small enough to have fewer
    # locations than that block cannot hold its own item pool. The side paths
    # and Modern Day keep even a one-world seed well clear of this, but the
    # arithmetic below would silently produce a short pool rather than say so.
    if remaining < 0:
        raise ValueError(
            f"item pool ({len(pool)} keys and plants) exceeds the "
            f"{pool_size} locations this slot builds; enable more worlds")
    trap_count = remaining * world.options.trap_percentage.value // 100
    for _ in range(trap_count):
        pool.append(world.create_item(LAWN_MOWER_TRAP))
    remaining -= trap_count

    for i in range(remaining):
        pool.append(world.create_item(FILLER_CYCLE[i % len(FILLER_CYCLE)]))

    return pool
