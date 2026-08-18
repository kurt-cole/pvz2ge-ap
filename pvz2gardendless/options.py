"""
PvZ2 Gardendless — player-facing options.
"""

import dataclasses

from Options import (
    Choice, DefaultOnToggle, OptionSet, Range, Toggle, DeathLink,
    PerGameCommonOptions,
)

from .constants import SELECTABLE_WORLDS


class WorldCount(Range):
    """
    How many main worlds this seed uses, counting Ancient Egypt.

    Ancient Egypt is always one of them -- it is the only world playable with
    no items, so it is where the seed opens. Modern Day is not counted: it is
    the goal world and is always present, unlocked by the world-goal
    requirement rather than by being picked here.

    The remaining slots are filled at random from the worlds not already named
    in enabled_worlds. Set this to `random` to let the generator pick the
    number of worlds too.

    Locations in worlds that are left out are removed from the seed entirely,
    along with their World Key items, so those worlds stay locked for good.

    12 (the default) is every world, which is how this game has always
    generated.
    """
    display_name = "World Count"
    range_start  = 1
    range_end    = len(SELECTABLE_WORLDS)
    default      = len(SELECTABLE_WORLDS)


class EnabledWorlds(OptionSet):
    """
    Worlds this seed must include. Any world named here is always in.

    Leave it empty to have world_count pick every world at random. Name fewer
    worlds than world_count and the rest of the slots are filled at random;
    name more and every one of them is still included, since an explicit
    choice always wins over the count.

    Ancient Egypt is included whether or not it is listed. Modern Day is not a
    valid entry -- it is always present as the goal world.
    """
    display_name = "Enabled Worlds"
    valid_keys   = SELECTABLE_WORLDS
    default      = frozenset()


class GoalType(Choice):
    """
    Condition that must be met before Modern Day unlocks.

    world_trophies: Earn N world trophies (the mid-world milestone check in each world).
      Note: Kongfu Temple has no world trophy in the game data and is always excluded,
      so the effective maximum for this mode is 10.

    world_completions: Beat the final regular level of N worlds (e.g. egypt35).
      All 11 non-Modern-Day worlds are eligible; maximum is 11.

    world_keys: Check the world-key level of N worlds (e.g. egypt8). All 11
      non-Modern-Day worlds are eligible; maximum is 11. Which level that is
      differs per world -- hint the "World Key Levels" group to see them.
    """
    display_name = "Modern Day Goal Type"
    option_world_trophies    = 0
    option_world_completions = 1
    option_world_keys        = 2
    default = 2


class WorldsRequired(Range):
    """
    How many worlds must satisfy the goal condition before Modern Day unlocks.
    For world_trophies the effective cap is 10 (Kongfu Temple excluded).
    For world_completions and world_keys the cap is 11.

    Worlds left out by world_count / enabled_worlds take their goal location
    with them, so this is clamped down to what the seed can actually offer --
    asking for 4 world keys in a 3-world seed requires 3.
    """
    display_name = "Worlds Required for Modern Day"
    range_start  = 1
    range_end    = 11
    default      = 7


class SkipTutorial(Toggle):
    """
    Skip the forced tutorial sequence at game start.
    When enabled, the game begins directly on the world map and all
    tutorial location checks are sent automatically on connect.

    Also skips the tutorials that make you open a screen the first time it
    unlocks: the almanac, the zen garden and the store each normally point you
    at their button and then walk you through the screen once you are inside.

    Left alone on purpose, because each does something besides prompt you: the
    plant food tutorial, which hands you a peashooter, and the world map and
    world key introductions, which decide where you land and move the world
    chooser along.
    """
    display_name = "Skip Tutorial"


class ModernDayVictory(Choice):
    """
    Which Modern Day level ends the run, once Modern Day has been unlocked.

    Modern Day runs modern1-modern31, then the ten Zomboss fights, then
    modern35-modern44, so the Zomboss sits at roughly level 33.

    world_key:  clear the World Key level, modern16. Shortest.
    zomboss:    beat the Modern Day Zomboss, around level 33. Default, and
                what every earlier version of this world used.
    completion: clear modern44, the final Modern Day level. Longest.

    Independent of the goal type, which only decides how much of the rest of
    the game is needed before Modern Day opens at all.
    """
    display_name = "Modern Day Victory"
    option_world_key  = 0
    option_zomboss    = 1
    option_completion = 2
    default = 1


