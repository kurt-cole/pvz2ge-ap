"""
PvZ2 Gardendless — access rules.

All logic is expressed through the worlds.generic.Rules rule-builder helpers
(set_rule / add_rule) rather than by assigning access_rule directly, so rules
compose predictably and stay consistent with the rest of Archipelago.
"""

from typing import TYPE_CHECKING

from worlds.generic.Rules import add_rule, forbid_items_for_player, set_rule

from .constants import (
    CHEAP_ATTACKER_PLANTS, EGYPT_STRETCH_PLANTS, KEYED_WORLDS, STRETCH_PLANTS,
    SUN_PRODUCER_PLANTS, WORLD_ENTRY_PLANTS, is_early_region,
)
from .locations import goal_locations_for

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
        # All three gates asking for exactly the same thing put Egypt's 44
        # levels in one sphere. The later two also want a plant count, so the
        # world opens up as the multiworld feeds it rather than all at once.
        # The first gate is deliberately left alone: Egypt is the only world
        # playable with no items, and tightening its opening would leave a
        # seed with nowhere to start.
        # Mid1 starts at egypt6, so has_sun_and_attacker above is what makes
        # "you are expected to have a sun producer by Egypt level 6" true in
        # logic. Together with the universal world rule below it is also one of
        # the only two exits from sphere 1, and both want a sun producer -- see
        # generate_early() for why that matters and what it replaced.
        need = EGYPT_STRETCH_PLANTS.get(checkpoint_name)
        if need:
            add_rule(multiworld.get_entrance(f"Enter {checkpoint_name}", player),
                     lambda state, n=need: state.has_group("Plants", player, n))

    # Keyed main worlds — accessible once their key is held. Worlds this seed
    # left out have no entrance to rule on (regions.py skips them) and no key
    # in the pool, so they stay locked with nothing behind them.
    for w in KEYED_WORLDS:
        if w == "Modern Day":
            continue  # handled separately, see below
        if w not in world.enabled_worlds:
            continue
        key_name = f"{w} Key"
        set_rule(multiworld.get_entrance(f"Enter {w}", player),
                 lambda state, k=key_name: state.has(k, player))

    # A few worlds need specific plants beyond their key. add_rule ANDs onto
    # the entrance's existing key requirement, which is equivalent to gating
    # every location inside the region individually but without the
    # per-location loop. Each world carries a LIST of requirements and needs
    # one plant from each, so a world can ask for more than one thing --
    # Dark Ages wants a sun producer (it is permanently night) and an answer
    # to the Jester, and those are separate asks, not alternatives.
    # The lists live in constants.WORLD_ENTRY_PLANTS so items.py can force
    # every one of them to progression -- see LOGIC_PLANTS.
    # Every world except Ancient Egypt needs a sun producer on top of whatever
    # else lets you in. No world is playable on falling sun alone -- the same
    # judgement Egypt's own checkpoints already made -- and holding a key was
    # letting a player walk into a world with no way to build an economy.
    #
    # This is also what makes the sun producer a STRUCTURAL guarantee rather
    # than a hope. Sphere 1 is egypt1-2, the tutorial, the shop and the
    # standalone side paths; every exit from it now runs through a sun producer
    # (Egypt's own gate at egypt3, or any world's entrance), so fill has to
    # place one in sphere 1 or the seed does not open at all. That is what the
    # old early_items request was reaching for and could not enforce.
    #
    # Ancient Egypt is excluded and has no named entrance to rule on anyway:
    # regions.py connects it to Tutorial unnamed, deliberately, because it is
    # the one world playable with no items and is what sphere 1 is made of.
    for world_name in sorted(world.enabled_worlds):
        if world_name == "Ancient Egypt":
            continue
        add_rule(multiworld.get_entrance(f"Enter {world_name}", player),
                 lambda state: state.has_any(SUN_PRODUCER_PLANTS, player))

    for world_name, requirements in WORLD_ENTRY_PLANTS.items():
        if world_name not in world.enabled_worlds:
            continue
        entrance = multiworld.get_entrance(f"Enter {world_name}", player)
        for group in requirements:
            add_rule(entrance, lambda state, p=group: state.has_any(p, player))

    # Sequential stretches inside each world (regions.py cuts them). Gated on
    # progression plants held, so a world key opens the start of a world and
    # the rest follows as the multiworld sends plants. Only entrances that
    # actually exist are ruled: regions.py skips worlds too small to cut and
    # skips Ancient Egypt, which is handled above.
    for w in sorted(world.enabled_worlds):
        for suffix, need in STRETCH_PLANTS.items():
            name = f"Enter {w}{suffix}"
            try:
                entrance = multiworld.get_entrance(name, player)
            except KeyError:
                continue
            set_rule(entrance, lambda state, n=need: state.has_group("Plants", player, n))

    # Keys out of the late stretches, when the option asks for it. This is an
    # item rule rather than an access rule: it does not change what any
    # location requires, only what fill is allowed to put there.
    #
    # Without it a key can sit behind another world's key AND that world's
    # mid-stretch plant count, so the chain to the last key runs long. Opening
    # a world costs only its key, so restricting keys to early regions makes
    # them chain through world openings and stay shallow.
    #
    # Every key name is forbidden, including this seed's disabled worlds and
    # Modern Day: neither is in the pool, so naming them costs nothing and the
    # set does not have to track which worlds the seed kept.
    if world.options.early_world_keys:
        key_names = {f"{w} Key" for w in KEYED_WORLDS}
        for region in multiworld.get_regions(player):
            if is_early_region(region.name):
                continue
            for location in region.locations:
                forbid_items_for_player(location, key_names, player)

    # Modern Day — unlocked once enough world goals (trophies / completions /
    # keys, per the goal_type option) are reachable.
    goal_locs = goal_locations_for(world.options.goal_type.value,
                                   world.enabled_regions)
    # Clamp: the goal list shrinks with the seed. world_trophies has only 10
    # eligible locations to begin with (Kongfu Temple has no trophy), and
    # world_count / enabled_worlds cut it down further, so the option's
    # nominal 1-11 range can ask for more goals than exist -- which would lock
    # Modern Day for good.
    req = min(world.options.worlds_required.value, len(goal_locs))

    # Resolve the goal Locations once, here, rather than by name inside the
    # rule. This rule is re-evaluated constantly during fill and sweeping, and
    # state.can_reach(name, "Location", player) pays a type dispatch plus a
    # name lookup on every goal on every call before it reaches the actual
    # reachability test. Location.can_reach() is what that resolves to anyway.
    goal_locations = [multiworld.get_location(name, player) for name in goal_locs]

    def modern_day_rule(state, n=req, locs=goal_locations):
        # Counts reachable goals, but stops as soon as the answer is settled:
        # once n are reachable the rest cannot change it, and once too few are
        # left to ever total n the answer is already no. The old version always
        # walked all 11.
        completed = 0
        left = len(locs)
        for loc in locs:
            if completed >= n:
                return True
            if completed + left < n:
                return False
            if loc.can_reach(state):
                completed += 1
            left -= 1
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
    # parent_region is the region the location was built into, so it is the
    # same region the old LOC_NAME_TO_DATA lookup produced -- read off the
    # objects already resolved above instead of going back through the tables.
    for loc in goal_locations:
        multiworld.register_indirect_condition(loc.parent_region, modern_day_entrance)

    multiworld.completion_condition[player] = lambda state: state.has("Victory", player)
