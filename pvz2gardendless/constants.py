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

    True for a world's opening stretch, the Danger Rooms, the tutorial and the
    store. Entering a world's opening costs only its key -- the plant-count
    gates sit on the later stretches -- so anything in an early region is
    reachable as soon as the key for it turns up.

    Side paths answer True here by name and must not be judged on it: they hang
    off the stretch holding the level that reveals them, so Ice Bloom is behind
    Big Wave Beach 40 while still being called "Ice Bloom Sidepath". rules.py
    resolves a side path to what it hangs off before asking this.

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

# Sold by the game NOW but added upstream after the two lists above were
# written, so it cannot go in them: location ids are assigned by increment and
# the shop block is not last in _make_locs(), so appending there would renumber
# every location after it. locations.py adds these at the very end instead.
SHOP_EXTRA_COMMODITIES = ['chillypepper']  # 40 gem, no UnlockLevel

# In those lists, but NOT in the store the game actually loads. Kurt's build
# sells witchhazel, slingpea and chillypepper where this table has mirrornut,
# wasabiwhip and pyrevine -- 43 commodities either way, three swapped upstream
# (confirmed 2026-08-18 against PVZGE-Electron/pvzge_web, not the `Base Game`
# snapshot, which is older and still lists the old three).
#
# A card that is not in StoreCommodityFeatures is never drawn, so its check can
# never fire. Kept here rather than deleted for the same id reason, and routed
# into UNREACHABLE_LOCATIONS so no seed ever builds them.
SHOP_ABSENT_COMMODITIES = ['mirrornut', 'wasabiwhip', 'pyrevine']

SHOP_COMMODITIES = (SHOP_PLANT_COMMODITIES + SHOP_UPGRADE_COMMODITIES
                    + SHOP_EXTRA_COMMODITIES)
# The order locations.py must keep for the ids already assigned. Anything new
# goes in SHOP_EXTRA_COMMODITIES, never in the middle of this.
SHOP_LEGACY_COMMODITIES = SHOP_PLANT_COMMODITIES + SHOP_UPGRADE_COMMODITIES
SHOP_REGION = "Shop"

# Which level makes each shop card appear, from the store data itself
# (`StoreCommodityFeatures.Plants[].UnlockLevel` in `import/0f/0fc6e99c8.json`).
#
# The game destroys a card before drawing it unless its UnlockLevel is cleared:
#
#   getPlantProgressByID(id).progress > 0 ||
#   (UnlockLevel && getLevelProgressByID(UnlockLevel).progress < 3)
#
# so the store is not one shop that opens at egypt6 -- it is 39 cards that
# appear one at a time across the whole run. 29 of the 34 gem-priced plants
# carry an UnlockLevel; jalapeno, mirrornut, wasabiwhip, pyrevine and cranjelly
# do not, and neither does any of the five upgrade commodities, so those ten
# are on sale as soon as the store button exists.
#
# Read straight out of the store file and NOT from anything else that names the
# same level. These collide with the side-path branch levels in three places
# (beach14, eighties14, lostcity14) and mean something unrelated each time.
SHOP_UNLOCK = {
    "iceweed":            "egypt9",
    "snowdrop":           "egypt28",
    "starfruit":          "future20",
    "pinkstarfruit":      "future28",
    "asparagus":          "sky14",
    "hypnoshroom":        "dark8",
    "peanut":             "dark18",
    "homingthistle":      "beach31",
    "chomper":            "beach14",
    "hurrikale":          "iceage14",
    "lavaguava":          "lostcity14",
    "toadstool":          "lostcity31",
    "powerlily":          "kongfu22",
    "bamboozle":          "kongfu38",
    "firepeashooter":     "iceage29",
    "cactus":             "eighties14",
    "electricblueberry":  "eighties31",
    "caulipower":         "eighties39",
    "jackolantern":       "iceage34",
    "grapeshot":          "dino3",
    "escaperoot":         "modern31",
    "explodeonut":        "dino39",
    "applemortar":        "future31",
    "floawerPot":         "sky31",
    "coldsnapdragon":     "dino19",
    "missiletoe":         "beach35",
    "electricpeashooter": "cowboy28",
    "zoybeanpod":         "lostcity37",
    "shrinkingviolet":    "modern14",
}  # 29 gated cards