class IncludeSidePaths(Toggle):
    """
    Include the side paths -- the branch quests hanging off the world maps,
    plus the standalone ones reached from the world chooser (Sandbox, the Bank
    Theft levels, Epic Beghouled, FloawerPot, Reinforcemint and
    ShootingStarFruit).

    Off (the default) removes every side path location from the seed, exactly
    the way an unpicked world is removed. Nothing can be placed there and
    nothing routes through them, so they become free play with no checks.

    Each path is gated on the level that reveals it in game -- the Squash quest
    at Ancient Egypt 6, Aloe at Lost City 8, Goo Peashooter at Dark Ages 16 --
    read off the world maps, where a branch island is labelled "<N>-1". A path
    spanning two worlds is gated on the earlier half: the Appease quest's
    second half sits behind Frostbite Caves 25, and the quest is one region, so
    the whole thing waits on Ancient Egypt 29. Hot Date has no branch node of
    its own and waits on the Sweet Potato path instead, the same way the game
    chains it.

    Two things the game does that this still does not: a path's later levels
    sit behind clearing its own first level, and a gate lands on the stretch
    holding its level rather than on the level itself, so Appease-mint opens
    with the rest of Egypt's Mid2 rather than at 29 exactly.

    On adds 187 locations -- 718 instead of 531 with every world enabled.
    Sphere 1 stays at 9 either way. Side paths belonging to a world this seed
    left out are still dropped either way.

    A small seed can end up with fewer locations than there are plants. Nothing
    fails there -- the pool ships fewer of the plants that gate nothing, and
    every progression plant, world key and upgrade still goes in. Turning this
    on is the way to get the full plant list into a small seed.
    """
    display_name = "Include Side Paths"


class IncludeDangerRooms(Toggle):
    """
    Include the Danger Rooms -- the game's endless survival mode.

    37 locations: one to three per world, plus Big Wave Beach's eight themed
    minigame rooms.

    Off (the default) drops them from the seed the way an unpicked world is
    dropped. The rooms are still playable, they just hold no checks.

    They are off by default because a Danger Room is endless, scaling survival
    content rather than a level with an end, so a check there is open-ended
    grind rather than progress. The levels that UNLOCK each room are ordinary
    numbered levels (egypt12, pirate4, beach20 and so on) and stay in the seed
    either way -- this only removes the rooms themselves.

    Each room is in logic only once the level that unlocks it is reachable,
    matching the game: a room's map node stays locked until you beat that
    level, whatever else you are carrying.
    """
    display_name = "Include Danger Rooms"


class Shopsanity(Toggle):
    """
    Turn the in-game store's one-time purchases into location checks.

    Adds 39 checks: 34 plants and 5 upgrades, all priced in gems. The gem,
    coin and sprout bundles are excluded because they can be bought
    repeatedly, and the four ticket-priced plants are excluded because
    tickets are pure grind with no Archipelago source.

    Note no store check is priced in coins, so coins only help indirectly,
    by buying gem bundles.

    Buying a plant still will not grant it -- plants only come from
    Archipelago -- so a purchase spends the currency and sends the check.

    The store itself does not exist until you clear Egypt level 6, which is the
    game's own rule, so logic puts these checks behind Ancient Egypt's sun
    producer gate rather than in the opening.
    """
    display_name = "Shopsanity"


class ShuffleUpgrades(DefaultOnToggle):
    """
    Shuffle the fourteen permanent upgrades into the item pool.

    These are the ones that raise your starting sun, plant food capacity, seed
    slots, sun shovel rate and manual mowers, plus Wall-nut First Aid, Plant
    Food Refresh and Sky Shield.

    On, the game stops granting them when you clear the level or buy them --
    the check still fires, but the upgrade itself becomes an Archipelago item
    that can land in anyone's world, and it only takes effect once you receive
    it. Off, the levels and store hand them out as they always have and the
    items are not in the pool.

    Off also matches how seeds generated before this option existed behave.
    """
    display_name = "Shuffle Upgrades"


class RandomizeConveyorPlants(Toggle):
    """
    Randomize which plants come down the belt on conveyor levels.

    Each conveyor entry keeps the level's own drop weight and count, so the
    pacing of the level is unchanged -- only the plant itself is swapped.

    Swaps stay within a plant's own power band, so a belt keeps the shape the
    level was built around. A sun producer is replaced by another sun producer,
    a one-shot by another one-shot, and the replacement costs about what the
    original did (the game's sun cost, bucketed into four tiers). A plant with
    nothing comparable to trade for is left as the level had it.

    Conveyor levels already hand out plants regardless of what Archipelago has
    sent you, so this does not leak progression: you get the plant on the belt
    for that level only, and do not keep it.

    Bowling, power-tile and potion levels are left alone. Their belts deliver
    projectiles and tools rather than plants, and swapping those for plants
    would make the level unplayable.

    Plants the lawn cannot host are never dealt to it. Lily Pad and Tangle Kelp
    only appear where there is water, and Gold Leaf, which needs a gold tile, is
    never swapped in at all. A level that puts one of these on its own belt
    keeps it, so a water level does not lose the plant its water columns need.

    The roll is fixed per level, so retrying a level gives the same plants
    rather than rerolling until you like them.
    """
    display_name = "Randomize Conveyor Plants"


