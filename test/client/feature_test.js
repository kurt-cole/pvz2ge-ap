// Drives the REAL syncFeatureFlags() from build_pvzge_ap.py.
//
// The store button in index.js is gated on one boolean:
//     !feats.feature_store || (this.storeButton.node.active = false)
// and the game sets it from its own chain:
//     n.feature_store || getLevelProgressByID("egypt6").progress >= 3
//                        && (n.feature_store = true)
// A save with egypt6 cleared and the flag unset therefore has no store at all.
// rebuildAPSave() rewrites levelProps from checked locations every connect, so
// that state is reachable; this is what repairs it.
const { syncFeatureFlags, PROGRESS_FINISHED } = require('./feature_fn.js');

let failed = 0;
const ok = m => console.log('  ok    ' + m);
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const is = (got, want, m) =>
  JSON.stringify(got) === JSON.stringify(want)
    ? ok(m) : fail(`${m}  (got ${JSON.stringify(got)}, want ${JSON.stringify(want)})`);

// A save the way rebuildAPSave leaves it: levelProps keyed by codename, each
// { progress: 3 } for a checked location.
const save = (levels, features) => ({
  levelProps: Object.fromEntries(
    Object.entries(levels).map(([k, v]) => [k, { progress: v }])),
  ...(features ? { features } : {}),
});

console.log('\n  egypt6 drives the store flag');

let cp = save({ egypt1: 3, egypt5: 3 });
is(syncFeatureFlags(cp), [], 'egypt6 not cleared -> nothing opened');
is(!!cp.features.feature_store, false, '...and the store stays shut');

cp = save({ egypt6: 3 });
is(syncFeatureFlags(cp), ['feature_store'], 'egypt6 cleared -> store opens');
is(cp.features.feature_store, true, '...and the flag is actually set');

// The game's own threshold. 1 and 2 are "unlocked" states, not a clear, and
// treating them as one would open the store off a level merely reachable.
for (const p of [0, 1, 2]) {
  cp = save({ egypt6: p });
  is(syncFeatureFlags(cp), [], `progress ${p} is not a clear (needs ${PROGRESS_FINISHED})`);
}
cp = save({ egypt6: 4 });
is(syncFeatureFlags(cp), ['feature_store'], 'progress 4 (finished) counts too');

console.log('\n  it repairs, and then stays quiet');

cp = save({ egypt6: 3 });
syncFeatureFlags(cp);
is(syncFeatureFlags(cp), [], 'second pass reports nothing new');
is(cp.features.feature_store, true, '...and leaves the flag on');

// Every rebuild calls this, so a flag the game already set must not be
// re-reported -- the caller logs whatever comes back.
cp = save({ egypt6: 3 }, { feature_store: true });
is(syncFeatureFlags(cp), [], 'a flag the game already set is not re-opened');

// Never turns one off: the game's chain does not, and a flag that flickered
// would take the store button away mid-session.
cp = save({ egypt1: 3 }, { feature_store: true });
is(syncFeatureFlags(cp), [], 'no egypt6 progress does not close an open store');
is(cp.features.feature_store, true, '...the flag survives');

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

// Only the keys it set exist. getFeatureProps() returns this object as-is, so
// anything it invents would read as an unlock the player never earned.
cp = save({ egypt6: 3 });
syncFeatureFlags(cp);
is(Object.keys(cp.features), ['feature_store'], 'sets no flag it was not asked to');

if (failed) {
  console.log(`\n${failed} FAILURE(S)`);
  process.exit(1);
}
console.log('\nFEATURE FLAG SYNC OK');
