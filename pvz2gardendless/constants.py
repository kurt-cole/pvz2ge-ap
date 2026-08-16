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
#
# That ungated opening is egypt1-5. Mid1 begins at egypt6, so the
# sun-and-attacker rule is what says "you are expected to have a sun producer
# by Egypt level 6". It began at egypt3 briefly (2026-08-12); before that at
# egypt10, which had logic
# calling nine levels playable on falling sun alone; a sun producer was nudged
# into sphere 1 with early_items to paper over it. Mid1 deliberately has no
# entry here: its gate is the sun producer, with no plant count on top.
EGYPT_STRETCH_PLANTS = {"Ancient Egypt Mid2": 3, "Ancient Egypt Late": 6}

# Region-name suffixes that mark a stretch past the opening of its world.
# Covers both the generic cut above (" Mid", " Late") and Ancient Egypt's
# bespoke four-region split (" Mid1", " Mid2", " Late").
LATE_REGION_SUFFIXES = (" Mid", " Mid1", " Mid2", " Late")


def is_early_region(name: str) -> bool:
    """Is this region reachable without grinding deeper into a world?

    True for a world's opening stretch, the side paths, the Danger Rooms, the
    tutorial and the store. Entering a world's opening costs only its key --
    the plant-count gates sit on the later stretches -- so anything in an early
    region is reachable as soon as the key for it turns up.

    Used by the early_world_keys option to keep World Keys from hiding behind
    each other's endgames. Modern Day is excluded as well: it opens only once
    the world-goal requirement is already met, so it is the latest place in any
    seed and a key there would be found after it was needed.
    """
    return not name.endswith(LATE_REGION_SUFFIXES) and name != "Modern Day"

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
# Shine Vine only modifies a neighbour's output (SunProductionModifier), Marigold
# produces coins, and Gold Bloom is a 0-cost conveyor-only plant.
#
# Moonflower is left out despite a real `sun` action: SunPerNeighbor 25 means it
# produces nothing without shadow plants beside it, so it cannot carry a gate
# alone. Solar Tomato is left out by Kurt's call (2026-08-16) -- it is a
# 100-sun, 25s-recharge plant whose production is not in its sheet at all, so
# it is not something a player can be assumed to open a world on.
#
# A name here is promoted to progression in items.py, so removing one demotes
# that plant to useful. Item IDs are unaffected.
SUN_PRODUCER_PLANTS = [
    "Sunflower", "Sun-Shroom", "Twin Sunflower", "Primal Sunflower",
    "Solar Sage",
]

# Cheap plants that can actually kill a zombie. rules.py gates every Ancient
# Egypt stretch on has_any() over this list, so a name here is a name the
# generator will accept as "the player can fight".
#
# DERIVED FROM GAME DATA. A plant qualifies on all three of:
#   1. Damage evidence -- an almanac `damage` PlantStat, a ChewDamage /
#      ContactDamage / ExplodeDamage field, or an Action carrying Damage >= 20.
#   2. SunCost <= 150.
#   3. Not `IsZenGardenWaterPlant` (Lily Pad and Tangle Kelp), which cannot be
#      placed on Ancient Egypt's dry terrain.
#
# This list used to be SunCost + Family, and Family is a theme tag rather than
# a damage flag. That let six plants that cannot hurt anything satisfy the
# Egypt gate: Moonflower, Intensive Carrot, Explode-O-Nut, Shrinking Violet,
# Hypno-shroom and E.M. Peach. Holding only Sunflower and Moonflower read as
# a survivable lawn.
#
# Three thresholds here are load-bearing and were each got wrong once:
#   - Damage >= 20, not > 0. 20 is one NDS, the game's normal damage shot (one
#     pea). Spring Bean's launch carries Damage 1 and Stunion's stun Damage 0;
#     neither is an attack.
#   - Action Type == "special" is NOT damage evidence. It only means "triggered
#     effect" -- Sunflower, Blover and Thyme Warp all have one.
#   - The almanac `damage` stat alone is not enough. It is a display rating and
#     Chomper carries none despite ChewDamage 200.
#
# Scaredy-shroom, Vamporcini and Skyshooter have no _PLANTPROPERTIES sheet at
# all. They are listed by hand because no sheet means unknown, not harmless --
# all three plainly attack.
#
# Magnifying Grass is held out by hand despite passing every test above: it
# spends sun to fire, so as the only plant on a sun-starved opening lawn it
# cannot be relied on to kill anything.
CHEAP_ATTACKER_PLANTS = [
    "Blooming Heart", "Bonk Choy", "Buttercup", "Cabbage-pult",
    "Celery Stalker", "Chard Guard", "Cherry Bomb", "Chili Bean", "Chomper",
    "Dusk Lobber", "Electric Blueberry", "Electric Currant", "Endurian",
    "Escape Root", "Fume-Shroom", "Ghost Pepper", "Gloom Vine", "Grapeshot",
    "Grimrose", "Guacodile", "Iceweed", "Jalapeno", "Kernel-pult",
    "Lava Guava", "Lightning Reed", "Nightshade",
    "Parsnip", "Pea Pod", "Pea Vine", "Pea-nut", "Peashooter", "Phat Beet",
    "Potato Mine", "Primal Potato Mine", "Puff-shroom", "Red Stinger",
    "Shadow-shroom", "Snap Dragon", "Snow Pea", "Spikeweed", "Split Pea",
    "Spore-shroom", "Squash", "Star Fruit",
    # no data sheet; attackers by inspection
    "Scaredy-shroom", "Skyshooter", "Vamporcini",
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
    "Cherry Bomb", "Chili Bean", "Escape Root", "Ghost Pepper", "Grapeshot",
    "Grimrose", "Jalapeno", "Lava Guava", "Potato Mine",
    "Primal Potato Mine", "Shadow-shroom", "Squash",
]