# Which commodities are actually used as AP checks: the ones the game puts on
# the shelf by CLEARING A LEVEL, plus the five upgrades.
#
# The ungated gem plants are deliberately left out. Every bit of upstream churn
# has happened in exactly that set -- mirrornut, wasabiwhip and pyrevine were
# swapped for witchhazel, slingpea and chillypepper between the snapshot in
# `Base Game` and the build the installer clones, while all 29 UnlockLevel
# entries agreed exactly. A card with no UnlockLevel is a shelf item the game
# can add or drop without touching anything else, and each time it does, an AP
# check either dies or is missed.
#
# So the rule is derived rather than listed: a plant is a check IF AND ONLY IF
# it has an UnlockLevel. Upstream reshuffling the ungated tail now costs
# nothing. It also means every shop check is gated on a level, which is what
# rules.py was already doing for 29 of them.
#
# The names stay in the lists above so their ids never move; locations.py
# filters them out of every seed instead.
SHOP_CHECK_COMMODITIES = ([c for c in SHOP_PLANT_COMMODITIES if c in SHOP_UNLOCK]
                          + list(SHOP_UPGRADE_COMMODITIES))

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
# Appease is TWO paths, because the game treats it as two. appease1_* branches
# off Ancient Egypt 29 and runs on epic_egypt; appease2_* branches off Frostbite
# Caves 25 and runs on epic_iceage. It used to be one region tied to Egypt, the
# earlier half, which put seven Frostbite Caves levels in logic from Egypt.
SIDE_PATH_WORLD = {
    "Aloe Sidepath":            "Lost City",
    "Appease-mint Sidepath":         "Ancient Egypt",
    "Appease-mint 2 Sidepath":       "Frostbite Caves",
    "Atomic Bombegranate Sidepath":        "Kongfu Temple",
    "Blooming Heart Sidepath":  "Neon Mixtape Tour",
    "Buttercup Sidepath":       "Pirate Seas",
    "Conceal-mint Sidepath":         "Modern Day",
    "Doom-shroom Sidepath":      "Dark Ages",
    "Electric Currant Sidepath": "Wild West",
    "Enlighten-mint Sidepath":       "Lost City",
    "Ghost Pepper Sidepath":     "Big Wave Beach",
    "Goo Peashooter Sidepath":  "Dark Ages",
    "Gloom-shroom Sidepath":     "Modern Day",
    "Gold Bloom Sidepath":       "Modern Day",
    "Hot Date Sidepath":         "Frostbite Caves",
    "Ice Bloom Sidepath":        "Big Wave Beach",
    "Ice-shroom Sidepath":       "Dark Ages",
    "Meteor Flower Sidepath":    "Jurassic Marsh",
    "Parsnip Sidepath":         "Big Wave Beach",
    "Plantern Sidepath":        "Dark Ages",
    "Reinforce-mint Sidepath":       "Far Future",
    "Rhythm Sidepath":          "Frostbite Caves",
    "Sap-fling Sidepath":        "Wild West",
    "Seashooter Sidepath":      "Big Wave Beach",
    "Solar Tomato Sidepath":     "Far Future",
    "Squash Sidepath":          "Ancient Egypt",
    "Strawburst Sidepath":      "Neon Mixtape Tour",
    "Sweet Potato Sidepath":     "Frostbite Caves",
    "Umbrella Leaf Sidepath":    "Modern Day",
    "Vamporcini Sidepath":      "Dark Ages",
}