class ShuffleZombies(Toggle):
    """
    Shuffle which zombies each level sends at you.

    Swaps stay inside a tier, so a level keeps the difficulty it was built
    around. The tier is the game's own `WavePointCost` -- the price its wave
    generator pays to field that zombie -- so a 100-point Mummy is traded for
    another 100-point zombie, never for a Gargantuar. Gargantuars only become
    Gargantuars, and Zombosses are never touched, so every boss fight is the
    one the level intended.

    Zombies that need a specific plant to answer them stay put: the Jester
    still only appears where a Jester appeared, and ice-block carriers only
    where ice-block carriers did. That is what keeps Dark Ages' Jester
    requirement and Frostbite Caves' warmth requirement honest -- the shuffle
    cannot move a threat into a world with no answer for it, nor take one out
    of a world whose access rule is built on it. Nothing about generation
    logic changes when this is on.

    Water zombies and land zombies are kept apart, since a land zombie
    dropped in a deep-water lane drowns.

    Levels built around particular zombies are skipped entirely -- the camel
    matching games, the cannon levels, Beghouled, bowling, Last Stand and the
    other set pieces. Those levels win on their specific zombies rather than
    just spawning them, so swapping there can leave one unbeatable. That is 84
    of the game's 1134 levels; the rest all shuffle.

    The roll is fixed per level, so retrying a level gives the same zombies
    rather than rerolling until you like them. Rolls differ between slots on
    the same seed.

    Off matches how seeds generated before this option existed behave.
    """
    display_name = "Shuffle Zombies"

class EarlyWorldKeys(Toggle):
    """
    Keep World Keys out of the later stretches of every world, so all of them
    can be found in the front half of the run.

    Without this a key can be placed deep inside another world -- behind that
    world's own key AND the plant count its middle stretch wants -- so the
    chain to the last key runs long. A seed generated this way put the Pirate
    Seas key inside Jurassic Marsh's middle stretch, which needed the Jurassic
    Marsh key and a stack of plants first.

    With it on, keys may only land in a world's opening stretch, the tutorial,
    the store, or a side path if include_side_paths kept them. Opening a world needs only its
    key (the plant-count gates are on the middle and late stretches), so keys
    chain through world openings and stay shallow.

    This does not make the run shorter. Every world still has to be played
    through; the keys just stop hiding behind each other's endgames.

    Off matches how seeds generated before this option existed behave.
    """
    display_name = "Early World Keys"


class TrapPercentage(Range):
    """
    Percentage of the filler item pool (coins and gems) to replace with traps.

    Lawn Mower Trap sets off every lawn mower on the field at once. They roll
    out and are spent, leaving those lanes with no last line of defence for the
    rest of the level. Traps received outside a level are held and applied when
    the next level starts.

    Costume Shuffle Trap re-rolls which costume every dressed plant is wearing,
    including taking some back off.

    -500 Coins and -20 Gems take that much off your balance, which is about
    what one coin or gem filler item gives. They can never take you below zero:
    a trap larger than your balance empties it and the rest is forgiven, never
    held against money you earn later.

    0 disables traps entirely.
    """
    display_name = "Trap Percentage"
    range_start  = 0
    range_end    = 100
    default      = 5


@dataclasses.dataclass
class PvZ2Options(PerGameCommonOptions):
    world_count:      WorldCount
    enabled_worlds:   EnabledWorlds
    goal_type:        GoalType
    worlds_required:  WorldsRequired
    modern_day_victory: ModernDayVictory
    skip_tutorial:    SkipTutorial
    include_side_paths: IncludeSidePaths
    include_danger_rooms: IncludeDangerRooms
    shopsanity:       Shopsanity
    shuffle_upgrades: ShuffleUpgrades
    randomize_conveyor_plants: RandomizeConveyorPlants
    shuffle_zombies:  ShuffleZombies
    early_world_keys: EarlyWorldKeys
    trap_percentage:  TrapPercentage
    death_link:       DeathLink
