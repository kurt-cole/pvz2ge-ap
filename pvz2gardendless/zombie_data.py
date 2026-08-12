"""
PvZ2 Gardendless -- zombie swap tiers for the shuffle_zombies option.

DERIVED FROM GAME DATA, not judgement. Every zombie the shipped levels can
actually spawn is bucketed by properties the game states outright, and a
shuffle only ever trades a zombie for another in its own bucket. Nothing here
is inferred from a name or a world.

The tier key is four game properties joined by "-":

  1. `WavePointCost` band. This is the game's OWN price for a zombie -- what
     its dynamic wave generator spends to field one -- so it is the game's
     answer to "how hard is this", not mine. Bucketed:
         t1 <= 150   t2 <= 350   t3 <= 650   t4 <= 1000   t5 > 1000
  2. land / water, from `LivesInDeepWater`. It means "survives deep water",
     so a water zombie is safe on either terrain and a land zombie is only
     safe on land. Keeping the two apart is what stops a swap from putting a
     zombie in a lane it drowns in.
  3. `garg`, from `ZombieSort == "Gargantuar"`. A Gargantuar only ever becomes
     another Gargantuar.
  4. A special-mechanic tag, for the handful of zombies that need a specific
     plant to answer them. These are partitioned so a mechanic can never move
     to a world that has no answer for it, and can never vanish from a world
     whose access rule is built on it:
         jester    `MoveSpeedMultiplierWhileJuggling` -- returns your own
                   projectiles. Answered by JESTER_COUNTER_PLANTS, which is
                   what gates Dark Ages.
         iceblock  `NumberOfIceblocksToSpawnWith` -- arrives carrying ice
                   blocks. Answered by FIRE_AURA_PLANTS, which gates
                   Frostbite Caves.
         air       `BalloonToughness` / `FlyDuration` / `FlyingSpeedScale` --
                   flies over ground plants. No counter list models this yet,
                   so it is pinned rather than gated.
         blocker   `PlantBlockers` / `ZombieBlockers` -- carries something
                   that specific plants alone can stop.

That last partition is the whole reason this option needs no new access rule.
Threat mechanics cannot be created or destroyed by a shuffle, so every world's
threat footprint after shuffling is exactly the one it had before, and the
plant requirements in WORLD_ENTRY_PLANTS stay exactly as true as they were.
Letting them roam instead would have put a Jester in nearly every world -- 3
jesters in an 82-member band, rolled across ~40 levels per world -- and forced
the Jester counter into almost every access rule, flattening the sphere
layering the rest of this world works to protect.

Two families are absent on purpose, so they can be neither swapped away nor
swapped in:

  Zomboss   `ZombieSort == "Zomboss"`. Every boss fight stays the fight the
            level was built around.
  camels    every type whose `ZombieBasedOn` contains "camel" -- all 25 of
            them, including the seasonal easter/feastivus/lunar sets. A camel
            is not a walker, it is a multi-segment chain driven by
            CamelMinigameProperties, and in the three levels that carry that
            module (egypt7, egypt16, egypt23) the camels ARE the game: you
            match them by hump count. Shuffling them left those levels with
            nothing to match and no way to win. Kurt found this in play
            testing, on egypt7.

That second one is the general shape to watch for: a zombie a level module
drives structurally, rather than one it merely spawns. Beghouled is the near
miss -- its match-3 pieces are PLANTS (BeghouledPresetProperties.InitialPlants),
so a zombie shuffle cannot touch it -- and the Kongfu bronze statues are
Gargantuar-sorted, so they only ever trade with each other.

Tiers with a single member simply never swap -- there is nothing comparable
to trade for -- which mirrors how randomize_conveyor_plants leaves a plant
alone when its group has no alternative.

To regenerate after a game update, read three tables out of the game source
(see the Base Game checkout, docs/assets/resources/):
    import/b9/b97ce2d2-*.json  ZombieTypes    -- codename -> Properties RTID
    import/e6/e67cb0cc-*.json  ZombieProps    -- the properties keyed above
    every level json with a LevelDefinition   -- RTID(x@ZombieTypes) refs,
                                                 which is what "can actually
                                                 spawn" means here
...then drop Zomboss sorts and anything whose ZombieBasedOn contains "camel".
281 zombies over 18 tiers as of the 0.8.x game data.
"""

from collections import Counter
from typing import Dict, List