# Which world level opens each side path, read off the world-map scenes.
#
# A branch island is labelled "<N>-1" and carries the quest's demo level, so
# `[9,"6-1",["squash0"]]` in Ancient Egypt's map means the Squash quest appears
# once egypt6 is cleared. The same convention labels a world's own optional
# levels (`[.."20-1",["egypt20_1"]]`), where "clear level N to reveal N-1" is
# already known to be how it reads.
#
# All 27 branch nodes, swept 2026-08-18 out of every scene carrying LevelIsland
# data (26 files -- the 11 world maps plus the epic maps, which carry no branch
# nodes of their own). Nothing else in the game reveals a quest: see
# level-and-shop-gating for the full list of ways a level can start.
#
# Two-step in game, and only the first step is modelled here: clearing this
# level reveals the quest's level 0, and clearing THAT opens the epic portal to
# levels 1..k. A side path is one flat region, so it is gated on the branch
# level alone and its own internal chain is not expressed.
#
# Appease-mint is two entries because it is two branches on two world maps.
SIDE_PATH_UNLOCK = {
    "Squash Sidepath":              "egypt6",       # 6-1   -> squash0
    "Appease-mint Sidepath":        "egypt29",      # 29-1  -> appease1_0
    "Appease-mint 2 Sidepath":      "iceage25",     # 25-1  -> appease2_0
    "Buttercup Sidepath":           "pirate33",     # 33-1  -> buttercup0
    "Sap-fling Sidepath":           "cowboy29",     # 29-1  -> sapfling0
    "Electric Currant Sidepath":    "cowboy34",     # 34-1  -> electriccurrant0
    "Reinforce-mint Sidepath":      "future13",     # 13-1  -> reinforce0
    "Solar Tomato Sidepath":        "future28",     # 28-1  -> solartomato0
    "Vamporcini Sidepath":          "dark4",        # 4-1   -> vamporcini0
    "Plantern Sidepath":            "dark9",        # 9-1   -> plantern0
    "Goo Peashooter Sidepath":      "dark16",       # 16-1  -> poisonpeashooter0
    "Ice-shroom Sidepath":          "dark22",       # 22-1  -> iceshroom0
    "Doom-shroom Sidepath":         "dark28",       # 28-1  -> doomshroom0
    "Seashooter Sidepath":          "beach7",       # 7-1   -> seashooter0
    "Ghost Pepper Sidepath":        "beach14",      # 14-1  -> ghostpepper0
    "Parsnip Sidepath":             "beach22",      # 22-1  -> parsnip0
    "Ice Bloom Sidepath":           "beach40",      # 40-1  -> icebloom0
    "Sweet Potato Sidepath":        "iceage12",     # 12-1  -> sweetpotato0
    "Aloe Sidepath":                "lostcity8",    # 8-1   -> aloe0
    "Enlighten-mint Sidepath":      "lostcity38",   # 38-1  -> enlighten0
    "Atomic Bombegranate Sidepath": "kongfu12",     # 12-1  -> atombomb0
    "Strawburst Sidepath":          "eighties14",   # 14-1  -> strawburst0
    "Blooming Heart Sidepath":      "eighties25",   # 25-1  -> bloominghearts0
    "Meteor Flower Sidepath":       "dino40",       # 40-1  -> meteorflower0
    "Umbrella Leaf Sidepath":       "modern10",     # 10-1  -> umbrellaleaf0
    "Conceal-mint Sidepath":        "modern25",     # 25-1  -> conceal0
    "Gold Bloom Sidepath":          "modern28",     # 28-1  -> goldbloom0
    "Gloom-shroom Sidepath":        "modern40",     # 40-1  -> gloomshroom0
}

# Side paths reached through another side path rather than from a world map.
#
# Hot Date is the only one. It has no branch node and no portal of its own --
# 27 chain-starts have one, Hot Date has none -- because it sits on the SAME
# epic_iceage chain immediately after sweetpotato5, so it is revealed by that
# chain cascading rather than by clearing a world level. Gating it on entering
# the Sweet Potato path is as close as a flat region gets to the game's "finish
# the Sweet Potato path"; the levels between are inside that one region and
# cannot be asked for separately.
SIDE_PATH_CHAIN = {
    "Hot Date Sidepath": "Sweet Potato Sidepath",
}