# Plants that persist but deal no damage of their own -- support and defence.
# Also unfit as the sole starting plant for the same reason: the guarantee is
# meant to be something that can actually kill a zombie.
#
# Every one of these was in CHEAP_ATTACKER_PLANTS at some point, because the
# old SunCost + Family derivation read a theme tag as a damage flag. They are
# kept as a named regression guard rather than as a filter: the derivation
# above already excludes them, and the assertion below now checks exactly that.
# If one reappears in CHEAP_ATTACKER_PLANTS, the Ancient Egypt gate has gone
# back to passing on a lawn that cannot kill anything.
NON_DAMAGING_PLANTS = [
    "E.M. Peach",       # stuns and disarms, Damage 0
    "Explode-O-Nut",    # a wall; only hurts what is already eating it
    "Hypno-shroom",     # converts a zombie, Damage 0
    "Intensive Carrot", # revives a destroyed plant, no attack at all
    "Moonflower",       # shadow support, powers other plants
    "Shrinking Violet", # shrinks zombies, no damage
]

# What generate_early() may hand a player for free. A cheap attacker that
# persists on the lawn and does damage on its own.
STARTER_PLANTS = [
    plant for plant in CHEAP_ATTACKER_PLANTS
    if plant not in set(SINGLE_USE_PLANTS) | set(NON_DAMAGING_PLANTS)
]

# No plant that cannot deal damage may count as an attacker.
_bad_attackers = set(NON_DAMAGING_PLANTS) & set(CHEAP_ATTACKER_PLANTS)
if _bad_attackers:
    raise ValueError("plants that deal no damage are being counted as "
                     f"attackers: {sorted(_bad_attackers)}")

# Single-use plants stay in CHEAP_ATTACKER_PLANTS on purpose -- they kill, so
# they satisfy the Egypt gate -- but a name that is not one would filter
# nothing and quietly leave that plant in the starter pool.
_unknown_excluded = set(SINGLE_USE_PLANTS) - set(CHEAP_ATTACKER_PLANTS)
if _unknown_excluded:
    raise ValueError("excluded starter plants are not cheap attackers: "
                     f"{sorted(_unknown_excluded)}")

# Plants that answer the Jester (dark_juggler), who returns projectiles at
# your own lawn.
#
# Lobbing is NOT an answer: he returns Cabbage-pult and Melon-pult like
# anything else. Their projectiles carry DamageFlags ["lobbed","catapult"] and
# no jester flag at all, so the arc buys nothing. An earlier version of this
# list assumed otherwise and let every pult through.
#
# What actually qualifies is the projectile the game explicitly marks
# CannotBeReversedByJester, checked on the plant's FIRST projectile action --
# its normal attack. Checking any projectile would wrongly admit Guacodile,
# whose ordinary shot is reversible and whose flagged projectile is the child
# it leaves behind, and Iceweed, whose flagged one is its plant food.
#
# Six plants qualify and are in the item pool. Others do in the game --
# Caulipower, Holly Knight, Anthurium, Dark Matter Dragonfruit -- but have no
# item, so naming them would gate on something the multiworld cannot send.
#
# Deliberately NOT included: the 62 plants that damage without a projectile at
# all, which he also has nothing to reverse. Most are melee, one-shots or
# utility rather than something to hold a Dark Ages lane with, and folding
# them in would make this requirement nearly free.
JESTER_COUNTER_PLANTS = [
    "Banana Launcher",
    "Electric Peashooter",
    "Magnifying Grass",
    "Missile Toe",
    "Sap-fling",
    "Strawburst",
]