ZOMBIE_TIERS: Dict[str, List[str]] = {
    't1-land': [
        'abbot', 'beach', 'beach_fem', 'beach_imp', 'birthday',
        'birthday_jetpack', 'chicken', 'chicken_pumpkin', 'cowboy', 'dark',
        'dark_imp', 'dark_imp_dragon', 'dino', 'dino_imp', 'easter_imp',
        'egypt_imp', 'eighties', 'eighties_imp', 'feastivus',
        'feastivus_flag', 'feastivus_imp', 'feastivus_poncho_no_plate',
        'feastivus_swashbuckler', 'foodfight', 'foodfight_flag', 'future',
        'future_flag', 'future_flag_veteran', 'future_imp',
        'future_infinut_shield', 'future_jetpack', 'future_jetpack_disco',
        'future_protector_shield', 'halloween', 'halloween_flag',
        'halloween_imp', 'holiday_imp', 'iceage', 'iceage_flag_veteran',
        'iceage_imp', 'kongfu', 'kongfu_rocket_imp', 'leprachaun_imp',
        'lostcity', 'lostcity_imp', 'lostcity_lostpilot', 'lunar', 'monk',
        'monk_blade', 'mummy', 'mummy_flag_veteran', 'pirate',
        'pirate_flag_veteran', 'pirate_imp', 'poncho_no_plate', 'ra', 'sky',
        'sky_dropship', 'sky_unarmed', 'sportzball', 'sportzball_imp',
        'stpatrick', 'stpatrick_imp', 'summer_imp', 'swashbuckler',
        'tutorial', 'tutorial_imp', 'west_bullrider', 'zoybean'
    ],  # 69
    't1-water': [
        'duckytube'
    ],  # 1
    't2-land': [
        'abbot_armor1', 'abbot_fan', 'abbot_torch', 'beach_armor1',
        'beach_fem_armor1', 'birthday_armor1', 'bobsled_team',
        'chicken_farmer', 'cowboy_armor1', 'dark_armor1', 'dino_armor1',
        'easter_poncho', 'eighties_armor1', 'eighties_boombox',
        'eighties_breakdancer', 'eighties_glitter', 'eighties_mc',
        'eighties_punk', 'explorer', 'feastivus_armor1', 'feastivus_poncho',
        'foodfight_armor1', 'foodfight_gobbler_king', 'future_armor1',
        'halloween_armor1', 'iceage_armor1', 'iceage_weaselhoarder',
        'kongfu_armor1', 'kongfu_chi', 'kongfu_gong', 'kongfu_hammer',
        'kongfu_torch', 'lostcity_armor1', 'lostcity_bug',
        'lostcity_excavator', 'lostcity_jane', 'lunar_armor1',
        'lunar_superfanimp', 'modern_superfanimp', 'monk_armor1',
        'monk_nunchaku', 'monk_torch', 'mummy_armor1', 'pelican',
        'pirate_armor1', 'poncho', 'prospector', 'seagull', 'sky_armor1',
        'sky_electric', 'sky_unarmed_armor1', 'sportzball_armor1',
        'stpatrick_armor1', 'summer_armor1', 'summer_bug', 'tomb_raiser',
        'tutorial_armor1', 'valentines_armor1', 'zoybean_armor1'
    ],  # 59
    't2-water': [
        'beach_snorkel', 'catapult', 'duckytube_armor1'
    ],  # 3
    't3-land': [
        'abbot_armor2', 'barrelroller', 'beach_armor2', 'beach_fem_armor2',
        'beach_fem_armor4', 'birthday_armor2', 'birthday_barrelroller',
        'birthday_pharaoh', 'cowboy_armor2', 'dark_armor2', 'dark_armor3',
        'dino_armor2', 'dino_armor3', 'dino_bully', 'easter_armor2',
        'easter_poncho_plate', 'eighties_arcade', 'eighties_armor2',
        'eighties_punk_veteran', 'feastivus_armor2', 'feastivus_piano',
        'feastivus_poncho_plate', 'foodfight_armor2', 'future_armor2',
        'future_jetpack_veteran', 'halloween_armor2', 'iceage_armor2',
        'iceage_armor3', 'iceage_dodo', 'iceage_hunter', 'kongfu_armor2',
        'kongfu_bomb', 'kongfu_drink', 'leprachaun_dodo', 'lostcity_armor2',
        'lostcity_bug_armor1', 'lostcity_bug_armor2',
        'lostcity_crystalskull', 'lostcity_impporter',
        'lostcity_relichunter', 'lunar_armor2', 'monk_armor2', 'monk_drink',
        'mummy_armor2', 'pharaoh', 'pharaoh_weak', 'piano', 'pirate_armor2',
        'pirate_captain', 'poncho_plate', 'sky_armor2',
        'sky_unarmed_armor2', 'sportzball_armor2', 'stpatrick_armor2',
        'stpatrick_dodo', 'summer_armor2', 'summer_bug_armor1',
        'summer_bug_armor2', 'tutorial_armor2', 'valentines_armor2',
        'west_bull', 'zoybean_armor2'
    ],  # 62
    't3-land-air': [
        'modern_balloon', 'monk_imp', 'sportzball_balloon'
    ],  # 3
    't3-land-blocker': [
        'abbot_3section_staff'
    ],  # 1
    't3-land-iceblock': [
        'birthday_troglobite', 'birthday_troglobite_1block',
        'birthday_troglobite_2block', 'iceage_troglobite',
        'iceage_troglobite_1block', 'iceage_troglobite_2block'
    ],  # 6
    't3-land-jester': [
        'birthday_juggler', 'dark_juggler', 'foodfight_chefster'
    ],  # 3
    't3-water': [
        'duckytube_armor2', 'future_protector', 'mech_cone', 'zomboni'
    ],  # 4
    't4-land': [
        'abbot_armor4', 'abbot_chi', 'beach_armor4', 'cannon',
        'cowboy_armor4', 'dark_armor4', 'dark_king', 'dark_king_veteran',
        'dark_wizard', 'dino_armor4', 'dino_bully_veteran', 'easter_wizard',
        'eighties_armor4', 'explorer_veteran', 'future_armor4',
        'iceage_armor4', 'iceage_hunter_veteran', 'lostcity_armor4',
        'lostcity_bug_armor4', 'modern_newspaper', 'monk_armor4',
        'monk_drink_veteran', 'mummy_armor4', 'pirate_armor4',
        'sky_battleplane', 'sportzball_wizard', 'tutorial_armor4',
        'valentines_armor4', 'west_bull_veteran',
        'west_bull_veteran_plantern_5'
    ],  # 30
    't4-land-blocker': [
        'beach_surfer'
    ],  # 1
    't4-land-iceblock': [
        'iceage_troglobite_veteran'
    ],  # 1
    't4-water': [
        'beach_fisherman', 'beach_octopus', 'disco_mech', 'football_mech',
        'future_protector_veteran'
    ],  # 5
    't5-land': [
        'dark_wizard_veteran', 'modern_allstar', 'newspaper_veteran',
        'sky_arbiterx', 'sky_twin'
    ],  # 5
    't5-land-blocker': [
        'beach_surfer_veteran'
    ],  # 1
    't5-water': [
        'sky_dronemaker'
    ],  # 1
    't5-water-garg': [
        'beach_gargantuar', 'birthday_gargantuar', 'cowboy_gargantuar',
        'dark_gargantuar', 'dino_gargantuar', 'easter_gargantuar',
        'easter_gargantuar_af', 'egypt_gargantuar', 'eighties_gargantuar',
        'feastivus_gargantuar', 'future_gargantuar', 'halloween_gargantuar',
        'holiday_gargantuar', 'iceage_gargantuar', 'kongfu_bronze_chi',
        'kongfu_bronze_chi_without_torch', 'kongfu_bronze_hook',
        'kongfu_bronze_strong', 'lostcity_gargantuar', 'pirate_gargantuar',
        'sky_gargantuar', 'sportzball_gargantuar', 'summer_gargantuar',
        'tutorial_gargantuar', 'valentines_gargantuar', 'zoybean_gargantuar'
    ],  # 26
}