# The seven side paths the game data ties to no world: Sandbox, the Bank Theft
# levels, Epic Beghouled, FloawerPot, the Mixed Danger Room, Reinforcemint and
# ShootingStarFruit. They are standalone content reached from the world
# chooser rather than from inside a world, so when they are in the seed at all
# they are reachable from the start. The Mixed one is now always empty:
# mixed_dangerroom2 was its only location and it is unreachable in game, see
# UNREACHABLE_LOCATIONS.
#
# The whole list is dropped unless include_side_paths is on, which it is not by
# default. That default is now a content choice rather than a logic one: each
# path is gated on the level that reveals it (SIDE_PATH_UNLOCK), so leaving
# them in no longer puts late content in sphere 1. It used to -- a path hung
# off the opening of its world, and Ancient Egypt's opening is ungated, so
# Squash and Appease-mint were sphere 1 whatever the game says.
SIDE_PATH_REGIONS = [
    "Aloe Sidepath", "Appease-mint Sidepath", "Appease-mint 2 Sidepath",
    "Atomic Bombegranate Sidepath", "Bank Sidepath",
    "Blooming Heart Sidepath", "Buttercup Sidepath", "Conceal-mint Sidepath",
    "Doom-shroom Sidepath", "Electric Currant Sidepath", "Enlighten-mint Sidepath",
    "Epic Beghouled Sidepath", "Floawerpot Sidepath",
    "Ghost Pepper Sidepath", "Gloom-shroom Sidepath", "Gold Bloom Sidepath",
    "Goo Peashooter Sidepath",
    "Hot Date Sidepath", "Ice Bloom Sidepath", "Ice-shroom Sidepath",
    "Meteor Flower Sidepath", "Mixed Sidepath", "Parsnip Sidepath", "Plantern Sidepath",
    "Reinforce-mint Sidepath", "Reinforcemint Unused Sidepath", "Rhythm Sidepath",
    "Sandbox Sidepath", "Sap-fling Sidepath", "Seashooter Sidepath",
    "Shootingstarfruit Sidepath", "Solar Tomato Sidepath", "Squash Sidepath",
    "Strawburst Sidepath", "Sweet Potato Sidepath", "Umbrella Leaf Sidepath",
    "Vamporcini Sidepath",
]

# The Danger Rooms: the game's endless survival mode, one per world (two to
# four for some), plus Big Wave Beach's eight themed minigame rooms and the
# Mixed Danger Room.
#
# 37 entries, of which 35 are ever built: kongfu_dangerroom4 and
# mixed_dangerroom2 are in UNREACHABLE_LOCATIONS. They stay named here so the
# set keeps matching its stated derivation from LOC_LEVELS.
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
    "eighties_dangerroom", "eighties_dangerroom2",
    "dino_dangerroom", "dino_dangerroom2",
    "sky_dangerroom",
    "modern_dangerroom", "modern_dangerroom2",
    "mixed_dangerroom2",
})


