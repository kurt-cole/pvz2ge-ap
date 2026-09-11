# Zombie randomization: audit and plan

**Status: all five phases implemented.** What shipped differs from the plan below in one place --
two more threat tags (`shield`, `summon`) were added once the data showed enough members to be worth
partitioning. Final measured result, replayed over 1086 shufflable levels at five seeds
(`test/balance_test.py`): per-level HP p5 0.96, median 1.00, p95 1.06, worst 1.17x, with about 70% of
all spawns still changed.

Scope: the `shuffle_zombies` option end to end -- the tier table in
[zombie_data.py](pvz2gardendless/zombie_data.py), the `zombie_*` keys in `fill_slot_data`, and the
swap hook inside `TMPPATCH_CONTENT` in
[build_pvzge_ap.py](pvz2gardendless/build_pvzge_ap.py).

## What was wrong

The option worked mechanically -- RTID unwrapping, per-level stability, closed threat tiers, the
bespoke-module skip -- and the whole suite passed. The fault was in the premise.

**The tier key was `WavePointCost` band + terrain + Gargantuar + threat tag.** `WavePointCost` is the
price the *dynamic wave generator* pays to field a zombie. It is a budget price for a generator that
also re-prices what it fields, not a measure of how hard a zombie is to kill. Simulating the client's
exact RNG over the 1037 shufflable shipped levels, seed 987654321:

| per-level total, post/pre | p5 | median | p95 | max |
| --- | --- | --- | --- | --- |
| `WavePointCost` | 0.78 | 0.99 | 1.21 | 6.1 |
| effective HP (`Toughness` + `StartingArmors`) | 0.56 | 1.00 | 2.51 | 107 |

Cost parity was preserved exactly as designed. Difficulty parity was not: 86 levels at 2x or more
effective HP, 34 at 3x or more, 30 at half or less. The worst was `pirate1`, the *first* Pirate Seas
level, at 27x -- all 18 basic pirates became `future_infinut_shield`, a 10000 HP immobile shield,
because both are priced at 150 or under.

Levels that build their waves with a `WaveManagerModuleProperties` `ZombiePool` self-correct, because
the generator reads `prop.WavePointCost` *through* the hook and spends the swapped price. Levels with
hand-authored `SpawnZombiesJitteredWaveActionProps` waves have no budget, so they absorbed the whole
delta. That is where every spike landed.

**The tiers were also internally heterogeneous on everything except price.** `t1-land` held 69
zombies whose `Toughness` ranged from 1 (`chicken`) to 10000 and whose `WalkSPS` ranged from 0 to 2.
Four families had no business being in a generic pool at all:

- **Immobile props** (`WalkSPS == 0`): `future_infinut_shield`, `future_protector_shield`,
  `sky_dropship`. The dropship is 1200 HP, immune to nearly every plant interaction, and spawns imps
  forever -- priced at 100, so it traded with a basic zombie. 55 levels gained one.
- **Sky City ship-dependent** (`SkyCityShipDetectXOffset`): 11 types including `sky_arbiterx`,
  `sky_twin`, `sky_battleplane`. 211 levels gained one, in worlds with no airship for them to act on.
- **`IgnoredInWaves`**: 19 types the game deliberately never wave-spawns (imps and support that
  arrive from a carrier). 166 levels gained one.
- **Aerial**: the `air` tag was derived from `BalloonToughness` / `FlyDuration` /
  `FlyingSpeedScale`, which catches only the three balloon zombies. The properties that actually mark
  flight are `ChooseToSpawnOnNonDeckRows`, `BugToughness` (bug riders) and, in the
  `_ZOMBIEPROPERTIES` sheet, `IsSpawnedFlying`. 447 levels gained an aerial threat they had none of
  and 358 lost theirs.

That last one means the invariant claimed in the `zombie_data.py` docstring and the `ShuffleZombies`
option text -- "threat mechanics cannot be created or destroyed by a shuffle" -- was false for
flight. It does still hold for the two mechanics generation logic is actually built on (jester,
iceblock), so `rules.py` was never unsound. This is a fairness fault, not a logic one.

**One functional bug, unrelated to balance.** `_apZombieSwap` computes the bespoke-module verdict on
the first resolve of a level and caches it under `thisLevelsID`. But `thisLevelsID` is assigned when
the level data loads, while `currentLevelObjects` is filled in by the component afterwards -- so
during that window the object list still describes the *previous* level. A resolve landing in the
window caches the wrong verdict for the whole level, in both directions: an ordinary level entered
from `egypt7` silently stops shuffling, and `egypt7` entered from an ordinary level *is* shuffled,
which is exactly the unwinnable camel bug 1f05e0e fixed.

## The design

Three changes, in order of how much they matter.

### 1. Effective HP as a tier axis

The tier key gains a geometric HP band, and keeps everything it had:

```
t{cost}-{land|water}[-garg][-jester][-iceblock][-air][-blocker][-shield][-summon]-h{band}
band = floor(log(Toughness + sum(StartingArmors toughness)) / log(1.35))
```

1.35 is chosen empirically: it caps the intra-tier HP ratio at 1.33 while leaving 90% of the table
with somebody to trade with (88% once the two extra tags below are in). Coarser bands buy little
(1.75 reaches 92%), finer ones start stranding zombies alone in a tier.

