"""
PvZ2 Gardendless — player-facing options.
"""

import dataclasses

from Options import (
    Choice, DefaultOnToggle, OptionSet, Range, Toggle, DeathLink,
    PerGameCommonOptions, Visibility, OptionGroup,
)

from .constants import SELECTABLE_WORLDS


class WorldCount(Range):
    """
    How many worlds this seed uses. This is the whole number of worlds you
    get -- every world counts, Ancient Egypt and Modern Day included.

    Ancient Egypt is always one of them: it is the only world playable with no
    items, so it is where the seed opens. Set this to 1 and Ancient Egypt is
    the entire seed.

    This is a hard cap, not a target. Slots left over after enabled_worlds is
    honoured are filled at random from the worlds it did not name, and if it
    named more worlds than this number allows the extras are dropped at random.
    Ancient Egypt is never one of the ones dropped. Set this to `random` to let
    the generator pick the number of worlds too.

    Locations in worlds that are left out are removed from the seed entirely,
    along with their unlock items, so those worlds stay locked for good.

    Every world in the seed ships three Progressive <World> items: the first
    opens the world, the second and third its middle and last stretches. The
    game enforces them, so a level you have not unlocked cannot be started.
    Ancient Egypt needs none to enter and and only requires two to complete.
    """
    display_name = "World Count"
    range_start  = 1
    range_end    = len(SELECTABLE_WORLDS)
    default      = len(SELECTABLE_WORLDS)-2


class StartingPlants(Range):
    """
    How many plants you begin the run with.
    """
    display_name = "Starting Plants"
    range_start  = 1
    range_end    = 10
    default      = 1


class EnabledWorlds(OptionSet):
    """
    Worlds this seed must include. Any world named here is always in.

    Leave it empty to have world_count pick every world at random. Name fewer
    worlds than world_count and the rest of the slots are filled at random;
    name more and world_count still wins, so the extras are dropped at random
    and you get exactly that many worlds.

    The default names eleven, so lowering world_count is how you get a smaller
    seed -- there is no need to empty this list first.

    Kongfu Temple and Aerial Fortress are the two the default leaves out. To
    play one, name it here AND raise world_count to match, or the list is
    twelve worlds long against eleven slots and one of the twelve is dropped at
    random -- sometimes the very world you added. Raising world_count on its
    own works too: 12 gets one of the two at random and 13 gets both.

    Ancient Egypt is included whether or not it is listed. Kongfu Temple and Aerial Fortress are disabled by default, but CAN be enabled.
    """
    display_name = "Enabled Worlds"
    valid_keys   = SELECTABLE_WORLDS
    default      = list(set(SELECTABLE_WORLDS) - set(["Kongfu Temple", "Aerial Fortress"])) 


class GoalType(Choice):
    """
    What counts as completing a world.

    zomboss: beat that world's Zomboss -- the boss fight partway through it
      (egypt25, dark20, dino32). Kongfu Temple has no Zomboss level in the
      game data and can never satisfy this one, so a seed containing it has
      one fewer world available than it looks.

    completion: clear the world's final level (egypt35, kongfu48, modern44).
      The longest of the three.

    world_key: clear the world's World Key level (egypt8, dark10, modern16).
      Not the same stage in every world -- hint the "World Key Levels" group
      to see them. The shortest.

    Applies to every world in the seed, Modern Day included.

    The older names world_trophies, world_completions and world_keys still
    work and mean the same three things: what this world used to call a
    world trophy always was the Zomboss fight.
    """
    display_name = "Goal Type"
    option_world_key  = 0
    option_zomboss    = 1
    option_completion = 2

    # Kept so a yaml written for an earlier version still generates. Same
    # values, so a seed rolled from one of these is identical to before.
    alias_world_keys        = 0
    alias_world_trophies    = 1
    alias_world_completions = 2
    default = 0