# Which level unlocks each Danger Room, as the location name of that level.
#
# DERIVED FROM GAME DATA, not from the naming. A Danger Room's map node is
# locked until its own level progress is above zero, and the only thing that
# raises it is `AllPlayerProperties.unlockTrophy` in index.js:
#
#   case "dangerroom":
#     n.objdata.UnlockLevel.forEach(r => {
#       var t = e.getLevelProgressByID(r);
#       t.progress <= 0 && (t.progress = g.unlocked_neverPlayed); ... })
#
# so the chain is: a level's `FirstRewardParam` names a `dangerroom_*` trophy in
# the TROPHIES table (`import/0f/0fc6e99c8.json`), and that trophy's
# `objdata.UnlockLevel` lists the rooms it opens. Scanning every level
# definition for a `dangerroom_*` FirstRewardParam produces exactly the 28
# levels below, and they match the client's own LOC_LEVELS mapping.
#
# Beating that level is therefore the whole condition -- there is no separate
# world-progress requirement -- which is what rules.py gates each room on.
# One level can open several rooms: beach24 opens all eight of Big Wave
# Beach's themed minigame rooms at once.
DANGER_ROOM_UNLOCK = {
    "egypt_dangerroom":                   "egypt12",           # egypt12
    "egypt_dangerroom_minigame":          "egypt23",  # egypt23
    "egypt_dangerroom2":                  "egypt31",          # egypt31
    "pirate_dangerroom":                  "pirate4",          # pirate4
    "pirate_dangerroom2":                 "pirate33",         # pirate33
    "cowboy_dangerroom":                  "cowboy3",          # cowboy3
    "cowboy_dangerroom2":                 "cowboy33",         # cowboy33
    "future_dangerroom":                  "future4",          # future4
    "future_dangerroom2":                 "future32",         # future32
    "future_dangerroom_sunbomb":          "future33",  # future33
    "dark_dangerroom":                    "dark12",            # dark12
    "dark_dangerroom2":                   "dark26",           # dark26
    "dark_dangerroom_potion":             "dark27",     # dark27
    "beach_dangerroom":                   "beach20",           # beach20
    "beach_dangerroom2":                  "beach36",          # beach36
    "beach_dangerroom_minigame_egypt":    "beach24",  # beach24
    "beach_dangerroom_minigame_pirate":   "beach24",  # beach24
    "beach_dangerroom_minigame_cowboy":   "beach24",  # beach24
    "beach_dangerroom_minigame_future":   "beach24",  # beach24
    "beach_dangerroom_minigame_dark":     "beach24",  # beach24
    "beach_dangerroom_minigame_beach":    "beach24",  # beach24
    "beach_dangerroom_minigame_iceage":   "beach24",  # beach24
    "beach_dangerroom_minigame_lostcity": "beach24",  # beach24
    "iceage_dangerroom":                  "iceage20",          # iceage20
    "iceage_dangerroom2":                 "iceage35",         # iceage35
    "lostcity_dangerroom":                "lostcity20",        # lostcity20
    "lostcity_dangerroom2":               "lostcity39",       # lostcity39
    "kongfu_dangerroom":                  "kongfu14",          # kongfu14
    "kongfu_dangerroom2":                 "kongfu30",         # kongfu30
    "kongfu_dangerroom3":                 "kongfu47",         # kongfu47
    "eighties_dangerroom":                "eighties20",        # eighties20
    "eighties_dangerroom2":               "eighties38",       # eighties38
    "sky_dangerroom":                     "sky20",            # sky20
    "dino_dangerroom":                    "dino20",            # dino20
    "dino_dangerroom2":                   "dino36",           # dino36
    "modern_dangerroom":                  "modern20",          # modern20
    "modern_dangerroom2":                 "modern40",         # modern40
}


