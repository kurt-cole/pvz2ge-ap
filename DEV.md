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

### Closed: npm blocks Electron's postinstall, and Node 26 breaks its extraction

Two separate faults that both end at the same symptom -- `npm start` (and therefore
[devrun.py](devrun.py)) dying with "Electron failed to install correctly" while the packaged app
builds and runs perfectly.

1. npm 10.9+ does not run dependency install scripts unless package.json lists them. Upstream
   declares this for pnpm only (`pnpm-workspace.yaml`'s `allowBuilds`), so under npm the Electron
   postinstall that downloads the binary is skipped. The installer now writes an `allowScripts`
   entry for `electron` and `electron-winstaller`, unpinned so it survives a version bump.
2. Even when that postinstall does run, `extract-zip` truncates the Electron archive to its first
   entry on Node 26: it writes one file, resolves successfully, and `install.js` exits 0 having
   produced a `dist/` with a single `snapshot_blob.bin` and no `path.txt`. The zip itself is intact.

`_ensure_electron_binary` in [build_pvzge_ap.py](pvz2gardendless/build_pvzge_ap.py) covers both. It
runs after the build, where electron-builder has already populated `~/.cache/electron`, and
re-extracts that zip with Python's `zipfile`, restoring the mode bits `zipfile` drops. It is
non-fatal by design: electron-builder downloads its own Electron, so only devrun needs this.
