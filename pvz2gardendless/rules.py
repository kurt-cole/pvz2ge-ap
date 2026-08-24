"""
PvZ2 Gardendless — access rules.

All logic is expressed through the worlds.generic.Rules rule-builder helpers
(set_rule / add_rule) rather than by assigning access_rule directly, so rules
compose predictably and stay consistent with the rest of Archipelago.
"""

from typing import TYPE_CHECKING

from worlds.generic.Rules import add_rule, forbid_items_for_player, set_rule

from .constants import (
    CHEAP_ATTACKER_PLANTS, DANGER_ROOM_UNLOCK, EGYPT_STRETCH_PLANTS,
    KEYED_WORLDS, SIDE_PATH_REGIONS, STRETCH_PLANTS, SUN_PRODUCER_PLANTS,
    WORLD_ENTRY_PLANTS, WORLD_REGIONS, is_early_region, progressive_item_name,
    progressive_need, stretch_suffixes,
)
from .locations import SHOP_LOC_UNLOCK, goal_locations_for

if TYPE_CHECKING:
    from . import PvZ2GardendlessWorld


def set_rules(world: "PvZ2GardendlessWorld") -> None:
    player = world.player
    multiworld = world.multiworld

    # "By Egypt level 6 you are expected to have a sun producing plant",
    # expressed as a rule -- and the reason a sun producer is guaranteed to be
    # findable at the start of a run rather than merely likely. egypt1-5 are
    # what sphere 1 is made of; every way out of it wants a sun producer, and
    # for Egypt itself that way out is egypt6.
    #
    # It applies to all three of Egypt's later stretches, not only the first:
    # a rule that stopped applying deeper in would let a player who lost their
    # sun producer walk into egypt26.
    #
    # Egypt has no key, so without this its stretches would be gated on the
    # progressive unlock alone. The other worlds' entrances carry the same
    # requirement (below); between them, nothing in any seed opens without a
    # sun producer.
    def has_sun_and_attacker(state):
        return (state.has_any(SUN_PRODUCER_PLANTS, player) and
                state.has_any(CHEAP_ATTACKER_PLANTS, player))

    for suffix, need in EGYPT_STRETCH_PLANTS.items():
        name = f"Enter Ancient Egypt{suffix}"
        try:
            entrance = multiworld.get_entrance(name, player)
        except KeyError:
            continue  # Egypt too small to cut, which no real seed produces
        set_rule(entrance, has_sun_and_attacker)
        # " Early" (egypt6-8) asks for the sun producer and nothing else: it is
        # still the opening, and a plant count there would gate the levels a
        # seed opens with.
        if need:
            add_rule(entrance,
                     lambda state, n=need: state.has_group("Plants", player, n))

    # Keyed main worlds — accessible once the FIRST of that world's progressive
    # unlocks is held. That item replaced the world's Key on 2026-08-23; the
    # rule below is the same shape the key rule was, and the second and third
    # copies open the world's later stretches further down.
    #
    # Worlds this seed left out have no entrance to rule on (regions.py skips
    # them) and no unlocks in the pool, so they stay shut with nothing behind
    # them.
    for w in KEYED_WORLDS:
        if w not in world.enabled_worlds:
            continue
        set_rule(multiworld.get_entrance(f"Enter {w}", player),
                 lambda state, i=progressive_item_name(w),
                 n=progressive_need(w, ""): state.has(i, player, n))

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
            # Ancient Egypt's two stretches are ruled above instead: it wants a
            # sun producer and an attacker rather than a plant count, and
            # add_rule below would AND this on top of that.
            if w != "Ancient Egypt":
                set_rule(entrance,
                         lambda state, n=need: state.has_group("Plants", player, n))

    # ...and every stretch, in every world, needs that world's progressive
    # unlock: one copy for the middle stretch, two for the last. This is the
    # gate the CLIENT enforces as well (see slot_data's world_gates and the
    # goToLevel hook) -- unlike the plant counts, which are logic only, a
    # player really cannot start Ancient Egypt 9 without the first of these.
    #
    # add_rule, so it stacks with the plant requirements rather than replacing
    # them: a stretch wants both.
    for w in sorted(world.enabled_worlds):
        item_name = progressive_item_name(w)
        for suffix in stretch_suffixes(w)[1:]:
            count = progressive_need(w, suffix)
            if not count:
                continue  # Ancient Egypt's " Early": a checkpoint, not a stretch
            try:
                entrance = multiworld.get_entrance(f"Enter {w}{suffix}", player)
            except KeyError:
                continue
            add_rule(entrance,
                     lambda state, i=item_name, n=count: state.has(i, player, n))

    # Danger Rooms — playable only once the level that unlocks the room has
    # been beaten. In the game a room's map node reads its own level progress,
    # which starts at locked and is raised by exactly one thing: finishing the
    # level whose FirstRewardParam names that room's trophy (see
    # DANGER_ROOM_UNLOCK for the derivation). "Beat that level" is "reach that
    # location" here, so the rule is the unlock location's own reachability.
    #
    # The rooms sit in whatever stretch of their world their position in
    # locations.py put them, which for most of them is already at or past the
    # unlock level and makes this a no-op. It bites on the five rooms that lead
    # their world's location list -- iceage/lostcity/kongfu/eighties/dino
    # _dangerroom -- which landed in their world's OPENING stretch while the
    # game does not unlock them until level 14-20. Those were reachable in
    # logic from the moment the world's key turned up, so fill could bury a
    # world key or a gated plant in a room the player cannot enter yet.
    #
    # Resolved to Location objects once, as with the Modern Day goals below:
    # this is evaluated on every sweep and Location.can_reach is what a
    # by-name lookup ends up calling anyway. No register_indirect_condition is
    # needed -- that is for entrances, and these are location rules, so nothing
    # about which REGIONS are reachable depends on them.
    danger_rooms = []
    for room_name, unlock_name in DANGER_ROOM_UNLOCK.items():
        try:
            room = multiworld.get_location(room_name, player)
        except KeyError:
            continue  # include_danger_rooms off, or this world is not in the seed
        # The unlock level is an ordinary level in the same world as its room,
        # so if the room was built this cannot miss. Left to raise if it ever
        # does: a silently ungated room looks exactly like a working one.
        unlock = multiworld.get_location(unlock_name, player)
        add_rule(room, lambda state, u=unlock: u.can_reach(state))
        danger_rooms.append(room)

    # Shop checks wait for the card to reach the shelf. The Shop region only
    # models the store BUTTON, which the game grows once egypt6 is cleared;
    # the shelf itself fills in over the whole run, because readCommodity
    # destroys a card whose UnlockLevel is not cleared yet:
    #
    #   getPlantProgressByID(id).progress > 0 ||
    #   (UnlockLevel && getLevelProgressByID(UnlockLevel).progress < 3)
    #
    # So 29 of the 39 checks were in logic from Egypt 6 while the game does not
    # put them on sale until Modern Day 14, Aerial Fortress 31, Kongfu 38 and so
    # on -- fill could bury a key behind a purchase that cannot be made for
    # another ten worlds. Same rule shape as the Danger Rooms above, and the
    # same reason no indirect condition is needed: it is a location rule, so no
    # region's reachability turns on it.
    #
    # The other ten cards carry no UnlockLevel and stay on the Shop region's
    # own gate. Cards whose world this seed left out are not built at all --
    # active_locations drops them, since nothing could ever clear their level.
    shop_gated = []
    for loc_name, unlock_name in SHOP_LOC_UNLOCK.items():
        try:
            shop_loc = multiworld.get_location(loc_name, player)
        except KeyError:
            continue  # shopsanity off, or this card's world is not in the seed
        # active_locations only keeps the card when its unlock level's world is
        # in the seed, so this cannot miss. Left to raise if it ever does: an
        # ungated card looks exactly like a working one.
        unlock = multiworld.get_location(unlock_name, player)
        add_rule(shop_loc, lambda state, u=unlock: u.can_reach(state))
        shop_gated.append(shop_loc)

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
        # The unlocks are the keys now, and all three copies are held to the
        # same rule: the second and third are what open a world's later
        # stretches, so burying one behind another world's endgame is the same
        # problem the option was written for.
        key_names = {progressive_item_name(w) for w in WORLD_REGIONS}

        # A side path is named neither " Mid" nor " Late", so is_early_region
        # reads every one of them as early. That was true when they all hung
        # off their world's opening; regions.py now hangs each one off the
        # stretch holding the level that reveals it, so Ice Bloom sits behind
        # Big Wave Beach 40 while still answering "early" by name. Resolve a
        # side path to whatever it actually hangs off and judge that instead,
        # following the chain for Hot Date, which hangs off another side path.
        side_paths = set(SIDE_PATH_REGIONS)

        def effective_region(name: str) -> str:
            seen = set()
            while name in side_paths and name not in seen:
                seen.add(name)
                try:
                    name = multiworld.get_entrance(f"Enter {name}",
                                                   player).parent_region.name
                except KeyError:
                    break  # not built in this seed
            return name

        for region in multiworld.get_regions(player):
            if is_early_region(effective_region(region.name)):
                continue
            for location in region.locations:
                forbid_items_for_player(location, key_names, player)
        # A Danger Room in a world's opening stretch is in an "early" region by
        # name but is not an early CHECK any more: the rule above puts it behind
        # a level 14-20 unlock. Leaving those open would let a key hide there
        # and quietly undo what this option is for.
        for room in danger_rooms:
            forbid_items_for_player(room, key_names, player)
        # Same for a shop card that is not on sale yet: "Shop" is an early
        # region by name, but a card gated on modern31 or sky31 is one of the
        # last checks in the seed.
        for shop_loc in shop_gated:
            forbid_items_for_player(shop_loc, key_names, player)

    # The win condition — complete worlds_required worlds, in whichever sense
    # goal_type picks (that world's Zomboss, its final level, or its World Key
    # level). Modern Day is one of them now; it used to be the goal world, and
    # this same count used to be what unlocked it.
    goal_locs = goal_locations_for(world.options.goal_type.value,
                                   world.enabled_regions)
    # Clamp: the goal list shrinks with the seed. The zomboss goal has only 11
    # eligible locations to begin with (Kongfu Temple has no Zomboss level),
    # and world_count / enabled_worlds cut it down further, so the option's
    # nominal 1-12 range can ask for more goals than exist -- which would make
    # the seed unwinnable.
    req = min(world.options.worlds_required.value, len(goal_locs))

    # Resolve the goal Locations once, here, rather than by name inside the
    # rule. This rule is re-evaluated constantly during fill and sweeping, and
    # state.can_reach(name, "Location", player) pays a type dispatch plus a
    # name lookup on every goal on every call before it reaches the actual
    # reachability test. Location.can_reach() is what that resolves to anyway.
    goal_locations = [multiworld.get_location(name, player) for name in goal_locs]

    def goal_rule(state, n=req, locs=goal_locations):
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

    # On the Victory event rather than on an entrance, so no region has to be
    # invented to hold the win. A location rule needs no
    # register_indirect_condition: the advancement sweep re-runs until it
    # stops collecting, so a rule that depends on other regions is picked up
    # on a later pass. An ENTRANCE rule is what needs the hint, which is why
    # the Modern Day version of this had a register_indirect_condition loop.
    set_rule(multiworld.get_location("Victory", player), goal_rule)

    multiworld.completion_condition[player] = lambda state: state.has("Victory", player)
