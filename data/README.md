# `data/` — level pressure, plant classes, and where the logic should cut

This directory answers four questions the apworld's logic currently guesses at:

1. **How much does a level demand?** Not "how many zombies" — how much HP arrives, how fast it
   walks left, and what damage rate you must land to stop it.
2. **What specialised zombies are in it?** Read off the same properties `zombie_data.py` tiers on.
3. **What hazards are in it?** Read off the level's own modules.
4. **What plants supply that?** Plants classified into elements and roles, with bands, so a rule
   can say "a b3 area attacker with warmth" instead of naming five plants by hand.

It exists because the logic is loose in a specific, checkable way: `WORLD_ENTRY_PLANTS` gates four
worlds on one plant each, stretch cuts land on milestones rather than on difficulty, and every side
path is one flat region gated on the level that reveals it — so `Squash 3` is in logic the moment
`egypt6` is cleared, which is nowhere near true in play.

**Nothing here changes generation.** It reads the apworld and reports. Turning a finding into a rule
is a deliberate edit to `constants.py`, and the site is built to make that edit obvious rather than
to make it automatically.

---

## Run it

```
python data/build.py                       # everything; finds the game checkout on its own
python data/build.py --game "<path>"       # point at a pvzge_web checkout explicitly
python data/serve.py                       # serve data/site, or just open index.html
python data/test_data.py                   # offline checks (also runs inside test/run.py)
```

`build.py` looks for a checkout at `build/*/PVZGE-Electron/pvzge_web` (what the installer produces),
`Base Game/`, and the directory `devrun.py` defaults to. With one it measures 1158 of 1261 levels;
without one it still builds the whole structure tier. Build products are gitignored — a full
measured run takes about a minute, a structure-only run about two seconds.

Development notes, open modelling questions and the next tools to build are in
[DEV.md](../DEV.md).

---

## The two tiers

| | needs | gives |
|---|---|---|
| **structure** | this repo only | every level, its world, its stretch, the region graph and its real access rules, side paths and what reveals them, zombie threat tags, plant classes |
| **measured** | a `pvzge_web` checkout | wave tables, zombie HP, plant damage, level modules — the numbers |

The 103 levels that stay unmeasured with a checkout present are correct, not gaps: Danger Rooms,
Sandbox, the Zomboss fights, Epic Beghouled and `rhythm1` have no static wave table because the game
generates their waves at runtime.

Every artifact says which tier it is, and **an unmeasured level is never reported as a zero**. That
one rule matters more than it looks: a zero would rank every unmeasured level as the easiest in the
game and quietly invert exactly the ordering this whole directory exists to establish.

---

## The metric

A zombie is not a lump of HP. It is a lump of HP on a clock — you have exactly as long as it takes
to walk nine columns. So the unit is

```
threat rate   r(z) = effective_hp(z) / cross_seconds(z)        [HP per second]
```

which reads directly as *the damage per second you must land on this zombie to kill it exactly at
the house line*. `effective_hp` includes armor, which is why a t3 zombie is not "a bit tougher" but
three times the problem. Summed over everything on the lawn at time *t*, that is **required DPS** —
stated in the same unit a plant's DPS is stated in, which is the whole reason the two can be
compared at all.

From that curve, per level:

| | |
|---|---|
| `peak` | the hardest moment |
| `sustained` | the 75th percentile — what the level asks for *most of the time*; peak alone reads one flag wave as the whole level |
| `per_lane` | `peak / usable rows`. Five rows of 500 HP/s is a different game from one row of 500 |
| `front_loading` | share of total pressure in the first third. Front-loaded is a **sun** problem; back-loaded is a **scaling** problem |
| `burst_index` | `peak / sustained`. High means spikes, which burst plants answer and sustained DPS does not |
| `index` | `log2(per_lane / baseline)`, anchored on `egypt1`. **+1 is twice the pressure.** This is the number everything else compares against |

