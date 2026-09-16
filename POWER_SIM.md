# Plant power: per-level loadout simulation

Status: in development (2026-09-16). Replaces the lawn-DPS power model in
`pvz2gardendless/plant_data.py` once it lands. This file is the design of record;
update it with the code.

## Why the old model is replaced

The lawn-DPS model priced a plant as `dps * min(12, 1000 // sun)` and a level as
`(roster HP / waves) / 25s`. It was wrong at both ends:

- Damage was read from whatever number a plant states, so reactive and utility
  effects counted as attacks: Buttercup (butter only when eaten) 1263 lawn DPS,
  Magnifying Grass 19820, Cran-Jelly 3600, Chomper 686. Contact and short-range
  plants counted as hitting the whole lane.
- Copies assumed 1000 sun on hand at once. No sun income, no recharge, no time.
- The level side averaged HP over all waves and the whole lawn: egypt2 needed
  35.8, which a lone Split Pea (224.6) "cleared" six times over. Playtest: egypt2
  with only Split Pea is not winnable.

## What a rule asks

A level is in logic when the player holds some **loadout** that passes that
level's simulation:

- one sun producer type, or none (sky sun only),
- a producer count: the best of 1-10 (`PRODUCERS_MAX`, two columns on a five-lane lawn),
- one attacker type,
- optionally one utility type (walls, slow, stun, knockback).

Two-attacker mixes are deliberately not modelled (damage is roughly linear in sun
spent, so a mix rarely beats its better half). Harder levels need more or better
producers, so additional sun producers enter logic as difficulty rises.

On top of the power rule, zombie counter rules (see Nullifiers) and the existing
hazard rules (Jester, ice blocks, flyers, dinos).

## The simulation (`pvz2gardendless/power_sim.py`)

Pure Python, deterministic: random ranges in game data use their expected value.
Every input comes from the level's own data and each plant's own props; nothing
uses a representative level or plant.

Per level:

- **Sun.** Starting sun (`StartingSun`, default 50). Sky sun from the level's own
  sun dropper module, resolved through `LevelModules` or the level itself:
  first drop at `InitialSunDropDelay`, then every
  `min(SunCountdownMax, SunCountdownBase + dropped * SunCountdownIncreasePerSun +
  SunCountdownRange / 2)` seconds, 50 sun each. No dropper, `SuppressSunSpawn`, or
  a `ListenToLawn` dropper at night means no sky sun.
- **Producers.** Planted first, `count` of them. Each produces its `SunValue` every
  `ProduceInterval + ProduceIntervalAdditional / 2` s after
  `ProduceCountdownStart + ProduceCountdownStartAdditional / 2`.
- **Purchases.** A packet is usable when its recharge (`Cooldown`, starting at
  `CooldownFrom`) is ready and sun covers `SunCost`. Order: producers, then
  attackers, then one utility per lane. Copies are BOUGHT on this schedule but
  PLANTED when a zombie calls for them (below). Per-lane cap
  `lane_cap = tiles - producer columns - 1`.
- **Waves.** Wave 1 at `ZombieCountdownFirstWaveSecs` (default 15). Next wave at
  the earlier of the timer (27.5 s, +10 after a flag wave) and the moment the
  current wave is down to its next-wave health threshold (mean of
  `Min/MaxNextWaveHealthPercentage`), but not before 4.5 s.
- **Lanes.** A zombie with a fixed row keeps it; others are dealt heaviest first
  to the lane holding the least HP in that wave, ties to the least cumulative HP.
- **Fights.** Per lane, zombies are killed front to back. A zombie walks at
  `WalkSPS` from the right edge; the lane fails when one reaches the front
  attacker. Walls in front add eat time (`Toughness / EatDPS`), slows and stuns
  stretch walk time, knockback adds distance. An attacker only damages a zombie
  inside its range (full lane, `AttackDistance`, or its own tile for contact
  plants). Instants spend a use (sun and a recharge shared across lanes) on the
  front zombie in range.
- **Reactive planting (`_Lawn`).** A lane plants the earliest bought, unplanted,
  unexpired copy when its current plants cannot kill the zombie before it
  arrives, up to the cap; a new copy changes its neighbours' rates (spread
  attackers). Chill and freeze are read from the copies alive halfway through
  the zombie's walk.
- **Backlog.** Each lane keeps a queue of (start, HP still to deal) across
  waves, replayed at the current rate, so a copy planted later also speeds up
  zombies already on the lawn. Sunburn plants pay per shot from the economy.

A level passes when no lane fails. Mowers and plant food are not modelled, on
purpose, as a safety margin.

## Plant behaviour (`tools/gen_sim_data.py` -> `pvz2gardendless/sim_data.py`)

Each plant gets a behaviour class with its numbers read from its own props, plus a
hand table for mechanics the props do not state, each entry with a reason:

| Class | Damage model | Examples |
| --- | --- | --- |
| shooter | per-hit damage / interval, full lane, targets per shot | Peashooter, Melon-Pult |
| short | as shooter, within N tiles | Bonk Choy, Bamboo Shoot |
| contact | damage to zombies crossing its tile | Spikeweed, Iceweed |
| burst | big periodic hit | Coconut Cannon, Banana Launcher |
| instant | per-use damage, sun + shared recharge | Potato Mine, Cherry Bomb |
| chomp | kills one zombie, then chews | Chomper |
| sunburn | shots paid in sun | Magnifying Grass |
| producer | sun income | Sunflower, Twin Sunflower |
| utility | wall / slow / stun / knockback | Wall-nut, Stunion |
| none | no attack and no modelled effect | Buttercup, Aloe |