# codename -> tier key. The client is sent ZOMBIE_TIERS and inverts it the same
# way; this side needs it to answer "may these two zombies trade places".
ZOMBIE_TIER_OF: Dict[str, str] = {
    zombie: tier for tier, zombies in ZOMBIE_TIERS.items() for zombie in zombies
}

# A zombie may not appear in two tiers -- the dict comprehension above would
# silently keep the last one, and the client's swap pool would disagree with
# this side's about which trade is legal.
_seen = Counter(z for zombies in ZOMBIE_TIERS.values() for z in zombies)
_dupes = sorted(z for z, n in _seen.items() if n > 1)
if _dupes:
    raise ValueError(f"zombies listed in more than one tier: {_dupes}")

# Tiers whose special-mechanic tag means the game needs a specific plant to
# answer them. Kept as a name list rather than folded into the tier keys so a
# test can assert the partition still holds after a data regeneration.
THREAT_TAGS = ("jester", "iceblock", "air", "blocker")


def tier_of(zombie: str) -> str:
    """Tier key for a zombie codename, or "" if it is not shuffled at all."""
    return ZOMBIE_TIER_OF.get(zombie, "")


def swap_pool(zombie: str) -> List[str]:
    """Zombies this one may be traded for, itself included.

    Empty for a zombie outside the table -- a Zomboss, a type no shipped level
    spawns, or one the game gives no WavePointCost -- which the caller reads as
    "leave this one exactly as the level had it".
    """
    tier = ZOMBIE_TIER_OF.get(zombie)
    return list(ZOMBIE_TIERS[tier]) if tier else []