class WorldsRequired(Range):
    """
    How many worlds must be completed, in the sense the Goal Type picks,
    before the run is won.

    Every world in the seed counts, Modern Day included, so the ceiling is 12
    -- or 11 for the zomboss goal, since Kongfu Temple has no Zomboss level.

    Worlds left out by world_count / enabled_worlds take their goal location
    with them, so this is clamped down to what the seed can actually offer --
    asking for 4 world keys in a 3-world seed requires 3.
    """
    display_name = "Worlds Required"
    range_start  = 1
    range_end    = 12
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
    Deprecated and ignored. The run no longer ends on one specific Modern Day
    level: it ends when Worlds Required worlds have been completed, and Modern
    Day is an ordinary keyed world that counts like the rest.

    Its three choices live on as the Goal Type, where they now decide what
    completing ANY world means rather than just Modern Day.

    Still accepted so a yaml written for an earlier version generates without
    an error, and hidden from the option templates so nobody sets it fresh.
    """
    display_name = "Modern Day Victory (deprecated)"
    option_world_key  = 0
    option_zomboss    = 1
    option_completion = 2
    default = 1
    visibility = Visibility.none


class IncludeSidePaths(Toggle):
    """
    Include the side paths -- the branch quests hanging off the world maps,
    plus the standalone ones reached from the world chooser (Sandbox, the Bank
    Theft levels, Epic Beghouled, FloawerPot, Reinforcemint and
    ShootingStarFruit).

    Off (the default) removes every side path location from the seed, exactly
    the way an unpicked world is removed. Nothing can be placed there and
    nothing routes through them, so they become free play with no checks.
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

    Adds up to 34 checks: 29 plants and 5 upgrades, all priced in gems. The gem,
    coin and sprout bundles are excluded because they can be bought
    repeatedly, and the ticket-priced plants are excluded because tickets are
    pure grind with no Archipelago source.
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
    Keep the world unlocks out of the later stretches of every world, so all of
    them can be found in the front half of the run.

    Without this an unlock can be placed deep inside another world -- behind
    that world's own unlocks AND the plant count its middle stretch wants -- so
    the chain to the last one runs long. A seed generated this way put the
    Pirate Seas key inside Jurassic Marsh's middle stretch, which needed the
    Jurassic Marsh key and a stack of plants first.

    With it on, unlocks may only land in a world's opening stretch, the
    tutorial, the store, or a side path if include_side_paths kept them.
    Opening a world needs only its first unlock, so they chain through world
    openings and stay shallow.

    All three copies are held to this, not just the first: the second and third
    are what open a world's later stretches, so burying one is the same problem.

    This does not make the run shorter. Every world still has to be played
    through; the unlocks just stop hiding behind each other's endgames.

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


class TrapWeight(Range):
    """Base class for the per-trap weights. Not an option itself."""
    range_start = 0
    range_end   = 100
    default     = 25


class TrapWeightLawnMower(TrapWeight):
    """
    Relative weight of Lawn Mower Trap among the traps.

    Sets off every lawn mower on the field at once. They roll out and are
    spent, leaving those lanes with no last line of defence for the rest of the
    level. One received outside a level is held and applied when the next level
    starts.

    Weights are relative, not percentages: what matters is each one against the
    others, so 50/50/50/50 and 25/25/25/25 both mean an even mix. The four
    default to 25 apiece, which is the even mix this game shipped before the
    weights existed.

    0 keeps this trap out of the seed entirely. trap_percentage still decides
    how many traps there are in total; this only decides how that total is
    divided up. Set every weight to 0 and no traps are generated at all,
    whatever trap_percentage says.
    """
    display_name = "Trap Weight: Lawn Mower"


class TrapWeightCostumeShuffle(TrapWeight):
    """
    Relative weight of Costume Shuffle Trap among the traps.

    Re-rolls which costume every dressed plant is wearing, including taking
    some back off. The mildest of the four: it costs nothing but appearances.

    See Trap Weight: Lawn Mower for how the weights are read.
    """
    display_name = "Trap Weight: Costume Shuffle"


class TrapWeightCoins(TrapWeight):
    """
    Relative weight of -500 Coins among the traps.

    Takes 500 coins off your balance, about what one coin filler item gives. It
    can never take you below zero: a trap larger than your balance empties it
    and the rest is forgiven, never held against money you earn later.

    Coins buy gem bundles in the store and nothing else Archipelago tracks, so
    this bites hardest with shopsanity on.

    See Trap Weight: Lawn Mower for how the weights are read.
    """
    display_name = "Trap Weight: -500 Coins"


class TrapWeightGems(TrapWeight):
    """
    Relative weight of -20 Gems among the traps.

    Takes 20 gems off your balance, about what one gem filler item gives, and
    cannot push you below zero.

    Worth weighting down in a small seed with shopsanity on: gems cannot be
    earned in game under Archipelago at all, so every one you lose has to come
    back from the multiworld.

    See Trap Weight: Lawn Mower for how the weights are read.
    """
    display_name = "Trap Weight: -20 Gems"


@dataclasses.dataclass
class PvZ2Options(PerGameCommonOptions):
    world_count:      WorldCount
    enabled_worlds:   EnabledWorlds
    starting_plants:  StartingPlants
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
    trap_weight_lawn_mower:       TrapWeightLawnMower
    trap_weight_costume_shuffle:  TrapWeightCostumeShuffle
    trap_weight_coins:            TrapWeightCoins
    trap_weight_gems:             TrapWeightGems
    death_link:       DeathLink
OPTION_GROUPS = [
    OptionGroup("Goal Settings",[GoalType, WorldsRequired, EnabledWorlds]),
    OptionGroup("AP Settings", [DeathLink]),
    OptionGroup("Level Access",[WorldCount, IncludeSidePaths]),
    OptionGroup("Extra Locations",[Shopsanity]),
    OptionGroup("Traps",[TrapPercentage, TrapWeightLawnMower,
                         TrapWeightCostumeShuffle, TrapWeightCoins,
                         TrapWeightGems]),
    OptionGroup("Gameplay Tweaks",[SkipTutorial,ShuffleUpgrades, StartingPlants]),
    OptionGroup("Experimental DANGER",[RandomizeConveyorPlants, ShuffleZombies, IncludeDangerRooms, ModernDayVictory, EarlyWorldKeys])
]
