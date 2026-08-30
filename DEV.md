## Development notes

### Open: adopt the AutoWorld and Region helper APIs — @kurt-cole to address

The world still builds its region graph and reaches for its own objects the long way round, using
patterns that predate the helpers Archipelago now provides. Nothing here is broken, but it is more
code than the current API needs and it drifts further from upstream conventions with each release.

Two related changes:

**1. Use the `World.get_*` helpers instead of the `multiworld.get_*` pair.** Throughout
`rules.py` the world reaches for its own objects by passing its player number back to the
multiworld:

```python
multiworld.get_entrance(f"Enter {world_name}", player)
multiworld.get_region(LOC_NAME_TO_DATA[loc_name].region, player)
```

`AutoWorld.World` exposes `self.get_entrance(name)`, `self.get_region(name)`,
`self.get_location(name)`, and the plural `get_entrances()` / `get_regions()` / `get_locations()`,
all of which scope to the calling world automatically. Since `set_rules()` already receives the
world object, every one of these call sites can drop its `player` argument. This is mechanical, but
it should be done in one pass rather than piecemeal so the file stays internally consistent.

**2. Use `Region.add_locations()` and `Region.add_exits()` in `regions.py`.** Locations are
currently constructed and attached by hand:

```python
loc = PvZ2Location(player, loc_data.name, loc_data.code, region)
region.locations.append(loc)
```

`Region.add_locations({name: address, ...}, PvZ2Location)` does both steps, and `add_exits()` takes
either a list of region names or a `{region_name: entrance_name}` mapping. Worth noting for whoever
picks this up: the entrance-naming behaviour is not identical to the current
`tutorial.connect(region, f"Enter {name}")` calls, and `rules.py` looks entrances up by those exact
names. The side-path and shop connections rely on `connect()`'s auto-generated
`"<source> -> <dest>"` names, which are not referenced anywhere, but the keyed-world and Ancient
Egypt checkpoint entrances are. Any conversion has to keep those names byte-identical or update both
files together.

The event location and its locked Victory item are a deliberate exception — leave those constructed
by hand, since `add_locations()` has no path for placing a locked item.

### Open: shop logic does not model in-game unlock gating — owned by head dev

With Shopsanity on, the `Shop` region is connected straight from `Tutorial` with no access rule, on
the reasoning that affordability is a grind rather than a gate. That reasoning holds for price but
not for availability: 31 of the 39 tracked commodities carry an `UnlockLevel` in the game's store
data and cannot be purchased until that level is cleared.

Concretely, `Shop: bamboozle` requires `kongfu38`, which requires the Kongfu Temple Key plus most of
that world — while generation treats it as reachable from the start. A world key placed on a shop
check that is itself gated behind the world that key opens produces an unwinnable seed.

Two commodities, `caulipower` (`eighties39`) and `floawerPot` (`sky31`), are gated behind levels the
world and client do not track at all. They remain obtainable in-game but are entirely invisible to
logic.

The mapping from commodity to gating level lives in the game's own
`json/Features/StoreCommodityFeatures` asset, and every tracked commodity's `UnlockLevel` resolves to
a level already present in the client's `LOC_LEVELS` map apart from those two.

---

## `data/` — the level-pressure and logic dataset

Added 2026-08-30. Full design doc in [data/README.md](data/README.md); this section is the
**development** view: what state it is in, what was learned building it, and what comes next.

### State

Working and measured. `python data/build.py` finds the game checkout automatically at
`build/PVZGE-AP/PVZGE-Electron/pvzge_web` (and any `build/*/PVZGE-Electron/pvzge_web`), reads 3456
asset files, and writes nine artifacts to `data/generated/` plus `data/site/bundle.js`. Its checks
run as the `data` suite inside `test/run.py`.

Current numbers, for regression comparison:

```
files_read 3456   files_failed 0   documents 1293   objects 33293
unresolved RTIDs 21 (all "//"-commented-out refs)
zombies 465   plants measured 213   levels with waves 1158 / 1261
pressure baseline (egypt1, per lane) 10.21 HP/s
hazard modules unmapped: 5      hard threat tokens with no answer: 0
```

The 103 unmeasured levels are correct, not gaps: Danger Rooms, Sandbox, `random_zomboss_*`, Epic
Beghouled and `rhythm1` have no static wave table, because the game generates their waves at
runtime. They report `measured: false` and render grey.

### Asset-format facts that cost time to find

Everything here is in the module docstrings too, but they are the things to re-check first if a game
update breaks the extractor.

- **The assets are Cocos Creator packs, not bare RTON-JSON.** A file is a JSON *array*; the PvZ2
  payload is a nested `[0, "<name>", {"version":1,"objects":[...]}]`. `extract/rton.py` walks for
  that shape rather than indexing `[5][0][2]`, because the wrapper's shape varies with how many
  assets a pack holds.
- **The document name is both the RTID group and the level codename.** `"egypt19"` is the level;
  `RTID(pea@ProjectileProps)` resolves in the document named `ProjectileProps`. The level codenames
  match the client's `LOC_LEVELS` values exactly, so records join to AP locations with no
  translation table.