# Levels the game defines but never attaches to a map, so nothing can launch
# them and their checks can never fire by playing.
#
# VERIFIED, not assumed (2026-08-16): each of these appears in exactly ONE
# resource file, `import/02/02ed09922.json`, which holds level definitions.
# They are absent from the world tables (`import/01/01c3025f0.json`), from
# every world's map-node data (e.g. `import/06/0611992e3.json` for Egypt), and
# from index.js entirely -- zero references. A live level like egypt35 or
# egypt_dangerroom appears in four files by comparison.
#
# They were reachable in logic, so fill could put a world key or a gated plant
# on one and leave the seed uncompletable -- and random_zomboss_egypt sat in
# Ancient Egypt's opening stretch, making it a PREFERRED early-fill target.
#
# Dropped in active_locations() rather than deleted from the table below: the
# IDs there are assigned by increment, so removing an entry would renumber
# every location after it and break seeds already generated.
UNREACHABLE_LOCATIONS = frozenset({
    "random_egypt",   "random_zomboss_egypt",
    "random_pirate",  "random_zomboss_pirate",
    "random_cowboy",  "random_zomboss_cowboy",
    "random_future",  "random_zomboss_future",
    "random_dark",    "random_zomboss_dark",
    "random_beach",   # no random_zomboss_beach exists
    # Two Danger Rooms in the same position, found while deriving
    # DANGER_ROOM_UNLOCK (2026-08-17). Every other room has a map node in its
    # world's scene data AND a level whose FirstRewardParam opens it; these two
    # have neither, so nothing can put them on a map and nothing can raise their
    # progress above locked:
    #   kongfu_dangerroom4 -- the dangerroom_kongfu4 trophy exists, but no level
    #     awards it and Kongfu Temple's map (`import/08/08fde7325.json`) carries
    #     only three DANGERROOM nodes, for rooms 1-3.
    #   mixed_dangerroom2 -- appears in exactly ONE resource file, the level
    #     definitions. No trophy, no node. This is the "Mixed Danger Room" the
    #     side-path option describes as Modern Day's "Highway to the Danger
    #     Room"; it is the sole location of the Mixed Sidepath region, which is
    #     now always empty.
    "kongfu_dangerroom4", "mixed_dangerroom2",
    # An alternate "Iceage 24" -- the preset-plant variant where the lawn
    # starts frozen and the seed bank is five Hot Potatoes, with no sun
    # dropper. Frostbite Caves' map chain is nodes 1-40 carrying a plain
    # iceage24; there is no 24-B node, the world table does not list it, and
    # index.js never names it. It is the ONLY level asset in the game with a
    # capital letter in its name (checked across all 1183), so there is no
    # variant family behind it -- just this one stray.
    "iceage24_B",
    # The eight side paths with no map node anywhere. Each appears in exactly
    # one resource file -- its own definition -- and the world chooser has no
    # icon for the aggregate `epic` map that would otherwise reach them.
    # Nothing else can launch a level either: Level of the Day is gated on
    # feature_lod, which is never set true in this build, and the only seven
    # ForceNextLevel entries are the tutorial chain.
    #
    # They were the whole reason side paths "hang off the tutorial" in
    # regions.py -- there is nothing to hang them off, because they cannot be
    # reached at all.
    "bank_theft1", "bank_theft2", "bank_theft3", "bank_theft4", "bank_theft5",
    "epic_beghouled1", "epic_beghouled2", "epic_beghouled3", "epic_beghouled4",
    "epic_beghouled5",
    "floawerpot1", "floawerpot2", "floawerpot3",
    "reinforcemint_unused_try1", "reinforcemint_unused_try2", "reinforcemint_unused_try3",
    "rhythm1",
    "sandbox", "sandbox_green", "sandbox_modern", "sandbox_modern_night",
    "sandbox_sky",
    "shootingstarfruit1", "shootingstarfruit2", "shootingstarfruit3",
}) | frozenset(shop_location_name(c) for c in SHOP_ABSENT_COMMODITIES)


# Every side path named above has to be a real region, or its entry silently
# gates nothing.
_unknown_side_paths = set(SIDE_PATH_WORLD) - set(SIDE_PATH_REGIONS)
if _unknown_side_paths:
    raise ValueError(f"SIDE_PATH_WORLD names unknown side paths: {sorted(_unknown_side_paths)}")
_unknown_side_path_worlds = set(SIDE_PATH_WORLD.values()) - set(WORLD_REGIONS)
if _unknown_side_path_worlds:
    raise ValueError(f"side paths tied to unknown worlds: {sorted(_unknown_side_path_worlds)}")

# Every Danger Room the seed can build has to name the level that unlocks it, or
# rules.py silently leaves it ungated -- which is the bug this table exists to
# fix, and it would look identical to it working. The only rooms allowed to have
# no unlock level are the two that are never built at all.
_ungated_rooms = set(DANGER_ROOM_LOCATIONS) - set(DANGER_ROOM_UNLOCK) - UNREACHABLE_LOCATIONS
if _ungated_rooms:
    raise ValueError(f"Danger Rooms with no unlock level: {sorted(_ungated_rooms)}")
_unknown_rooms = set(DANGER_ROOM_UNLOCK) - set(DANGER_ROOM_LOCATIONS)
if _unknown_rooms:
    raise ValueError(f"DANGER_ROOM_UNLOCK names non-rooms: {sorted(_unknown_rooms)}")
