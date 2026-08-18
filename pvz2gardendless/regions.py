"""
PvZ2 Gardendless — region graph construction.

Entrances and locations are wired up here with no access rules attached;
rules.py applies all logic afterwards via the worlds.generic.Rules helpers,
keeping region shape and logic cleanly separated.
"""

from typing import Dict, TYPE_CHECKING

from BaseClasses import Region, ItemClassification

from .constants import (
    ALL_WORLD_REGIONS, KEYED_WORLDS, SHOP_REGION, SIDE_PATH_CHAIN,
    SIDE_PATH_REGIONS, SIDE_PATH_UNLOCK, SIDE_PATH_WORLD, WORLD_REGIONS,
    WORLD_STRETCHES,
)
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

    # Regions of worlds this seed left out are never built, so nothing can be
    # placed in them and nothing can route through them. That extends to the
    # side paths of a dropped world, which have no way in once it is gone.
    # Shop is built even with shopsanity off: an empty region costs nothing,
    # while a missing one would break the connect below.
    # include_side_paths off drops all of them, worldless ones included --
    # see the option for why that is the default.
    if world.options.include_side_paths:
        dropped_side_paths = {sp for sp, owner in SIDE_PATH_WORLD.items()
                              if owner not in world.enabled_worlds}
    else:
        dropped_side_paths = set(SIDE_PATH_REGIONS)
    built = ({r for r in ALL_REGIONS if r not in ALL_WORLD_REGIONS}
             | world.enabled_regions) - dropped_side_paths
    for name in ALL_REGIONS:
        if name in built and name not in regions:
            regions[name] = Region(name, player, multiworld)

    # Ancient Egypt — always accessible from Tutorial, and always built
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
    # Only the enabled ones get an entrance, which is what rules.py keys off:
    # it walks the same list and would raise on a missing entrance otherwise.
    for w in KEYED_WORLDS:
        if w == "Modern Day":
            continue  # handled separately, see below
        if w not in world.enabled_worlds:
            continue
        tutorial.connect(regions[w], f"Enter {w}")

    # Modern Day — unlocked purely by meeting the world-goal requirement
    # (see rules.py); there is no Modern Day Key.
    tutorial.connect(regions["Modern Day"], "Enter Modern Day")

    # Shop — the store button does not exist until egypt6 is cleared. That is
    # the game's own rule, in index.js's feature-unlock chain:
    #   feature_coins   <- tutorial4      feature_powerup/zengarden <- egypt5
    #   feature_store   <- egypt6
    # egypt6 is the first level of Mid1, so hanging the shop off that region
    # gives it exactly the game's condition and inherits Mid1's sun-and-attacker
    # rule for free. It used to hang off Tutorial, which put all 39 shopsanity
    # checks in sphere 1 and made a shopsanity seed open five times as wide as
    # the same seed without it.
    #
    # Affordability is still not modelled: currency accrues from play and from
    # Archipelago's own coin/gem items, so a purchase is a matter of grinding
    # rather than a logic gate.
    regions["Ancient Egypt Mid1"].connect(regions[SHOP_REGION])

    active = world.active_locations()

    # Cut each world into sequential stretches, so holding its key opens the
    # start of it rather than all 44-53 levels at once. Locations keep their
    # world as loc_data.region -- that is what active_locations() and the hint
    # groups read -- and are routed into a stretch here by their position in
    # the world's own level order.
    #
    # Ancient Egypt is skipped: it already declares a four-region split in
    # locations.py and re-cutting it would fight that. rules.py escalates its
    # existing gates instead.
    stretch_of: Dict[str, Region] = {}
    for w in sorted(world.enabled_worlds):
        if w == "Ancient Egypt":
            continue
        w_locs = [l for l in active if l.region in WORLD_REGIONS[w]]
        # Too small to be worth cutting; Aerial Fortress at 16 is the smallest
        # world that still is. Below two per stretch the split says nothing.
        if len(w_locs) < len(WORLD_STRETCHES) * 2:
            continue
        prev = regions[w]
        for suffix in WORLD_STRETCHES[1:]:
            name = w + suffix
            regions[name] = Region(name, player, multiworld)
            prev.connect(regions[name], f"Enter {name}")
            prev = regions[name]
        # Ceiling division, so the remainder lands in the earlier stretches and
        # the last one is never the biggest.
        size = -(-len(w_locs) // len(WORLD_STRETCHES))
        for i, l in enumerate(w_locs):
            idx = min(i // size, len(WORLD_STRETCHES) - 1)
            stretch_of[l.name] = regions[w + WORLD_STRETCHES[idx]]

    # Side paths hang off the stretch holding the level that reveals them, not
    # off Tutorial and not off their world's opening. A side path is entered
    # from a branch node on a world map, so it is not reachable until the level
    # that node hangs off is -- you cannot walk into a Far Future side path
    # from Egypt, and you cannot walk into the Squash quest before Egypt 6.
    #
    # They used to connect to the world's opening on the reasoning that gating
    # deeper than the game does would be too strict. That had it backwards: the
    # game gates Squash at egypt6 and Appease-mint at egypt29, both strictly
    # deeper than the opening, and Ancient Egypt's opening is ungated -- so its
    # two side paths, 18 checks including anything fill cared to hide there,
    # were sphere 1. A real seed put two world keys in Appease-mint.
    #
    # Stretch granularity is the most this model can say. `can_reach` on the
    # unlock level is exactly "its region is reachable", so connecting to that
    # region is the same rule an access rule would express, without needing an
    # indirect condition on the entrance.
    #
    # The eight paths the game ties to no world are standalone content reached
    # from the world chooser, and stay connected to Tutorial. All eight are
    # empty in every seed (see UNREACHABLE_LOCATIONS), so this only decides
    # where an empty region hangs.
    declared_region = {l.name: l.region for l in active}
    for sp in SIDE_PATH_REGIONS:
        if sp not in regions:
            continue  # its world is not in this seed, so neither is it
        parent = None
        chain_target = SIDE_PATH_CHAIN.get(sp)
        if chain_target is not None:
            # Reached through another side path rather than from a world map.
            parent = regions.get(chain_target)
        else:
            unlock = SIDE_PATH_UNLOCK.get(sp)
            if unlock is not None:
                # stretch_of first: it is the finer of the two, and holds every
                # world the stretch cut applied to. Ancient Egypt is not in it
                # -- it declares its own four regions -- so fall back to what
                # locations.py declared. A world too small to cut has neither,
                # and lands on the world region below.
                parent = stretch_of.get(unlock)
                if parent is None and unlock in declared_region:
                    parent = regions.get(declared_region[unlock])
        if parent is None:
            owner = SIDE_PATH_WORLD.get(sp)
            parent = regions[owner] if owner in regions else tutorial
        parent.connect(regions[sp], f"Enter {sp}")

    # Add all locations to their regions. Indexed, not .get(name, tutorial):
    # ALL_REGIONS is derived from these same locations, so a miss is
    # impossible today and would mean the two had drifted apart. Falling back
    # to Tutorial would quietly relocate the orphans into sphere 1, where
    # nothing gates them -- a KeyError at generation time is the far cheaper
    # failure.
    for loc_data in active:
        region = stretch_of.get(loc_data.name) or regions[loc_data.region]
        region.locations.append(
            PvZ2Location(player, loc_data.name, loc_data.code, region))

    # Victory event in Modern Day. multiworld.completion_condition is set in
    # rules.py, alongside the rest of this world's logic.
    victory_loc = PvZ2Location(player, "Victory", None, regions["Modern Day"])
    victory_loc.place_locked_item(
        PvZ2Item("Victory", ItemClassification.progression, None, player))
    regions["Modern Day"].locations.append(victory_loc)

    for r in regions.values():
        multiworld.regions.append(r)