- **`@CurrentLevel` means "this document".** Waves are `RTID(Wave1@CurrentLevel)`. Resolution has to
  carry the document it is standing in or `Wave1` resolves to whichever level loaded first.
- **Field names are not the obvious ones.** Zombie HP is `Toughness`, not `Hitpoints`. Speed is
  `WalkSPS` — *squares per second*, so crossing time is `9 / WalkSPS` with **no calibration
  constant**; a 0.185 SPS mummy takes 48.6s, which is what it does in game.
- **Armor is a separate table.** `StartingArmors: ["egypt_armor2"]` → `ArmorProps`. `mummy_armor2` is
  190 body + 1100 armor. Reading the body alone understates that zombie by six times.
- **`SelectionMethod` lives in `SeedBankProperties`, not `LevelDefinition`.**
- **Wave budget is the game's own difficulty statement.** `WaveManagerProperties` gives
  `WaveSpendingPoints` + `WaveSpendingPointIncrement`, and `WaveManagerModuleProperties.DynamicZombies`
  gives the pools it is spent on. Points become HP through each pool's own mean
  HP-per-`WavePointCost`, so the difficulty is priced by the game rather than by us.

### Modelling decisions that are open questions

Three places where the data does not settle the answer and the code picks a defensible reading.
Each is commented at the site of the choice; they are listed together here because they are the
things most worth revisiting with playtest evidence.

1. **The per-pool `StartingPoints` / `PointIncrementPerWave` offsets are recorded but not spent.**
   Their values are negative and grow more negative (`-100`, then `-40` a wave), so they cannot be a
   spend; they read as either a phase-in or a cost modifier and nothing in the data decides which.
   The model uses the wave budget alone, at the mean price of whatever pools are live. Giving each
   pool its own full budget multiplied egypt3 by seven and put it above egypt26 — that bug is fixed,
   but the shape of it is the thing to watch.
2. **The wave clock is nominal** (25s, flag waves 35s). The game advances on a mix of
   `MinNextWaveHealthPercentage` and a timer that is not in the sheet. Every level is on the same
   synthetic clock, which makes levels comparable to each other and makes no single number a
   stopwatch reading.
3. **Grid rows are assumed to be 5.** No level states its own row count; the stage module probably
   does. Until that is read, `per_lane` divides by 5 everywhere, which understates the difficulty of
   levels that give you fewer usable rows.

### Bugs the real data exposed, worth not reintroducing

- A zombie's `water` tag is `LivesInDeepWater`, which means **"survives deep water"**, not "this
  level has water". Every Gargantuar carries it. Propagating it to the level made Dark Ages demand
  Lily Pad. Water as a level fact now comes from the module scan (`WaterLanes`, `LilypadPlacement`)
  alone.
- `equivalent_level` ("plays like") must walk **progression order** — world order then play order,
  with Tutorial first. Sorted alphabetically, Aerial Fortress leads and every side path reports
  "plays like sky3". Defaulting Tutorial's rank to the end put tutorial4 last and made *it* the
  fallback answer.
- It also has to use a **rolling median**, not a running max. `egypt5` is a ground-spawner level at
  index 2.7 in a world otherwise under 1.2; on a running max, every path in the game reported "plays
  like egypt5".
- A wave action's `Type` field must be read **non-recursively**. Every nested
  `{"Type": "RTID(mummy@ZombieTypes)"}` in a `Zombies` list also has a `Type`, so recursing
  collected sixty zombie codenames as hazard names.

### The finding this was built to produce

Side paths are one flat region gated on the level that reveals them, and the gap is large. Sorted by
`max_spike` (pressure index the hardest stage adds over its unlock level; +1 is twice the pressure):

```
Strawburst      unlock neon14   idx  1.10   +3.04   hardest Strawburst 2   beyond the main path
Squash          unlock egypt6   idx -0.19   +2.92   hardest Squash 3       plays like egypt32
Appease-mint 2  unlock iceage25 idx  2.06   +2.86   hardest ...2_5         beyond the main path
Parsnip         unlock beach22  idx  2.19   +2.52   hardest Parsnip 5      beyond the main path
Doom-shroom     unlock dark28   idx  3.94   +2.50   hardest Doom-shroom 0  beyond the main path
```

`Squash 3` is in logic from `egypt6` and plays like `egypt32`. "Beyond the main path" means no
window of ten consecutive main levels ever settles that heavy — the content is off the end of the
game's own curve. **Nothing in generation has been changed on the strength of this**; it is evidence
for a deliberate edit to `constants.py`, not an automatic one.

---

## Next: the loadout testing harness — not started

The dataset says what each level demands *in theory*. The next tool closes the loop by testing it in
the actual game, one level at a time, and feeding the verdicts back into the bands and the rules.

### What it has to do

