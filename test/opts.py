"""The options object every offline suite generates against.

Lifted out of gen_test.py on 2026-08-26 so tracker_test.py could build seeds
too: importing gen_test to reach it would have run that whole suite as a side
effect, and a second hand-maintained copy would have drifted the moment an
option was added.

apstub must already be importable (both suites put test/ on sys.path first);
pvz2gardendless.options is imported through it.
"""
from pvz2gardendless.options import (
    WorldCount, EnabledWorlds, GoalType, WorldsRequired, ModernDayVictory,
    SkipTutorial, Shopsanity, TrapPercentage, ShuffleUpgrades,
    RandomizeConveyorPlants, EarlyWorldKeys, ShuffleZombies, IncludeSidePaths,
    IncludeDangerRooms, StartingPlants,
    TrapWeightLawnMower, TrapWeightCostumeShuffle, TrapWeightCoins,
    TrapWeightGems, IncludeLevelsPastGoal,
)
from apstub import DeathLink


class Opts:
    def __init__(self, **kw):
        self.world_count = WorldCount(kw.get("world_count", WorldCount.default))
        # Follow the option's own default rather than an empty set: with a
        # world_count below 13 an empty set makes every default seed pick its
        # worlds AT RANDOM, so a test naming one world's content fails
        # intermittently on whichever seeds left that world out.
        self.enabled_worlds = EnabledWorlds(
            frozenset(kw.get("enabled_worlds", EnabledWorlds.default)))
        self.starting_plants = StartingPlants(
            kw.get("starting_plants", StartingPlants.default))
        self.goal_type = GoalType(kw.get("goal_type", GoalType.default))
        self.worlds_required = WorldsRequired(kw.get("worlds_required", 7))
        self.modern_day_victory = ModernDayVictory(kw.get("modern_day_victory", 1))
        self.skip_tutorial = SkipTutorial(kw.get("skip_tutorial", 0))
        self.include_side_paths = IncludeSidePaths(
            kw.get("include_side_paths", IncludeSidePaths.default))
        self.include_danger_rooms = IncludeDangerRooms(
            kw.get("include_danger_rooms", IncludeDangerRooms.default))
        self.shopsanity = Shopsanity(kw.get("shopsanity", 0))
        self.shuffle_upgrades = ShuffleUpgrades(kw.get("shuffle_upgrades", ShuffleUpgrades.default))
        self.randomize_conveyor_plants = RandomizeConveyorPlants(
            kw.get("randomize_conveyor_plants", RandomizeConveyorPlants.default))
        self.shuffle_zombies = ShuffleZombies(kw.get("shuffle_zombies", 0))
        self.early_world_keys = EarlyWorldKeys(kw.get("early_world_keys", 0))
        self.include_levels_past_goal = IncludeLevelsPastGoal(
            kw.get("include_levels_past_goal",
                   IncludeLevelsPastGoal.default))
        self.trap_percentage = TrapPercentage(kw.get("trap_percentage", 5))
        for _tw, _cls in (("trap_weight_lawn_mower", TrapWeightLawnMower),
                          ("trap_weight_costume_shuffle", TrapWeightCostumeShuffle),
                          ("trap_weight_coins", TrapWeightCoins),
                          ("trap_weight_gems", TrapWeightGems)):
            setattr(self, _tw, _cls(kw.get(_tw, _cls.default)))
        self.death_link = DeathLink(0)
