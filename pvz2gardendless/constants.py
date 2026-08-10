"""
Static world-shape data shared across items.py, locations.py, regions.py and
rules.py: identifiers, world lists, and the plant sets used for logic gating.
"""

GAME_NAME = "PvZ2 Gardendless"
BASE_ID   = 0xD1A2B3C4

# Worlds that need a key item to access (Ancient Egypt is always free)
KEYED_WORLDS = [
    "Pirate Seas", "Wild West", "Far Future", "Dark Ages",
    "Big Wave Beach", "Frostbite Caves", "Lost City",
    "Kongfu Temple", "Neon Mixtape Tour", "Jurassic Marsh", "Modern Day", "Aerial Fortress",
]

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
