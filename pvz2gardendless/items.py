"""
PvZ2 Gardendless — item definitions and item pool construction.
"""

import dataclasses
from typing import Dict, List, TYPE_CHECKING

from BaseClasses import Item, ItemClassification

from .constants import (
    slot_entry_groups, UPGRADE_POOL_SHARE, slot_stretch_groups, stretch_suffixes,
    ALL_LOGIC_PLANTS, BASE_ID, CHEAP_ATTACKER_PLANTS, GAME_NAME,
    KEY_NAME_TO_WORLD, KEYED_WORLDS, LOGIC_PLANTS, SUN_PRODUCER_PLANTS,
    WORLD_ENTRY_PLANTS, WORLD_REGIONS,
    progressive_count, progressive_item_name,
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

# The classification above is the SLOT-INDEPENDENT part: sun producers and world
# entry plants, which every seed's rules name the same way. The cheap attackers
# are decided per slot -- rules.py names only that slot's draw -- so they are
# promoted in PvZ2GardendlessWorld.create_item instead, and read here through
# slot_progression_plants().
# Every plant name, for create_item's per-slot classification. A set rather
# than a scan of PLANT_ITEMS on every call: create_item runs once per pool item.
PLANT_NAMES = {plant.name for plant in PLANT_ITEMS}


def _trim_upgrades(world, upgrades, keep_n):
    """`keep_n` of `upgrades`, drawn from the slot's own RNG.

    Drawn rather than truncated so a small seed does not always ship the same
    front slice of UPGRADE_GROUPS, and re-sorted afterwards so the pool is built
    in a fixed order regardless of how the draw fell.
    """
    keep_n = max(0, min(keep_n, len(upgrades)))
    keep = set(world.random.sample(range(len(upgrades)), keep_n))
    return [u for i, u in enumerate(upgrades) if i in keep]


def _pool_floor_groups(world):
    """The plant groups a rule this slot BUILT names, one plant of each needed.

    Shared by the upgrade trim and the progression-plant trim so the two cannot
    disagree about how much room logic actually requires.
    """
    # No attacker group: no rule names one, so the floor has nothing to protect
    # for them. The starter covers the gameplay side and is precollected.
    groups = [list(SUN_PRODUCER_PLANTS)]
    for w in sorted(world.enabled_worlds):
        # Narrowed, same as the rule: the floor must protect the ONE Jester
        # counter this slot named, not any of the 36 that can hurt him.
        groups.extend(slot_entry_groups(world, w))
        # Per-stretch requirements too, or a small seed can trim away the only
        # plant that opens the back half of a world it built.
        for suffix in stretch_suffixes(w):
            groups.extend(slot_stretch_groups(world, w, suffix))
    return groups


def _pool_floor_names(world) -> set:
    """One plant per floor group that is not already granted.

    A granted plant needs no slot: the rule naming it is already satisfied.
    """
    granted = set(getattr(world, "starting_plants", ()))
    names = set()
    for group in _pool_floor_groups(world):
        # A group with a granted member needs NOTHING reserved: the rule naming
        # it is already satisfied by a plant the player holds before the seed
        # starts. The cheap-attacker group is always in this case, because the
        # starter is drawn from it and precollected in every seed -- which is
        # why Ancient Egypt alone needs exactly one progression item, a sun
        # producer, and not two.
        if granted & set(group):
            continue
        eligible = sorted(n for n in group if n not in granted)
        if eligible:
            names.add(eligible[0])
    return names


def slot_progression_plants(world) -> set:
    """Plant names that are progression FOR THIS SLOT.

    Exactly the plants some rule this slot BUILT names, and nothing else.
    Anything a rule names has to be progression: AP only tracks advancement
    items in CollectionState.prog_items, so has_any() is permanently False for
    a "useful" item and a rule naming one silently loses that option. The
    converse matters just as much in a small seed -- a plant marked progression
    for a rule this seed does not have takes a slot from the useful plants,
    the filler and the traps, and an Egypt-only seed has room for none of them.

    Three sources, all per-slot:
      - the sun producers, for Ancient Egypt's egypt6 checkpoint, which every
        seed has
      - the entry plants of the worlds this seed actually ENABLED. rules.py
        skips a world that is not in the seed, so Lily Pad gates nothing in an
        Egypt-only run
      - this slot's own cheap-attacker draw
    """
    # NOT the cheap attackers. Nothing has named them since 2026-08-25, when the
    # attacker half of Ancient Egypt's egypt6 checkpoint was dropped for being
    # vacuous -- the precollected starter always satisfied it. Promoting a plant
    # no rule names costs a progression slot for nothing, which in a small seed
    # is a slot taken from the useful plants, the filler and the traps.
    plants = set(SUN_PRODUCER_PLANTS)
    for w in world.enabled_worlds:
        for group in slot_entry_groups(world, w):
            plants.update(group)
        # ...and whatever this slot's BUILT stretches of that world ask for.
        for suffix in stretch_suffixes(w):
            for group in slot_stretch_groups(world, w, suffix):
                plants.update(group)
    return plants


# A rule naming a plant with no matching item is a rule that can never pass,
# and it would fail silently -- state.has() just returns False forever. Checked
# over every plant any rule COULD name, not just the always-progression ones,
# since the per-slot draw can surface any of the 46.
_unknown_logic_plants = ALL_LOGIC_PLANTS - {plant.name for plant in PLANT_ITEMS}
if _unknown_logic_plants:
    raise ValueError("access rules reference plants that have no item: "
                     f"{sorted(_unknown_logic_plants)}")

# World Key items — NO LONGER IN THE POOL as of 2026-08-23. A world is opened
# by the first of its Progressive <World> unlocks instead, so "Wild West Key"
# plus two Progressive Wild West became three Progressive Wild West: same
# number of items, one fewer concept.
#
# The definitions stay because item IDs are positional and removing them would
# renumber every item after them, and because the client still honours a key
# from a seed generated before the change.
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

# A cosmetic filler: grants one costume, for a random plant you already hold,
# out of the 309 the game has across the 120 plants Archipelago manages.
# Appended after every other block so no existing item ID moves. It is NOT
# added to FILLER_ITEMS, which would have shifted the trap and upgrade blocks
# that are numbered from the end of it.
COSTUME_FILLER = "Random Plant Costume"
COSTUME_ITEMS: List[PvZ2ItemData] = [
    PvZ2ItemData(COSTUME_FILLER, ItemClassification.filler,
                 _upgrade_base + len(UPGRADE_ITEMS)),
]

# Everything get_filler_item_name() and the pool builder may hand out. Kept
# separate from FILLER_ITEMS so that list can stay exactly the currency block
# its IDs were assigned from.
FILLER_POOL: List[PvZ2ItemData] = FILLER_ITEMS + COSTUME_ITEMS

# Re-rolls which costume every dressed plant is wearing, including taking some
# back off. Appended past the costume filler for the same reason that was
# appended past the upgrades: TRAP_ITEMS is the block the upgrade IDs are
# numbered from, so it cannot grow.
COSTUME_SHUFFLE_TRAP = "Costume Shuffle Trap"
COSTUME_TRAP_ITEMS: List[PvZ2ItemData] = [
    PvZ2ItemData(COSTUME_SHUFFLE_TRAP, ItemClassification.trap,
                 _upgrade_base + len(UPGRADE_ITEMS) + len(COSTUME_ITEMS)),
]

# Currency traps: the filler block's mirror image. Named with a leading minus
# so the client can read the amount straight off the name, the same way it does
# for "500 Coins" -- one regex either side, and no table to drift.
#
# Sized at the middle of each filler range (500 of 100/500/1000, 20 of
# 10/20/50), so a trap costs about what one filler grant gives.
#
# A trap can never push a balance below zero: the client takes
# min(balance, amount) and forgives the rest rather than carrying a debt that
# would silently eat later income.
#
# Appended past the costume trap for the same reason that was appended past the
# upgrades -- TRAP_ITEMS is the block UPGRADE_ITEMS is numbered from, so it
# cannot grow.
COIN_TRAP = "-500 Coins"
GEM_TRAP  = "-20 Gems"
_currency_trap_base = (_upgrade_base + len(UPGRADE_ITEMS) + len(COSTUME_ITEMS)
                       + len(COSTUME_TRAP_ITEMS))
CURRENCY_TRAP_ITEMS: List[PvZ2ItemData] = [
    PvZ2ItemData(name, ItemClassification.trap, _currency_trap_base + i)
    for i, name in enumerate([COIN_TRAP, GEM_TRAP])
]

# Every trap the pool builder deals out, and the order it rotates through.
TRAP_POOL: List[PvZ2ItemData] = (TRAP_ITEMS + COSTUME_TRAP_ITEMS
                                 + CURRENCY_TRAP_ITEMS)
TRAP_CYCLE = [t.name for t in TRAP_POOL]

# Which yaml option carries each trap's weight. Keyed by item name so a rename
# on either side is a KeyError at import rather than a trap that silently
# stops being dealt.
TRAP_WEIGHT_OPTIONS = {
    LAWN_MOWER_TRAP:      "trap_weight_lawn_mower",
    COSTUME_SHUFFLE_TRAP: "trap_weight_costume_shuffle",
    COIN_TRAP:            "trap_weight_coins",
    GEM_TRAP:             "trap_weight_gems",
}
if set(TRAP_WEIGHT_OPTIONS) != set(TRAP_CYCLE):
    raise ValueError("TRAP_WEIGHT_OPTIONS and TRAP_CYCLE disagree: "
                     f"{set(TRAP_WEIGHT_OPTIONS) ^ set(TRAP_CYCLE)}")


def trap_weights(world) -> List[int]:
    """This slot's trap weights, in TRAP_CYCLE order."""
    return [getattr(world.options, TRAP_WEIGHT_OPTIONS[name]).value
            for name in TRAP_CYCLE]


def weighted_trap_names(trap_count: int, weights: List[int]) -> List[str]:
    """`trap_count` trap names, divided between the traps by weight.

    Weights are RELATIVE: only their ratio matters, so 25/25/25/25 and
    50/50/50/50 are the same even mix. All zero means no traps at all, which is
    the only way the result is shorter than trap_count.

    Deterministic, deliberately. The old uniform rotation could promise that a
    slot's trap mix was identical every generation and did not depend on how
    the RNG happened to fall, and that is worth keeping -- so this apportions
    by largest remainder rather than sampling. Equal weights reproduce the old
    `TRAP_CYCLE[i % len(TRAP_CYCLE)]` rotation exactly, item for item, which is
    what makes the defaults a no-op against every seed generated before the
    weights existed.
    """
    total = sum(weights)
    if trap_count <= 0 or total <= 0:
        return []

    # Largest remainder: floor each share, then hand the leftovers to the
    # biggest fractional parts. Ties break by TRAP_CYCLE position, so the
    # result never depends on float comparison order.
    quotas = [trap_count * w / total for w in weights]
    counts = [int(q) for q in quotas]
    short = trap_count - sum(counts)
    by_remainder = sorted(range(len(weights)),
                          key=lambda i: (-(quotas[i] - counts[i]), i))
    for i in by_remainder[:short]:
        counts[i] += 1

    assert sum(counts) == trap_count, (counts, trap_count)

    # Interleaved rather than blocked, so a partly-filled seed still gets a
    # spread of trap types instead of every Lawn Mower Trap first.
    #
    # Driven by what is LEFT rather than by len(names) < trap_count: each pass
    # of the inner loop takes at least one, so this always terminates. The
    # count-driven form spins forever if the apportionment above ever comes up
    # short, which is a far worse way to fail than a wrong number of traps.
    names, left = [], list(counts)
    while any(left):
        for i, name in enumerate(TRAP_CYCLE):
            if left[i]:
                names.append(name)
                left[i] -= 1
    return names

# Progressive world unlocks — two per world, including Ancient Egypt, which
# has no key. A world opens at its World Key level; the first of these carries
# it to its Zomboss and the second to its final level (see
# locations.world_stretches for the exact cuts). Ancient Egypt is playable from
# the start, so for that world these are the only gates it has.
#
# APPENDED AFTER every other group on purpose: item IDs are positional, so a
# new group anywhere else renumbers everything after it and breaks seeds
# already generated.
PROGRESSIVE_WORLD_ITEMS: List[PvZ2ItemData] = []
_progressive_base = _currency_trap_base + len(CURRENCY_TRAP_ITEMS)
for i, world_name in enumerate(WORLD_REGIONS):
    PROGRESSIVE_WORLD_ITEMS.append(PvZ2ItemData(
        progressive_item_name(world_name),
        ItemClassification.progression, _progressive_base + i))

PROGRESSIVE_ITEM_TO_WORLD = {progressive_item_name(w): w for w in WORLD_REGIONS}

# Guaranteed gems. One copy, worth 150, in EVERY seed regardless of size, and
# rules.py pins it to a location reachable before Ancient Egypt 9.
#
# The problem they solve: gems are the shop's only currency, and under
# Archipelago a player can earn exactly zero of them. The game's whole resource
# set contains one GIVE_GEM action, worth 20, inside the PREMIUM_BRING_OUT
# dialogue -- which the client deliberately silences, because that flow
# softlocked a real run on the world chooser. So every gem a player will ever
# see arrives as an item.
#
# And the gem FILLER only appears in large seeds. Filler is what is left after
# the plants, and the plants outnumber the locations until a seed is several
# worlds wide: an Egypt-only shopsanity seed is 50 locations carrying 7 shop
# cards worth 210 gems and, before this, zero gem items. A world unlock landing
# on a 30-gem card was then unwinnable rather than a grind. Kurt hit exactly
# that in a test run.
#
# Progression, not filler, and that is the entire point: filler is trimmed away
# first in a small seed, which is the case that needs it. No access rule NAMES
# it -- affordability is still not modelled in logic -- so it gates nothing; the
# classification is what keeps it in the pool, makes fill place it somewhere
# reachable, and lets rules.py restrict WHERE with an item rule.
#
# One 150 rather than two 75s (Kurt, 2026-08-23). A single item is a single
# thing to find: two halves can both land late, and half of a gem budget buys
# a 30-gem card just as well as none does if the other half is behind the wall
# it was meant to open.
#
# The name is load-bearing. The client reads the amount straight off it with
# /^(\d+) (Coins|Gems)$/, the same regex that handles "500 Coins", so this
# needs no client change and no rebuild. Do not rename it to anything that
# regex will not match, or the item silently becomes a toast and no gems.
#
# APPENDED AFTER every other group, PROGRESSIVE_WORLD_ITEMS included: item IDs
# are positional, so a new group anywhere else renumbers everything after it
# and breaks seeds already generated.
GEM_GRANT = "150 Gems"
GEM_GRANT_COUNT = 1
_gem_grant_base = _progressive_base + len(PROGRESSIVE_WORLD_ITEMS)
GEM_GRANT_ITEMS: List[PvZ2ItemData] = [
    PvZ2ItemData(GEM_GRANT, ItemClassification.progression, _gem_grant_base),
]

ALL_ITEMS: List[PvZ2ItemData] = (PLANT_ITEMS + KEY_ITEMS + FILLER_ITEMS
                                 + TRAP_ITEMS + UPGRADE_ITEMS + COSTUME_ITEMS
                                 + COSTUME_TRAP_ITEMS + CURRENCY_TRAP_ITEMS
                                 + PROGRESSIVE_WORLD_ITEMS + GEM_GRANT_ITEMS)
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

# Buckets for !hint. Hinting a group name resolves to every item in it, so
# "!hint World Keys" answers where all eleven keys are in one command instead of
# eleven. Every item belongs to at least one, checked below -- the currencies
# and the costume used to belong to none, so there was no way to ask about them
# except by their exact name.
ITEM_NAME_GROUPS: Dict[str, set] = {
    "Plants":     {i.name for i in PLANT_ITEMS},
    # The five sun producers, as their own group. Worth hinting for on its own:
    # a sun producer is the one plant every seed needs and the one plant that is
    # never handed over -- starting_plants refuses to grant one, and Ancient
    # Egypt expects one from level 6 -- so "where is my sun" is a real question
    # a player will have, and !hint Plants answers it with any of 135.
    #
    # The list is SUN_PRODUCER_PLANTS itself rather than a copy, so a plant
    # added to or dropped from the gate moves here with it. Solar Tomato was
    # dropped from that list once already.
    "Sun Plants": set(SUN_PRODUCER_PLANTS),
    # The unlocks ARE the keys now, so both names answer with them -- a player
    # who learned "!hint World Keys" should not get an empty answer. The Key
    # items themselves are still defined (item IDs are positional) but no seed
    # generated after 2026-08-23 contains one.
    "World Unlocks": {i.name for i in PROGRESSIVE_WORLD_ITEMS},
    "World Keys": {i.name for i in PROGRESSIVE_WORLD_ITEMS}
                  | {i.name for i in KEY_ITEMS},
    "Traps":      {i.name for i in TRAP_POOL},
    "Upgrades":   {i.name for i in UPGRADE_ITEMS},
    "Costumes":   {i.name for i in COSTUME_ITEMS},
    # Positive currency only. The two negative ones are traps and are in
    # "Traps"; folding them in here would answer "where are my coins" with the
    # places that take them away.
    "Coins":      {i.name for i in FILLER_ITEMS if i.name.endswith("Coins")},
    # The guaranteed grants answer here too: a player asking where their gems
    # are means all of them, and these are the ones worth finding.
    "Gems":       {i.name for i in FILLER_ITEMS if i.name.endswith("Gems")}
                  | {i.name for i in GEM_GRANT_ITEMS},
    "Filler":     {i.name for i in FILLER_ITEMS} | {i.name for i in COSTUME_ITEMS},
}
ITEM_NAME_GROUPS["Currency"] = ITEM_NAME_GROUPS["Coins"] | ITEM_NAME_GROUPS["Gems"]

# Singular aliases. A player typing "!hint World Key" means the group, and AP
# resolves a group name only on an exact match -- so without this the natural
# phrasing falls through to fuzzy-matching one item and hints a single key.
for _plural, _singular in (
    ("Plants", "Plant"), ("World Keys", "World Key"), ("Traps", "Trap"),
    ("Upgrades", "Upgrade"), ("Costumes", "Costume"), ("Coins", "Coin"),
    ("Gems", "Gem"), ("World Unlocks", "World Unlock"),
    ("Sun Plants", "Sun Plant"),
):
    ITEM_NAME_GROUPS[_singular] = ITEM_NAME_GROUPS[_plural]

# ...and the names a player is likely to reach for instead. AP resolves a group
# only on an exact match, so a near miss falls through to fuzzy-matching a
# single ITEM and hints one plant rather than the group.
for _alias in ("Sun", "Sun Producers", "Sun Producer", "Sunflowers"):
    ITEM_NAME_GROUPS[_alias] = ITEM_NAME_GROUPS["Sun Plants"]

# Same rule the location groups follow: a group sharing a name with an item
# makes !hint ambiguous, and AP cannot tell the player which one it picked.
_item_group_clashes = set(ITEM_NAME_GROUPS) & set(ITEM_NAME_TO_ITEM)
if _item_group_clashes:
    raise ValueError("item group names collide with item names: "
                     f"{sorted(_item_group_clashes)}")

# An item in no group cannot be hinted as part of anything, which is how the
# currencies and the costume were missed.
_ungrouped = {i.name for i in ALL_ITEMS} - set().union(*ITEM_NAME_GROUPS.values())
if _ungrouped:
    raise ValueError(f"items in no hint group: {sorted(_ungrouped)}")

# Order filler is dealt out in. It deliberately interleaves the currencies
# instead of reusing FILLER_ITEMS order, which is grouped by type and would
# hand out a long run of coins followed by a long run of gems. The costume
# sits once in the rotation, so it is roughly one filler slot in seven.
FILLER_CYCLE = ["100 Coins", "500 Coins", "10 Gems", COSTUME_FILLER,
                "1000 Coins", "20 Gems", "50 Gems"]

# The two lists drifting apart would not raise: a name here that is not a real
# item reaches create_item() as an unknown, which builds it with code=None --
# and AP reads a None code as an event, not a pool item.
if set(FILLER_CYCLE) != {f.name for f in FILLER_POOL}:
    raise ValueError("FILLER_CYCLE and FILLER_POOL disagree: "
                     f"{sorted(set(FILLER_CYCLE) ^ {f.name for f in FILLER_POOL})}")


def create_item_pool(world: "PvZ2GardendlessWorld", pool_size: int) -> List[Item]:
    """Build this slot's item pool. Does not touch multiworld.itempool --
    the caller decides how to merge it in, since that pool is shared by
    every player in the multiworld."""
    pool: List[Item] = []

    # The progressive unlocks: three per world, or two for Ancient Egypt, which
    # needs none to enter. The first opens the world, the second and third its
    # middle and last stretches. A world this seed left out is skipped --
    # nothing behind it exists.
    #
    # These replaced the World Key items entirely, and they are enforced in
    # game as well as in logic, so they are the least negotiable thing in the
    # pool.
    for w in sorted(world.enabled_worlds):
        # Sized to the stretches this slot BUILDS. Under the world_key goal a
        # world is one stretch long, so its second and third unlocks would gate
        # nothing and ship as dead items -- 24 of them in a 12-world seed.
        for _ in range(progressive_count(
                w, world.options.goal_type.value,
                bool(world.options.include_levels_past_goal))):
            pool.append(world.create_item(progressive_item_name(w)))

    # Permanent upgrades, when the option has the game withhold them. With it
    # off the game hands them out itself, so shipping them as items too would
    # mean receiving something already owned.
    #
    # Added before the plants so the plant trim below knows how much room is
    # actually left: these are as non-negotiable as the unlocks.
    if world.options.shuffle_upgrades:
        # One copy per level the group covers: three Progressive Sun Shovels,
        # one Sky Shield. Sized off the codename list so adding a level to a
        # group is a constants.py edit alone.
        upgrades = [name for name, codenames in UPGRADE_GROUPS for _ in codenames]

        # THE PROPORTIONAL SHARE. Upgrades gate nothing, so a seed too small to
        # carry all 14 should carry a share of them and spend the rest on
        # plants. 20% of a full seed is 106, far past the 14 that exist, so this
        # is a no-op everywhere except the small seeds it exists for.
        share = pool_size * UPGRADE_POOL_SHARE // 100
        if share < len(upgrades):
            upgrades = _trim_upgrades(world, upgrades, share)

        # THE UPGRADES GIVE BEFORE THE PLANTS DO. No access rule anywhere reads
        # an upgrade item -- they raise starting sun, plant food capacity, seed
        # slots and mowers, and gate nothing -- so an upgrade that does not fit
        # costs the player convenience, where a progression plant that does not
        # fit costs the seed its logic.
        #
        # This only bites where the seed is smaller than the mandatory block,
        # which the goal trim made reachable: Ancient Egypt alone under the
        # world_key goal is the tutorial plus egypt1-8, twelve locations against
        # fourteen upgrades. Before this it failed to generate outright.
        #
        # Reserve is the plant floor -- one plant per group some rule this seed
        # built names -- computed the same way as the trim further down, plus
        # whatever is already in the pool. Egypt-only under world_key needs
        # exactly one: a sun producer, since the egypt6 checkpoint's other half
        # is a cheap attacker and the starter is always one, precollected.
        reserve = len(pool) + len(_pool_floor_names(world))
        room = max(0, pool_size - reserve)
        if room < len(upgrades):
            upgrades = _trim_upgrades(world, upgrades, room)
        for name in upgrades:
            pool.append(world.create_item(name))

    # The guaranteed gems, before the plants for the same reason the upgrades
    # are: not negotiable, and the trim below has to see the room they take.
    #
    # ONLY WITH SHOPSANITY. The grant exists to stop a progression item stranding
    # behind a shop card the player cannot afford, and shop cards are the only AP
    # locations in this game that cost anything -- no access rule reads currency,
    # and nothing else in a seed can be bought. With shopsanity off there is no
    # wall to break, and a mandatory item in a 43-check seed is a real cost: it
    # is a slot that would otherwise be a plant.
    #
    # The gem FILLER (10/20/50 Gems) is not gated this way and should not be.
    # Those are ordinary filler with in-game value; this one is mandatory, which
    # is what makes it worth justifying. A currency trap arriving in a seed with
    # no gems is harmless either way -- the client takes min(balance, debt) and
    # forgives the rest rather than holding a debit against later income.
    if world.options.shopsanity:
        for _ in range(GEM_GRANT_COUNT):
            pool.append(world.create_item(GEM_GRANT))

    # Progression plants. Every rule that names a plant is a has_any() over a
    # whole GROUP, so what logic needs is one plant from each group that some
    # rule this seed built actually asks for -- not all 55 of them.
    #
    # That is what makes them trimmable at all. An Egypt-only seed is 43
    # locations against 55 progression plants, and used to fail to generate
    # outright.
    #
    # The floor is one plant from every group a rule names, drawn from the
    # slot's own RNG so a seed is stable and slots differ. Below that a gate
    # becomes unsatisfiable, so the ValueError is still the right answer.
    #
    # WHICH groups depends on the seed. Ancient Egypt's egypt6 checkpoint is in
    # every seed, so its two are always here. WORLD_ENTRY_PLANTS adds one group
    # per requirement of each ENABLED world -- Lily Pad if Big Wave Beach is in,
    # Blover if Far Future is -- and adds nothing for a world the seed left out,
    # whose entrance rules.py never builds. Miss this and a small seed can trim
    # away the only plant that opens a world it enabled, which fill reports as
    # unreachable locations rather than as anything pointing back here.
    # Plants the player already starts with are not shipped again. Before this
    # the starter was precollected AND left in the pool, so one check in every
    # seed handed over a plant already owned; at starting_plants 10 that would
    # be ten of them, which is a quarter of an Egypt-only seed.
    #
    # Dropping a progression plant here is safe precisely because the player
    # HAS it: the rule naming it is already satisfied, so the floor below has
    # nothing left to protect for that group.
    _granted = set(getattr(world, "starting_plants", ()))
    _slot_prog = slot_progression_plants(world) - _granted
    prog_plants = [p for p in PLANT_ITEMS
                   if p.name in _slot_prog and p.name not in _granted]
    room = pool_size - len(pool)
    if room < len(prog_plants):
        # The attacker group is the slot's OWN draw, not all 46: those are the
        # only names rules.py put in the Egypt 6 rule, so keeping one of the
        # other 36 would not satisfy it.
        groups = _pool_floor_groups(world)
        prog_names = {p.name for p in prog_plants}
        floor_names = set()
        for group in groups:
            # Already satisfied by a granted plant: reserve nothing. See
            # _pool_floor_names, which has to agree with this exactly or the
            # upgrade trim reserves a different amount than the plant trim uses.
            if _granted & set(group):
                continue
            eligible = sorted(n for n in group if n in prog_names)
            if eligible:
                floor_names.add(world.random.choice(eligible))
        if room < len(floor_names):
            raise ValueError(
                f"item pool ({len(pool)} unlocks, upgrades and gem grants) "
                f"leaves {room} of the {pool_size} locations this slot builds, "
                f"too few for the {len(floor_names)} plants its access rules "
                "need; raise world_count or turn on include_side_paths")
        spare = [p.name for p in prog_plants if p.name not in floor_names]
        keep = floor_names | set(world.random.sample(spare, room - len(floor_names)))
        prog_plants = [p for p in prog_plants if p.name in keep]
    for plant in prog_plants:
        pool.append(world.create_item(plant.name))

    # Useful plants fill what is left. Normally that is all of them, but a small
    # seed can have fewer locations than the full plant list, and these are the
    # only part of the block that can give: they gate nothing, so a seed short
    # of room ships fewer plants rather than failing to generate. A one-world
    # seed with side paths off is 101 locations (140 with shopsanity) against
    # 149 items, which is where this bites.
    #
    # Which ones go is drawn from the slot's own RNG so it is stable for a seed
    # and differs between slots, then re-sorted into PLANT_ITEMS order so the
    # pool itself is built in a fixed order regardless of what the draw picked.
    # Everything not progression FOR THIS SLOT, which includes the 36 cheap
    # attackers the draw passed over. They are ordinary plants: still worth
    # having, still in the pool when there is room, and the first thing to go
    # when there is not.
    useful = [p for p in PLANT_ITEMS
              if p.name not in _slot_prog and p.name not in _granted]
    room = pool_size - len(pool)
    if room < len(useful):
        # Cannot be negative: the progression-plant trim above already sized
        # the pool to fit, and raises if even the floor does not.
        assert room >= 0, f"pool {len(pool)} overruns {pool_size} locations"
        keep = set(world.random.sample([p.name for p in useful], room))
        useful = [p for p in useful if p.name in keep]
    for plant in useful:
        pool.append(world.create_item(plant.name))

    # Everything left over is filler, of which trap_percentage becomes
    # traps. Traps only ever displace filler, never a plant or a key.
    # Cannot go negative: the useful-plant trim above already sized the pool to
    # fit, and raises if even the mandatory block does not. Asserted rather than
    # assumed, since a short pool fails much later and much less legibly.
    remaining = pool_size - len(pool)
    assert remaining >= 0, f"pool {len(pool)} overruns {pool_size} locations"
    trap_count = remaining * world.options.trap_percentage.value // 100
    # Apportioned by weight rather than picked at random, so a slot's trap mix
    # is the same every generation and does not depend on how the RNG happened
    # to fall. The default weights are even and reproduce the old uniform
    # rotation exactly.
    trap_names = weighted_trap_names(trap_count, trap_weights(world))
    for name in trap_names:
        pool.append(world.create_item(name))
    # Not trap_count: every weight set to 0 means the player asked for no traps
    # at all, and those slots go back to filler rather than leaving the pool
    # short of the locations it has to fill.
    remaining -= len(trap_names)

    for i in range(remaining):
        pool.append(world.create_item(FILLER_CYCLE[i % len(FILLER_CYCLE)]))

    return pool