# Plants that give off heat, for Frostbite Caves. Its ice blocks freeze plants
# solid and its winds blow them off the lawn, and only a standing source of
# warmth keeps a lawn workable.
#
# These are the plants the game gives a WarmingRadius: a 1.5-square aura that
# pulses every 6 seconds, deals 200 fire damage to grid items (the ice blocks)
# and applies "thaw_whole_stage" to plants. That property is the mechanic, so
# it is the definition used here.
#
# Six plants have it; Wasabi Whip is the one with no Archipelago item, so it
# is left out. Deliberately absent are Hot Potato and Pepper-pult, which the
# old version of this rule accepted: neither has a warming radius. Hot Potato
# thaws one plant once and is gone, and Pepper-pult only deals fire damage.
# Both help, but neither keeps a lawn warm, which is what the world asks for.
FIRE_AURA_PLANTS = [
    "Fire Peashooter",
    "Hot Date",
    "Jack O' Lantern",
    "Lava Guava",
    "Torchwood",
]

# Plants a world needs on top of its key, as a list of requirements: the
# player needs at least one plant from EACH list, so a world can ask for more
# than one thing at once. rules.py ANDs them onto that world's entrance.
WORLD_ENTRY_PLANTS = {
    "Big Wave Beach":  [["Lily Pad"]],
    # Frostbite Caves freezes plants and blows them away, so it wants a
    # standing source of heat rather than any fire plant -- see
    # FIRE_AURA_PLANTS for why Hot Potato and Pepper-pult no longer count.
    "Frostbite Caves": [FIRE_AURA_PLANTS],
    "Jurassic Marsh":  [["Perfume-shroom"]],
    # Dark Ages is permanently night, so no sun falls at all and a sun producer
    # is the difference between playing the world and standing still. That is
    # no longer listed here: rules.py requires a sun producer to enter EVERY
    # world, so naming it again would only evaluate the same has_any twice.
    # What stays is the Jester, who returns straight-line shots, so something
    # that gets round him is needed on top.
    "Dark Ages":       [JESTER_COUNTER_PLANTS],
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
# chooser rather than from inside a world, so when they are in the seed at all
# they are reachable from the start.
#
# The whole list is dropped unless include_side_paths is on, which it is not by
# default: logic cannot gate a side path the way the game does (a path is one
# flat region hung off the opening of the world it branches from, and these
# seven hang off the tutorial), so leaving them in put late content -- Modern
# Day's own danger room among it -- in sphere 1. With them out, sphere 1 is the
# tutorial, egypt1-2 and the shop, and that is the whole pool fill has to open
# the seed with.
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

# The Danger Rooms: the game's endless survival mode, one per world (two to
# four for some), plus Big Wave Beach's eight themed minigame rooms and the
# Mixed Danger Room, which is Modern Day's "Highway to the Danger Room".
#
# DERIVED, not hand-picked: these are exactly the locations whose level
# codename in the client's LOC_LEVELS contains "dangerroom". Every one of them
# is named after its own codename, because a Danger Room hands out no reward
# for the randomizer to borrow a name from. The 28 locations called
# "Dangerroom <World> Unlock" are NOT in here and must never be -- those are
# ordinary numbered levels (egypt12, pirate4, beach20 ...) whose reward is
# unlocking the room. gen_test pins both halves of that.
#
# Dropped from the seed unless include_danger_rooms is on.
DANGER_ROOM_LOCATIONS = frozenset({
    "egypt_dangerroom", "egypt_dangerroom2", "egypt_dangerroom_minigame",
    "pirate_dangerroom", "pirate_dangerroom2",
    "cowboy_dangerroom", "cowboy_dangerroom2",
    "future_dangerroom", "future_dangerroom2", "future_dangerroom_sunbomb",
    "dark_dangerroom", "dark_dangerroom2", "dark_dangerroom_potion",
    "beach_dangerroom", "beach_dangerroom2",
    "beach_dangerroom_minigame_beach", "beach_dangerroom_minigame_cowboy",
    "beach_dangerroom_minigame_dark", "beach_dangerroom_minigame_egypt",
    "beach_dangerroom_minigame_future", "beach_dangerroom_minigame_iceage",
    "beach_dangerroom_minigame_lostcity", "beach_dangerroom_minigame_pirate",
    "iceage_dangerroom", "iceage_dangerroom2",
    "lostcity_dangerroom", "lostcity_dangerroom2",
    "kongfu_dangerroom", "kongfu_dangerroom2", "kongfu_dangerroom3",
    "kongfu_dangerroom4",
    "eighties_dangerroom",
    "dino_dangerroom", "dino_dangerroom2",
    "modern_dangerroom", "modern_dangerroom2",
    "mixed_dangerroom2",
})


# Every side path named above has to be a real region, or its entry silently
# gates nothing.
_unknown_side_paths = set(SIDE_PATH_WORLD) - set(SIDE_PATH_REGIONS)
if _unknown_side_paths:
    raise ValueError(f"SIDE_PATH_WORLD names unknown side paths: {sorted(_unknown_side_paths)}")
_unknown_side_path_worlds = set(SIDE_PATH_WORLD.values()) - set(WORLD_REGIONS)
if _unknown_side_path_worlds:
    raise ValueError(f"side paths tied to unknown worlds: {sorted(_unknown_side_path_worlds)}")
