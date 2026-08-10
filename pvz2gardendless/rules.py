"""
PvZ2 Gardendless — access rules.

All logic is expressed through the worlds.generic.Rules rule-builder helpers
(set_rule / add_rule) rather than by assigning access_rule directly, so rules
compose predictably and stay consistent with the rest of Archipelago.
"""

from typing import TYPE_CHECKING

from worlds.generic.Rules import add_rule, set_rule

from .constants import CHEAP_ATTACKER_PLANTS, KEYED_WORLDS, SUN_PRODUCER_PLANTS
from .locations import LOC_NAME_TO_DATA, goal_locations_for

if TYPE_CHECKING:
    from . import PvZ2GardendlessWorld


def set_rules(world: "PvZ2GardendlessWorld") -> None:
    player = world.player
    multiworld = world.multiworld

    # Ancient Egypt checkpoints: each requires holding at least one sun
    # producer and one cheap attacker, mirroring what's actually needed to
    # survive further in.
    def has_sun_and_attacker(state):
        return (state.has_any(SUN_PRODUCER_PLANTS, player) and
                state.has_any(CHEAP_ATTACKER_PLANTS, player))

    for checkpoint_name in ("Ancient Egypt Mid1", "Ancient Egypt Mid2", "Ancient Egypt Late"):
        set_rule(multiworld.get_entrance(f"Enter {checkpoint_name}", player),
                 has_sun_and_attacker)

    # Keyed main worlds — accessible once their key is held.
    for w in KEYED_WORLDS:
        if w == "Modern Day":
            continue  # handled separately, see below
        key_name = f"{w} Key"
        set_rule(multiworld.get_entrance(f"Enter {w}", player),
                 lambda state, k=key_name: state.has(k, player))

    # A few worlds need a specific plant beyond their key. add_rule ANDs onto
    # the entrance's existing key requirement, which is equivalent to gating
    # every location inside the region individually but without the
    # per-location loop.
    add_rule(multiworld.get_entrance("Enter Big Wave Beach", player),
              lambda state: state.has("Lily Pad", player))
    add_rule(multiworld.get_entrance("Enter Frostbite Caves", player),
              lambda state: (state.has("Hot Potato", player) or
                             state.has("Pepper-pult", player) or
                             state.has("Fire Peashooter", player)))
    add_rule(multiworld.get_entrance("Enter Jurassic Marsh", player),
              lambda state: state.has("Perfume-shroom", player))

    # Modern Day — unlocked once enough world goals (trophies / completions /
    # keys, per the goal_type option) are reachable.
    goal_locs = goal_locations_for(world.options.goal_type.value)
    # Clamp: world_trophies has only 10 eligible locations (Kongfu Temple has
    # no trophy), so the option's nominal 1-11 range can request more goals
    # than are reachable, making Modern Day permanently locked.
    req = min(world.options.worlds_required.value, len(goal_locs))

    def modern_day_rule(state, n=req, locs=goal_locs):
        completed = sum(
            1 for loc_name in locs
            if state.can_reach(loc_name, "Location", player)
        )
        return completed >= n

    modern_day_entrance = multiworld.get_entrance("Enter Modern Day", player)
    set_rule(modern_day_entrance, modern_day_rule)

    # modern_day_rule calls state.can_reach() on locations in OTHER regions
    # (e.g. Pirate Seas' trophy) from an entrance rooted at Tutorial. AP's
    # sweep doesn't know "Enter Modern Day" structurally depends on those
    # regions, so each dependency must be registered via
    # register_indirect_condition -- otherwise the sweep can evaluate this
    # rule before a dependency region has been marked reachable in the same
    # pass (queue order for retried entrances is not guaranteed) and
    # incorrectly read it as still locked.
    for loc_name in goal_locs:
        dep_region = multiworld.get_region(LOC_NAME_TO_DATA[loc_name].region, player)
        multiworld.register_indirect_condition(dep_region, modern_day_entrance)

    multiworld.completion_condition[player] = lambda state: state.has("Victory", player)