For each level, take the **minimum loadout logic claims is sufficient** — the any-of picks from
`requirements.json`'s `must` groups, plus enough damage/sun to meet the pressure curve — load the
game straight into that level with exactly those plants, and let the user record what actually
happened. Per plant: **sufficient / lacking / overkill**. Per loadout: pass or fail, and if it
failed, *what would have made it work*. Then a second pass on the amended loadout to confirm the new
minimum. A **"next" button** loads the following level-and-loadout with no manual setup — the whole
value is in the testing being fast enough to do hundreds of times.

### Pieces that need building

**1. Loadout enumeration** (`data/model/loadouts.py`, new).
Turn a level's requirement vector into a small set of concrete candidate loadouts rather than a
combinatorial explosion. One per `must` group cross-product is already too many for the 36-member
Jester group, so pick a *representative* per group — cheapest, median band, and highest band — and
mark which one the candidate is testing. The loadout also needs the ordinary supply picks: a sun
producer, and attackers chosen by `afford_curve` until the margin against the pressure curve closes.

**2. Progressive upgrades must be part of the loadout, not an afterthought.**
`constants.UPGRADE_GROUPS` / `UPGRADE_ITEM_TO_CNS` define them and they are *progressive* — the Nth
copy of an upgrade item raises the plant a level — so "Peashooter" is not one data point but several,
and a loadout is a set of `(plant, upgrade_level)` pairs. `items.UPGRADE_ITEM_COUNT` and
`UPGRADE_POOL_SHARE` bound how many a seed can even contain. A verdict recorded against the wrong
upgrade level is worse than no verdict.

**3. A client bridge** (the harder half).
The injected client already has `LOC_LEVELS` and a `goToLevel` hook (`build_pvzge_ap.py`, around the
world-gate code). It needs a **test mode**: accept `{level, plants[], upgrades{}}` from outside,
force the seed bank to exactly those plants, and jump straight in. Options, in order of preference:

- a small local HTTP/WebSocket endpoint the client already connects to, reusing the AP client's
  existing socket plumbing rather than adding a second one;
- failing that, a file the client polls in the build directory, which devrun.py already writes to.

Whatever the transport, it belongs behind an explicit flag: this must never be reachable in a normal
seed. And **it changes `TMPPATCH_CONTENT`, so `drift_test.py` applies** — any function copied into
`test/client/*_fn.js` has to be re-copied, and the check must not be relaxed.

**4. Verdict capture in the site** (`data/site/`, new view).
Level, its loadout, the pressure curve, and a three-way control per plant (sufficient / lacking /
overkill), plus a free-form "what it needed" plant picker for failures. "Next" advances. Verdicts
persist to `data/curated/playtest.json` — **append-only, one record per run**, carrying the level,
the full loadout including upgrade levels, the verdicts, the dataset build hash, and a timestamp.
Append-only matters: a re-test after a game patch must not silently overwrite the observation that
disagreed with it.

**5. The feedback pass** (`data/model/calibrate.py`, new).
Read `playtest.json` and propose changes, never apply them silently:

- a plant repeatedly `lacking` for a role → lower its band in `plant_classes.json`; `overkill` →
  raise it. This is the fastest way to replace the curated seed bands with earned ones.
- a loadout that failed with every `must` group satisfied → the pressure threshold or the
  `threat_answers` predicate for that token is too weak.
- a loadout that passed well below the modelled requirement → the pressure model is overstating that
  level, which is the signal that one of the three open modelling questions above needs revisiting.
- output a **diff against `constants.py`** for the human to apply, in the same any-of-group shape
  `WORLD_ENTRY_PLANTS` and `STRETCH_ENTRY_PLANTS` already use.

`data/test_data.py` should grow a check that every plant named in `playtest.json` is still a real AP
item, so a renamed plant surfaces as a failure rather than as silently discarded evidence.

### After that: the editable logic tree

Replace the current Logic-graph view with a tree laid out like the **in-game world maps** — worlds as
branches, levels as nodes in play order, side paths hanging off the level that reveals them — with
full editing: drag a stretch cut, add or remove a requirement on an entrance, split a side path into
two regions. Edits write back to local data (a `data/curated/logic_overrides.json`, kept separate
from `generated/` so a rebuild cannot destroy them), and `build.py` emits the resulting `constants.py`
diff. The read-only graph that exists today is the input to this; the pieces it already has are the
real entrance names, the real requirement text with its source table, and the stretch assignment
computed by `locations.world_stretches` itself.

Two constraints carried over from the rest of the repo and easy to lose here:

- **Entrance names are load-bearing.** `rules.py` looks them up by exact string
  (`f"Enter {world}"`, `f"Enter {stretch}"`). An editor that renames or invents one produces logic
  that silently does nothing. `data/test_data.py` already asserts the graph invents no entrance name;
  keep that check pointed at the editor's output too.
- **A conveyor level can never be gated on a plant.** The belt decides what you play, so a plant
  requirement there is one the player can satisfy and still not be able to use. `requirement_vector`
  refuses to propose one; the editor must refuse to accept one.