## Nullifiers

Zombies that disable plants get counter rules wherever they spawn [user]:

| Zombies | Rule |
| --- | --- |
| torch: explorer, explorer_veteran, kongfu_torch, monk_torch, abbot_torch | an ice plant |
| wizard: dark_wizard(_veteran), sportzball_wizard, easter_wizard | an instant kill (Chomper counts) |
| gargantuars (SmashDamage) | an instant kill, or enough damage in the toughest-zombie check |
| eighties_boombox, eighties_skunk | an attacker out-ranging the effect, or enough damage with the stun downtime simulated |
| lostcity_excavator | a backwards shooter, or an instant whose recharge kills every excavator in the level |
| kongfu_bomb | something that kills it fast enough (an instant counts) |
| sky_drone, eighties_breakdancer | an instant kill |

[user] The roll never adds a nullifier to an opening level (tutorial1-5, egypt1-5)
unless the level ships it (`zombie_roll.OPENING_LEVELS`, mirrored in the client).
Tagged `noswallow` zombies only change which chomp plants count and are not
nullifiers.

## Offline table and generation

Exhaustive search is per level over every loadout, done once per game version by
`tools/gen_power_table.py` with multiprocessing (no numpy: Archipelago installs
cannot be assumed to have it). Exact pruning only:

- every producer count is tried, skipping a count that cannot beat what an
  earlier count reached;
- utilities are tried only where the attacker fails without one;
- a producer or utility matched or beaten on every stat by another is skipped.

For every level and loadout the table stores the **break-even HP multiplier**:
the largest scaling of the level's vanilla roster the loadout survives, found by
binary search between the easiest (750 per mille) and toughest (1333 per mille,
`LEVEL_HARD`) HP the budget roll can accept.

At generation no simulation runs by default:

- a loadout passes a level when the rolled level's HP ratio is at or below its
  break-even multiplier;
- the toughest-zombie check (the rolled roster's highest-HP zombie against the
  loadout's worst-lane damage before it crosses) and the nullifier rules are
  computed exactly for the rolled roster;
- optionally, loadouts within a narrow margin (about 5%) of their break-even are
  re-simulated against the rolled roster. Whether this stays depends on how many
  it touches per seed; measured before it is enabled.

Known approximation: the break-even multiplier treats a roll as a scaling of the
vanilla roster. A roll that trades many weak zombies for few strong ones is not a
scaling; the toughest-zombie check covers the dangerous direction.

Levels without a table row get no power rule: preset or conveyor seed banks
(`own_plants` false), bespoke levels and levels generated at runtime. 341 of 813
tracked levels have one.

The table reuses a per-level cache keyed by the simulator and data hash
(`build/power_cache/<fingerprint>`). A full run takes about 105 minutes on 12
workers; when only zombie HP changes, only the levels fielding those zombies
need re-simulating.

## Selection (`power_logic.select`)

[user] Naming every passing loadout made nearly every plant progression. At
generation the slot keeps a small set of plants instead:

- built levels are walked in play order (tutorial and Egypt first, then by
  depth along `level_predecessors`, same-depth ties drawn);
- per level, counter groups (nullifiers and the budget roll's hazard counters)
  and then loadouts are topped up until the level has
  `power_loadouts_per_level` distinct ways to pass (1 for the opening levels),
  counting a loadout that is a superset of another as the same way;
- a top-up takes the candidate adding the fewest new plants, then the one whose
  new plants help the most built levels, as a seeded pick among the best 3.

Every loadout rule, nullifier group and hazard group then names only selected or
granted plants, so only those are promoted. The old DPS ladder and per-budget
draws are no longer promoted when a selection exists. The selection is sent as
`logic_power_selection` so Universal Tracker builds the same rules; a seed
without it names every passing loadout, as before. Measured 2026-09-16: 21-27%
of pool plants progression at 2-3 loadouts per level.

## Calibration

Model only for now; recalibrated from playtest. Fixed verdicts become tests:

- egypt2 with only Split Pea (no producer) fails.

## Game facts used [data, pvzge_web checkout]

- Sun dropper defaults: `SunCD 2, SunCountdownBase 6, SunCountdownRange 3,
  SunCountdownIncreasePerSun 0.1, SunCountdownMax 12, Value 50`.
  `LevelModules` holds Reverted, VerySlow, Slow, Default, DefaultListenToLawn,
  Fast, VeryFast; levels can define their own.
- Waves: `NextWaveCountdown = 25 + rand*5 (+10 after flag wave)`; next wave also
  once `WaveLeftHealth / WaveToughness <= rand(Min, MaxNextWaveHealthPercentage)`
  after `WaveZombieDamageCountdown = 4 + rand`.
- Sunflower 50 sun, 23.5 + rand*1.5 s, first after 5 + rand*5.
- Mummy `WalkSPS 0.185`, `EatDPS 100`.
