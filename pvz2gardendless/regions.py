"""
PvZ2 Gardendless — region graph construction.

Entrances and locations are wired up here with no access rules attached;
rules.py applies all logic afterwards via the worlds.generic.Rules helpers,
keeping region shape and logic cleanly separated.
"""

from typing import Dict, TYPE_CHECKING

from BaseClasses import Region, ItemClassification

from .constants import (
    ALL_WORLD_REGIONS, EGYPT_SUN_CUT, KEYED_WORLDS, SHOP_REGION,
    SIDE_PATH_CHAIN, SIDE_PATH_REGIONS, SIDE_PATH_UNLOCK, SIDE_PATH_WORLD,
    WORLD_REGIONS, WORLD_STRETCHES, stretch_suffixes,
)
from .items import PvZ2Item
from .locations import ALL_REGIONS, PvZ2Location, world_stretches

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

    # Keyed main worlds — rules.py requires each world's key on its entrance.
    # Only the enabled ones get an entrance, which is what rules.py keys off:
    # it walks the same list and would raise on a missing entrance otherwise.
    # Modern Day is in here like any other keyed world as of 2026-08-23. It
    # used to be connected separately and gated on the world-goal count, back
    # when reaching it WAS the goal; the run now ends on completing worlds, so
    # it is just a world with a key again.
    for w in KEYED_WORLDS:
        if w not in world.enabled_worlds:
            continue
        tutorial.connect(regions[w], f"Enter {w}")

    active = world.active_locations()

    # Cut each world into sequential stretches, so holding its key opens the
    # start of it rather than all 44-53 levels at once. Locations keep their
    # world as loc_data.region -- that is what active_locations() and the hint
    # groups read -- and are routed into a stretch here.
    #
    # The cuts are the world's own milestones (World Key level, then Zomboss),
    # not a count: see locations.world_stretches. Ancient Egypt goes through
    # the same loop as of 2026-08-23; it used to declare a bespoke four-region
    # split of its own, cut in different places.
    stretch_of: Dict[str, Region] = {}
    for w in sorted(world.enabled_worlds):
        w_locs = [l for l in active if l.region in WORLD_REGIONS[w]]
        # Too small to be worth cutting. Below two per stretch the split says
        # nothing, and nothing in the game is that small today.
        if len(w_locs) < len(WORLD_STRETCHES) * 2:
            continue
        suffixes = stretch_suffixes(w)
        prev = regions[w]
        for suffix in suffixes[1:]:
            name = w + suffix
            regions[name] = Region(name, player, multiworld)
            prev.connect(regions[name], f"Enter {name}")
            prev = regions[name]
        parts = world_stretches((l.name for l in w_locs),
                                EGYPT_SUN_CUT if w == "Ancient Egypt" else None)
        for idx, part in enumerate(parts):
            for loc_name in part:
                stretch_of[loc_name] = regions[w + suffixes[idx]]

    # Shop — the store button does not exist until egypt6 is cleared. That is
    # the game's own rule, in index.js's feature-unlock chain:
    #   feature_coins   <- tutorial4      feature_powerup/zengarden <- egypt5
    #   feature_store   <- egypt6
    # Hung off the stretch holding egypt6, which is Egypt's " Early" -- so the
    # store button exists exactly when the game says it does, and inherits that
    # stretch's sun-and-attacker rule for free. It used to hang off Tutorial,
    # which put all 39 shopsanity checks in sphere 1 and made a shopsanity seed
    # open five times as wide as the same seed without it.
    #
    # Connected after the stretch cut rather than before it, because that is
    # what creates the region.
    #
    # Affordability is still not modelled: currency accrues from play and from
    # Archipelago's own coin/gem items, so a purchase is a matter of grinding
    # rather than a logic gate.
    # egypt6 is where the game sets feature_store, and egypt6 is in Egypt's
    # " Early" stretch -- so the store button exists exactly when that stretch
    # is reachable, sun producer and all.
    regions["Ancient Egypt Early"].connect(regions[SHOP_REGION])

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

    # Victory event. It hangs off Tutorial rather than off any one world,
    # because winning is now "complete N worlds" and no single world is on
    # that path -- rules.py puts the count on this location's access rule, and
    # sets multiworld.completion_condition alongside the rest of the logic.
    # In Modern Day until 2026-08-23, which only worked while Modern Day was
    # the goal world.
    victory_loc = PvZ2Location(player, "Victory", None, tutorial)
    victory_loc.place_locked_item(
        PvZ2Item("Victory", ItemClassification.progression, None, player))
    tutorial.locations.append(victory_loc)

    for r in regions.values():
        multiworld.regions.append(r)