### 2. Exclusions

Immobile, `IgnoredInWaves` and Sky City ship-dependent types leave the table entirely, joining
Zomboss and the camels. Untiered already means "leave exactly as the level authored it", so a level
that ships a `sky_dropship` still gets its dropship -- no other level can gain one. As shipped against game
0.14.0, 62 codenames are excluded (20 `IgnoredInWaves`, 18 camel, 14 Sky City, 9 unpriced
placeholders, 1 immobile) and 262 are tiered.

The `air` tag is re-derived from `ChooseToSpawnOnNonDeckRows` / `BalloonToughness` / `BugToughness`,
which makes the "threat mechanics are conserved" claim true as stated rather than true for two
mechanics out of four.

Two tags were added that the audit had not called for, because the data showed enough members to be
worth conserving: `shield` (`ShieldToughness` / `ProjectileAbsorbingFactor`, 8 zombies -- a straight
shooter stops being an answer) and `summon` (`ZombiesToSummon` and friends -- fields zombies of its
own, which the level's wave budget never accounted for). `NumberOfArcadeCabinetsToSpawnWith` folds
into `blocker`. The cost is 3 points of swappability: 88% of the table still has somebody to trade
with, down from 91%.

### 3. A per-level plan, in the client

The hook stops rolling one codename at a time and builds a plan for the level once, which buys three
things a lazy per-codename roll cannot have:

- **A budget guard.** Sum the level's roster HP before and after; if the ratio leaves 0.85-1.15,
  re-roll with a salted key, up to 6 attempts, keeping the closest attempt. If even that leaves
  0.6-1.6, fall back to the identity map. Deterministic, so a retry is still not a reroll. Requires
  a new `zombie_hp` slot_data key (codename -> effective HP), absent on older seeds, which reads as
  "no guard" and so behaves exactly as today.
- **Injectivity.** Distinct source codenames prefer distinct replacements, so a level does not
  collapse three zombie types onto one (`dark10` did). Linear probe forward through the tier.
- **A correct bespoke verdict.** The plan is keyed on the level's object list, not just
  `thisLevelsID`, so a stale list from the previous level cannot pin the wrong answer.

Anything the plan does not name -- a lawn placeholder resolving mid-level, a dynamic pool pick --
still resolves through the old lazy path, with the same key format at attempt 0, so those rolls are
unchanged.

Measured over 1086 shufflable levels with all three in place, at five seeds: HP ratio p5 0.96, median
1.00, p95 1.06, worst 1.17x, nothing anywhere near 1.5x -- while about 70% of all spawns still change.
The option gets to keep being a shuffle. `pirate1`, the 27x level, now sits at 1.04x.

### Deliberately not done

**Progression-bounded swap radius** (don't let early Egypt field endgame units). The HP axis already
prevents the power jump that made this worth wanting, and the flavour version of it needs the client
to model world order and interacts badly with `include_levels_past_goal` trimming. Revisit only if
playtesting says a balanced-but-wrong-world roster still reads as unfair.

## Phases

All implemented. Each landed with the tests named in phase 4 passing; the whole suite is 19 green.

- **Phase 1 -- data.** `tools/gen_zombie_tiers.py` reads `ZombieTypes`, `ZombieProps` and
  `ArmorProps` out of a game checkout and writes `zombie_data.py` (tiers, `ZOMBIE_HP`, exclusion
  lists) plus `test/data/zombie_balance.json`, the offline extract the balance test replays. Replaces
  the "read three tables by hand" comment the table was previously maintained by.
- **Phase 2 -- world.** `fill_slot_data` sends `zombie_hp` alongside `zombie_tiers`, absent when the
  option is off, tolerated as absent by any client.
- **Phase 3 -- client.** The level plan: object-list-keyed bespoke verdict, roster scan, injective
  assignment, budget guard. Copied into `test/client/zombie_fn.js` for `drift_test.py`.
- **Phase 4 -- tests.** `test/zombie_tier_test.py` asserts the tier partition holds (no tier mixes
  aerial with ground, immobile with mobile, `IgnoredInWaves` with normal, and no intra-tier HP ratio
  above 1.4). `test/balance_test.py` replays the client's exact RNG over the extract and fails if the
  p95 or the worst level leaves its band -- the test that would have caught `pirate1`. New cases in
  `zombie_test.js` for the plan, the guard and the stale object list.
- **Phase 5 -- docs.** The `ShuffleZombies` option text, the `zombie_data.py` header, and a DEV.md
  pointer here.

## Regenerating after a game update

```
python tools/gen_zombie_tiers.py --game-root ~/pvzge_ap_build/PVZGE-Electron
python test/run.py
```

The generator rewrites `pvz2gardendless/zombie_data.py` and `test/data/zombie_balance.json` together,
so the table and the extract the balance test replays can never describe different data. Both are
committed; neither generation nor the test suite ever reads a game checkout.

If `zombie_tier_test.py` fails afterwards, the game data changed in a way that broke a partition --
a threat that stopped being tagged, a tier that outgrew its HP band, an excluded family that came
back. That is a fact about the new build worth understanding before the assertion is touched. If
`balance_test.py` fails, some level got meaningfully harder or easier than it ships; the bands in
that file are the promise the option makes, so re-earn them rather than widening them.