**This is a comparator, not a simulation.** Plants do not fire, zombies do not eat, armor is HP
rather than a damage filter, and the wave clock is nominal (the game advances waves on a mix of
"previous wave mostly dead" and a timer, neither of which is readable off the sheet, so every level
is laid on the same synthetic clock). Quote a number as "egypt19-equivalent", never as a stopwatch
reading.

---

## Threats are separate from pressure, on purpose

Pressure is the quantitative demand. **Tokens** are the qualitative one — a Jester, deep water,
tombstones — and a token is answered or it is not. An unanswered *hard* token makes a level
unwinnable no matter how much damage you have.

That split is the design claim of this directory:

> **Tokens are what an access rule should be made of. Pressure is what tells you where the rule belongs.**

"Enough damage" is a loadout question, not an item question, and should never become a rule. But the
point on the pressure curve where the game stops carrying a player is exactly the point a stretch
should be cut — and that *is* readable.

Tokens come from two places, and each record says which:

- **zombie tags** — `jester`, `iceblock`, `air`, `blocker`, `garg`, `water`, `hurdle`, `burrow`,
  `summoner`, `camel`. Same fields `zombie_data.py` partitions its tiers on.
- **hazard tags** — `graves`, `tide`, `wind`, `gloom`, `portals`, `lava`, `conveyor`, `no_sun_drop`,
  `endless`, `trap_tiles`, `power_tiles`, `potions`, `mold`, `objective`, … from the level's module
  list and from wave actions that name their own effect, via `curated/hazards.json`.

`hazards.json` also carries an `ignore` list: the ~100 objclasses that are level *plumbing* — stages,
mowers, intros, win conditions, seed banks, the wave manager itself. Without it the extractor's
`unmapped` report is mostly noise and stops being the thing you read to extend the table. With it,
five objclasses are currently unmapped.

`curated/threat_answers.json` maps each token to a predicate over plant records, with a severity
(`hard` / `soft` / `flavour`) and the rule in `rules.py` that models it today — or `null`, which is
the interesting case: **a hard token with no rule is a logic gap**, and the site's Threats view lists
them.

One guard matters more than the rest: a level whose `selection` is `conveyor` **cannot be gated on a
plant at all**, because the belt decides what you play. `requirement_vector` refuses to propose a
requirement on such a level.

---

## Plant classes

Three orthogonal axes, because a plant is not one thing and belongs in as many classes as apply:

- **elements** — `kinetic fire ice electric poison shadow light sun aquatic explosive arcane`
- **roles**, each with a **band** `b1..b5` — `dps_single dps_aoe dps_pierce dps_lob burst instakill
  slow freeze stun push wall shield sun_econ air_clear grave_clear warmth thaw hypno revive disarm
  illuminate lure terrain support`
- **flags** — `jester_safe consumable timed aquatic_only land_only sun_hungry no_data`

Torchwood is `fire` + `{support:b5, warmth:b4}` + `jester_safe`. A rule can reach it as a fire plant,
as a warmth source, or as a Jester answer, and all three are true at once.

**Bands are relative, not absolute.** `b1..b5` are quintiles of the role's own measured distribution,
so a band survives a balance patch that moves every plant together and only moves when a plant moves
*relative to its peers*. "A b3 area attacker answers this" therefore keeps meaning the same thing
across game updates.

Precedence when building a plant record, strongest first:

1. **`constants.py`'s derived lists.** They are what generation actually reads. `jester_safe`,
   `consumable`, `timed` and `no_data` are never taken from anywhere else.
2. **Extracted game stats**, when a checkout is present — sun, recharge, DPS, burst, warming radius.
3. **`curated/plant_classes.json`**, for elements and for bands the numbers cannot decide.

Every field carries a provenance of `curated` or `derived`, and the site renders them differently, so
nobody mistakes an opinion for a measurement.

---

## Side paths

