"""
PvZ2 Gardendless — player-facing options.
"""

import dataclasses

from Options import Choice, Range, Toggle, DeathLink, PerGameCommonOptions


class GoalType(Choice):
    """
    Condition that must be met before Modern Day unlocks.

    world_trophies: Earn N world trophies (the mid-world milestone check in each world).
      Note: Kongfu Temple has no world trophy in the game data and is always excluded,
      so the effective maximum for this mode is 10.

    world_completions: Beat the final regular level of N worlds (e.g. egypt35).
      All 11 non-Modern-Day worlds are eligible; maximum is 11.

    world_keys: Check the "World Key - X" location in N worlds. All 11
      non-Modern-Day worlds are eligible; maximum is 11.
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
    """
    display_name = "Shopsanity"


class TrapPercentage(Range):
    """
    Percentage of the filler item pool (coins and gems) to replace with traps.

    Lawn Mower Trap sets off every lawn mower on the field at once. They roll
    out and are spent, leaving those lanes with no last line of defence for the
    rest of the level. Traps received outside a level are held and applied when
    the next level starts.

    0 disables traps entirely.
    """
    display_name = "Trap Percentage"
    range_start  = 0
    range_end    = 100
    default      = 5


@dataclasses.dataclass
class PvZ2Options(PerGameCommonOptions):
    goal_type:        GoalType
    worlds_required:  WorldsRequired
    modern_day_victory: ModernDayVictory
    skip_tutorial:    SkipTutorial
    shopsanity:       Shopsanity
    trap_percentage:  TrapPercentage
    death_link:       DeathLink
