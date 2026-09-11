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

Two commodities, `caulipower` (`eighties39`) and `floawerPot` (`sky31`), were gated behind levels the
world and client did not track at all. Both levels are tracked now -- `neon39` and `sky31`, added when
the second halves of those two worlds were filled in -- so the gap is the general one above rather
than a separate case.

Which plants the store prices in tickets rotates weekly, which `SHOP_PLANT_COMMODITIES` and
`SHOP_ABSENT_COMMODITIES` in constants.py handle by freezing the gem-priced names and routing the
rest into `UNREACHABLE_LOCATIONS`. That snapshot goes stale on its own: a card that rotates back in
is a check no seed builds, one that rotates out is a check that can never fire. Re-reading a current
checkout and hand-editing the two lists is the fix -- they cannot be derived, because a commodity
that rotates out still has to keep its location id.

The mapping from commodity to gating level lives in the game's own
`json/Features/StoreCommodityFeatures` asset, and every tracked commodity's `UnlockLevel` resolves to
a level already present in the client's `LOC_LEVELS` map apart from those two.

### Closed: zombie randomization was fair on price and nothing else

`shuffle_zombies` traded zombies strictly on the game's `WavePointCost`, which is a wave-generator
budget price rather than a measure of how hard a zombie is to kill. Per-level cost stayed inside
0.78-1.21 (p5-p95) while per-level effective HP ran 0.56-2.51, with 34 levels at 3x or worse --
`pirate1` fielded eighteen 10000 HP immobile shields in place of its basic pirates. Separately, the
bespoke-module verdict was cached under `thisLevelsID` while the object list it read belongs to the
*previous* level until the component catches up, so a level could inherit the wrong verdict in either
direction, including the unwinnable camel one.

Fixed across the tier table, `fill_slot_data` and the client hook: an effective-HP axis on the tier
key, three families of non-walker excluded outright, a corrected aerial tag, and a per-level plan in
the client that weighs the roster it is about to produce. Per-level HP now lands at 0.96-1.06 with
about 70% of spawns still changing.

The audit, the measurements and the design are in [ZOMBIE_RANDO_DEV.md](ZOMBIE_RANDO_DEV.md). The
table is generated by [tools/gen_zombie_tiers.py](tools/gen_zombie_tiers.py) and must be regenerated,
not hand edited; `test/zombie_tier_test.py` and `test/balance_test.py` are what hold the result.

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