The problem, stated precisely: each path is **one flat region** gated on `SIDE_PATH_UNLOCK`, so every
stage is in logic the moment the first is — and the stages climb steeply.

`sidepaths.json` gives, per path: the pressure index of its unlock level, the index of every stage,
the **main-path level each stage plays like**, and `max_spike` — how much index the hardest stage
adds over the level that reveals it. **A spike above +1.0 means the hardest stage is more than twice
the pressure the path is gated at.**

"plays like" is a rolling median over ten consecutive main-path levels, in progression order, not the
first level to spike that high — the question is where that much pressure becomes *normal*, which is
where a gate belongs. A stage can come back as **"beyond the main path"**: no window of ten main
levels ever settles that heavy, so there is no level to gate it behind. That is an answer, not a gap,
and it is true of the hardest stage of most paths.

The measured result: `Squash 3` is in logic from `egypt6` (index −0.19) and plays like `egypt32`.

The fix that data suggests is not "gate the whole region deeper" — that would put stage 0 out of
reach for no reason. It is to **split the path**, the same way worlds are cut into stretches, at the
stage where `plays_like` jumps a world. `suggested_deep_gate` names where the far end belongs.

---

## Layout

```
paths.py           where the game checkout is, where artifacts go
apworld.py         imports the real apworld offline, through test/apstub.py
build.py           the pipeline: read -> classify -> measure -> write
serve.py           local static server for site/
test_data.py       offline checks; also wired into test/run.py

extract/           needs a game checkout
  rton.py          index over the converted-JSON asset tree; resolves RTIDs
  zombies.py       HP, armor, speed, wave cost, threat tags
  plants.py        sun, recharge, DPS, burst, warming radius, jester safety
  levels.py        waves, modules, selection method, sun rules, grid

model/             pure, no game data required
  taxonomy.py      the vocabularies; everything else speaks these strings
  classify.py      plant records: curated seed + derived lists + measurements
  pressure.py      the required-DPS curve and everything derived from it
  requirements.py  predicate language, requirement vectors, the supply model
  logic.py         the apworld's CURRENT regions, rules and side paths

curated/           judgement, and labelled as such
  plant_classes.json    elements and seed bands, one line per plant
  threat_answers.json   token -> predicate, severity, and the rule that models it
  hazards.json          module objclass -> hazard token; per-world fallback

site/              index.html + app.js, dependency-free, opens off disk
generated/         build products (gitignored)
```

---

## The rules this layer lives by

- **Never mirror the apworld.** `constants.py` and `locations.py` are imported and asked. A
  hand-kept copy of the rules would be wrong within a week, and `test_data.py` fails if this layer
  ever describes a rule generation does not have.
- **Prefer `list:NAME` to a plant list.** A predicate that names `list:FIRE_AURA_PLANTS` stays true
  when that list changes. One that re-lists the five plants becomes a second source of truth.
- **Derived beats curated, and say which.** The repo already learned this twice the hard way
  (Chard Guard's "damage" that was knockback; Sap-fling's unreversible projectile that dealt none).
  Every record carries provenance for the same reason those comments exist.
- **Missing is not zero.** Unmeasured levels, unknown plants and unresolved RTIDs are all recorded
  as gaps. `coverage.json` is the honest account of how much of a run was real.

## Extending it

- **A new hazard**: add the objclass substring to `hazards.json`, then the token to
  `taxonomy.HAZARD_TAGS` and `threat_answers.json`. The extractor writes every objclass it could not
  map into `hazards.json`'s `unmapped` list, so this is reading rather than guessing.
- **A new plant**: add a line to `plant_classes.json`. `test_data.py` fails on any AP plant with no
  entry, because a plant with no class can answer nothing and would silently vanish from every
  candidate set.
- **A new game version**: rerun `build.py --game`. `coverage.json` reports files that would not
  parse, objects with no alias, and unresolved RTIDs; a large jump in any of those means the asset
  format moved.
