// Drives the REAL syncFeatureFlags() from build_pvzge_ap.py.
//
// The game gates real behaviour on cp.features, not just buttons:
//     feature_plantfood || (this.showPlantfood = false)
//     feature_powerup   || (this.showPowerUps  = false)
//     feature_coins     || (this.dropCoins     = false)
//     feature_zengarden || (this.dropSprouts   = false)
//     !feature_store    || (this.storeButton.node.active = false)
// and sets them from level progress as you play. An AP save is rebuilt from
// checked locations on every connect, and a real save (2026-08-16) with
// egypt1, tutorial1-4 and eleven Modern Day levels checked still had all nine
// false -- so under AP they never turn on by themselves. This is what repairs
// that, and these cases pin it to the game's own conditions.
const { syncFeatureFlags, FEATURE_UNLOCK_LEVELS, PROGRESS_FINISHED }
  = require('./feature_fn.js');

let failed = 0;
const ok = m => console.log('  ok    ' + m);
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const is = (got, want, m) =>
  JSON.stringify(got) === JSON.stringify(want)
    ? ok(m) : fail(`${m}  (got ${JSON.stringify(got)}, want ${JSON.stringify(want)})`);
const sorted = a => a.slice().sort();

// A save the way rebuildAPSave leaves it: levelProps keyed by codename, each
// { progress: 3 } for a checked location.
const save = (levels, features) => ({
  levelProps: Object.fromEntries(
    Object.entries(levels).map(([k, v]) => [k, { progress: v }])),
  ...(features ? { features } : {}),
});

console.log('\n  each flag answers to the level the game names');

let cp = save({ egypt2: 3 });
is(sorted(syncFeatureFlags(cp)), ['feature_almanac'], 'egypt2 -> almanac');

cp = save({ egypt5: 3 });
is(sorted(syncFeatureFlags(cp)), ['feature_powerup', 'feature_zengarden'],
   'egypt5 -> power-ups and zen garden');

cp = save({ egypt6: 3 });
is(sorted(syncFeatureFlags(cp)), ['feature_store'], 'egypt6 -> store');

cp = save({ egypt1: 3 });
is(sorted(syncFeatureFlags(cp)),
   ['feature_coins', 'feature_plantfood', 'feature_worldmap'],
   'egypt1 cleared -> coins, plant food, world map');

console.log('\n  coins have two conditions, and one is a lower bar');

// The game: tutorial4 finished OR egypt1 merely past `locked`.
cp = save({ tutorial4: 3 });
is(sorted(syncFeatureFlags(cp)), ['feature_coins'], 'tutorial4 finished -> coins');

cp = save({ egypt1: 1 });
is(sorted(syncFeatureFlags(cp)), ['feature_coins'],
   'egypt1 unlocked_neverPlayed is enough for coins, alone');

cp = save({ egypt1: 0, tutorial4: 0 });
is(syncFeatureFlags(cp), [], 'locked (0) is not enough for anything');

// ...but the higher bar still governs the other two.
cp = save({ egypt1: 1 });
syncFeatureFlags(cp);
is(!!cp.features.feature_plantfood, false,
   'egypt1 at 1 does not grant plant food, which wants 3');

console.log('\n  the reported save: egypt1 + tutorials, nothing else');

// Exactly the state that proved the bug. Coins must come on; the store must
// not, because egypt6 was never cleared.
cp = save({ tutorial1: 3, tutorial2: 3, tutorial3: 3, tutorial4: 3, egypt1: 3 });
const opened = sorted(syncFeatureFlags(cp));
is(opened, ['feature_coins', 'feature_plantfood', 'feature_worldmap'],
   'coins, plant food and world map open');
is(!!cp.features.feature_store, false, 'the store stays shut without egypt6');
is(!!cp.features.feature_zengarden, false, 'the zen garden stays shut without egypt5');

console.log('\n  thresholds');

for (const p of [0, 1, 2]) {
  cp = save({ egypt6: p });
  is(syncFeatureFlags(cp), [], `store: progress ${p} is not a clear (needs ${PROGRESS_FINISHED})`);
}
cp = save({ egypt6: 4 });
is(sorted(syncFeatureFlags(cp)), ['feature_store'], 'store: progress 4 (finished) counts too');

console.log('\n  it repairs, and then stays quiet');

cp = save({ egypt6: 3 });
syncFeatureFlags(cp);
is(syncFeatureFlags(cp), [], 'second pass reports nothing new');
is(cp.features.feature_store, true, '...and leaves the flag on');

cp = save({ egypt6: 3 }, { feature_store: true });
is(syncFeatureFlags(cp), [], 'a flag the game already set is not re-opened');

// Never turns one off: the game's chain does not, and a flag that flickered
// would take the store button away mid-session.
cp = save({ egypt1: 3 }, { feature_store: true });
is(!!cp.features.feature_store, true, 'no egypt6 progress does not close an open store');

console.log('\n  it survives a half-built save');

is(syncFeatureFlags(null), [], 'no player at all');
is(syncFeatureFlags(undefined), [], 'undefined player');
cp = {};
is(syncFeatureFlags(cp), [], 'no levelProps yet');
is(typeof cp.features, 'object', '...but features is created for the game to fill');
cp = { levelProps: { egypt6: null } };
is(syncFeatureFlags(cp), [], 'a null level entry does not throw');
cp = { levelProps: { egypt6: {} } };
is(syncFeatureFlags(cp), [], 'a level entry with no progress does not throw');

console.log('\n  it grants nothing the game does not');

// feature_lod and feature_worldkeys are never set to true anywhere in
// index.js, so there is no condition to mirror and this must not invent one.
for (const never of ['feature_lod', 'feature_worldkeys']) {
  is(never in FEATURE_UNLOCK_LEVELS, false, `${never} has no rule, and must not`);
}
cp = save({ tutorial4: 3, egypt1: 3, egypt2: 3, egypt5: 3, egypt6: 3 });
syncFeatureFlags(cp);
is(sorted(Object.keys(cp.features)),
   ['feature_almanac', 'feature_coins', 'feature_plantfood', 'feature_powerup',
    'feature_store', 'feature_worldmap', 'feature_zengarden'],
   'a fully cleared save sets these seven and no others');

if (failed) {
  console.log(`\n${failed} FAILURE(S)`);
  process.exit(1);
}
console.log('\nFEATURE FLAG SYNC OK');
