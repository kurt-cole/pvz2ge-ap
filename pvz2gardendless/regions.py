"""
PvZ2 Gardendless — region graph construction.

Entrances and locations are wired up here with no access rules attached;
rules.py applies all logic afterwards via the worlds.generic.Rules helpers,
keeping region shape and logic cleanly separated.
"""

from typing import Dict, TYPE_CHECKING

from BaseClasses import Region, ItemClassification

from .constants import KEYED_WORLDS, SHOP_REGION, SIDE_PATH_REGIONS
from .items import PvZ2Item
from .locations import ALL_REGIONS, PvZ2Location

if TYPE_CHECKING:
    from . import PvZ2GardendlessWorld


def create_regions(world: "PvZ2GardendlessWorld") -> None:
    player = world.player
    multiworld = world.multiworld

    menu     = Region("Menu",     player, multiworld)
    tutorial = Region("Tutorial", player, multiworld)
    menu.connect(tutorial)

    regions: Dict[str, Region] = {"Menu": menu, "Tutorial": tutorial}

    for name in ALL_REGIONS:
        if name not in regions:
            regions[name] = Region(name, player, multiworld)

    # Ancient Egypt — always accessible from Tutorial
    tutorial.connect(regions["Ancient Egypt"])

    # Ancient Egypt is split into sequential checkpoints (roughly every 10
    # levels) so generation logic doesn't treat the whole 35-level world as
    # flatly reachable with zero items. rules.py gates each entrance on
    # holding a sun producer and a cheap attacker.
    prev_egypt_region = regions["Ancient Egypt"]
    for checkpoint_name in ("Ancient Egypt Mid1", "Ancient Egypt Mid2", "Ancient Egypt Late"):
        prev_egypt_region.connect(regions[checkpoint_name], f"Enter {checkpoint_name}")
        prev_egypt_region = regions[checkpoint_name]

    # Keyed main worlds — rules.py requires each world's key on its entrance.
    for w in KEYED_WORLDS:
        if w == "Modern Day":
            continue  # handled separately, see below
        tutorial.connect(regions[w], f"Enter {w}")

    # Modern Day — unlocked purely by meeting the world-goal requirement
    # (see rules.py); there is no Modern Day Key.
    tutorial.connect(regions["Modern Day"], "Enter Modern Day")

    # Side paths — always accessible from Tutorial
    for sp in SIDE_PATH_REGIONS:
        tutorial.connect(regions[sp])

    # Shop — reachable from the world map at any time. Affordability is not
    # modelled: currency accrues from play and from Archipelago's own
    # coin/gem items, so a purchase is a matter of grinding rather than a
    # logic gate.
    tutorial.connect(regions[SHOP_REGION])

    # Add all locations to their regions
    for loc_data in world.active_locations():
        region = regions.get(loc_data.region, tutorial)
        loc = PvZ2Location(player, loc_data.name, loc_data.code, region)
        region.locations.append(loc)

    # Victory event in Modern Day. multiworld.completion_condition is set in
    # rules.py, alongside the rest of this world's logic.
    victory_loc = PvZ2Location(player, "Victory", None, regions["Modern Day"])
    victory_loc.place_locked_item(
        PvZ2Item("Victory", ItemClassification.progression, None, player))
    regions["Modern Day"].locations.append(victory_loc)

    for r in regions.values():
        multiworld.regions.append(r)
