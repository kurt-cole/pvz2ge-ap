# PvZ2 Gardendless — Archipelago World

An [Archipelago](https://archipelago.gg) multiworld integration for **PvZ2 Gardendless**, a web-based
reimagining of Plants vs. Zombies 2 ([PVZGE-Electron](https://github.com/Twig6943/PVZGE-Electron) /
[pvzge_web](https://github.com/Gzh0821/pvzge_web)). Each world (except Ancient Egypt) is unlocked by
finding its unique Key item, Modern Day unlocks once a configurable number of world goals are met, and
victory is defeating the Modern Day Zomboss.

## Installation

### Full build (packages the game client as an .exe)

This produces the actual game — an Electron app with the Archipelago client injected — via a Tk GUI
installer, not a CLI build. Launch it either:

- **From Archipelago**: install the `.apworld`, open the Archipelago Launcher, and click
  **"PvZ2 Gardendless Installer"**.
- **Standalone**: `python pvz2gardendless/build_pvzge_ap.py`

Pick a build directory in the GUI, then it will:

1. Check that `git`, `node`, and `npm` are on your PATH.
2. Clone `PVZGE-Electron` (the Electron wrapper) and `pvzge_web` (the game source, ~300MB, from `master`).
3. Overwrite `tmpPatch.js` with the Archipelago client code (save-slot redirection, plant-unlock gating,
   location/item sync, etc.).
4. Patch `main.js` to enable F12 devtools.
5. Run `npm install`.
6. Run `npm run build:win` (or `:mac` / `:linux`), producing `PvZ Gardendless AP.exe`.

This takes several minutes the first time (clone + `npm install` + packaging).

**Requirements:** Python 3.8+, Node.js 18+, Git, and an internet connection for the initial clone.

### Fast iteration on the client JS (Primarily for development)

Once you've run the full build once, use `devrun.py` instead of rebuilding — it skips the clone,
`npm install`, and packaging steps entirely:

```
python devrun.py                              # patch + launch via `npm start`
python devrun.py --patch-only                  # just rewrite tmpPatch.js, don't launch
python devrun.py "D:\custom\PVZGE-Electron"    # override build dir
```

It rewrites `tmpPatch.js` from the same client source embedded in `build_pvzge_ap.py` and launches
unpackaged via `npm start`, so edits show up in seconds instead of a multi-minute rebuild. The default
build directory is `C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron`; pass a path as the first
argument if yours differs.

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
