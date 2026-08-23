// Progressive world unlocks, client side.
//
// A world opens at its World Key level and each unlock carries it one stretch
// further. Unlike the plant-count gates, which only ever existed in generation
// logic, this one is enforced in game: KeyListener.goToLevel is every path a
// level can start from -- the map node, the Danger Room entrance, an epic
// portal, ForceNextLevel chaining, the next-level and restart buttons, and
// getForceLevel() on resume -- so refusing there refuses all of them.
const G = require('./worldgate_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);
const EGYPT = 'Progressive Ancient Egypt';
const NEON = 'Progressive Neon Mixtape Tour';
const held = (...pairs) => {
  const o = {};
  for (let i = 0; i < pairs.length; i += 2) o[pairs[i]] = pairs[i + 1];
  return o;
};

// ── which levels are gated at all ────────────────────────────────────────────
G.reset({ worldGates: G.gates() });
if (G.levelBlockedBy('egypt1')) fail('egypt1 is in the opening and must never be gated');
else if (G.levelBlockedBy('egypt8')) fail('egypt8 is the World Key level, still the opening');
else ok('the opening stretch is never gated');

if (!G.levelBlockedBy('egypt9')) fail('egypt9 was playable with no unlocks');
else if (G.levelBlockedBy('egypt9').need !== 1) fail('egypt9 should need 1 unlock');
else ok('egypt9 needs the first unlock');

if (G.levelBlockedBy('egypt26').need !== 2) fail('egypt26 should need 2 unlocks');
else ok('egypt26 needs the second');

// A level in no gate table is a level this seed does not gate -- a side path,
// a tutorial step, a world that was too small to cut. It must stay playable.
if (G.levelBlockedBy('tutorial1')) fail('an ungated level was blocked');
else ok('a level outside the gates is left alone');

// ── the count is what opens it ───────────────────────────────────────────────
G.reset({ worldGates: G.gates(), worldUnlocks: held(EGYPT, 1) });
if (G.levelBlockedBy('egypt9')) fail('one unlock did not open egypt9');
else if (!G.levelBlockedBy('egypt26')) fail('one unlock opened the last stretch too');
else ok('one unlock opens the middle stretch and no further');

G.reset({ worldGates: G.gates(), worldUnlocks: held(EGYPT, 2) });
if (G.levelBlockedBy('egypt26') || G.levelBlockedBy('egypt35'))
  fail('two unlocks did not open the last stretch');
else ok('two unlocks open the last stretch');

// Per world, not a running total: Egypt's unlocks must do nothing for Neon.
G.reset({ worldGates: G.gates(), worldUnlocks: held(EGYPT, 2) });
if (!G.levelBlockedBy('eighties17')) fail("Egypt's unlocks opened Neon Mixtape Tour");
else ok("one world's unlocks do not open another's");

// ── the location-name to level-id translation ────────────────────────────────
// slot_data sends AP location names; goToLevel is called with game level ids.
// Neon is the world where those differ.
G.reset({ worldGates: G.gates(), worldUnlocks: held(NEON, 1) });
if (G.levelBlockedBy('eighties17')) fail('neon17 did not resolve to eighties17');
else if (!G.levelBlockedBy('eighties33')) fail('eighties33 should still need 2');
else ok('location names resolve to game level ids (neon17 -> eighties17)');

G.reset({ worldGates: G.gates() });
if (G.levelBlockedBy(undefined)) fail('an undefined level id produced a gate');
else if (G.gateCount() !== 7)
  fail('expected 7 gated levels, got ' + G.gateCount() + ' -- a shop card leaked in');
else ok('a location with no level (a shop card) is not turned into a gate');

// Danger Rooms are levels too, and are gated with the stretch they sit in.
G.reset({ worldGates: G.gates() });
if (!G.levelBlockedBy('egypt_dangerroom')) fail('a gated Danger Room was playable');
else ok('a Danger Room follows the stretch it sits in');

// ── seeds with no gates ──────────────────────────────────────────────────────
// Everything generated before 2026-08-23 sends no world_gates at all, and its
// pool contains no unlocks -- so reading a missing table as "all locked" would
// leave those seeds unplayable past each world's opening.
G.reset({});
for (const lvl of ['egypt9', 'egypt26', 'eighties33']) {
  if (G.levelBlockedBy(lvl)) { fail('an older seed blocked ' + lvl); break; }
}
if (!failed) ok('a seed with no gates locks nothing');

// ── the hook ─────────────────────────────────────────────────────────────────
G.reset({ worldGates: G.gates() });
let KL = G.makeKeyListener();
G.installLevelGateHook(KL);
KL.goToLevel(['egypt1']);
if (KL.calls !== 1) fail('an allowed level did not start');
else if (JSON.stringify(KL.started[0]) !== JSON.stringify(['egypt1']))
  fail('the arguments were not passed through: ' + JSON.stringify(KL.started[0]));
else ok('an allowed level starts, with its arguments intact');

KL.goToLevel(['egypt9']);
if (KL.calls !== 1) fail('a locked level was started anyway');
else if (!G.toasts.length) fail('a locked level was refused silently');
else ok('a locked level does not start, and says why');

// The refusal has to be awaitable AND has to land somewhere. Callers run
// darken() before awaiting this, and the next-level button has already torn
// the level down, so resolving without loading a scene leaves a black screen.
const before = KL.worldmaps;
const ret = KL.goToLevel(['egypt9']);
if (!ret || typeof ret.then !== 'function')
  fail('refusing did not return a promise: ' + ret);
else if (KL.worldmaps !== before + 1)
  fail('refusing did not send the player to the world map');
else ok('refusing returns a promise and lands on the world map');

// ...and a build with no GoToWorldmap must still not throw.
const noMap = G.makeKeyListener();
delete noMap.GoToWorldmap;
G.installLevelGateHook(noMap);
const r2 = noMap.goToLevel(['egypt9']);
if (!r2 || typeof r2.then !== 'function') fail('no-worldmap refusal broke');
else if (noMap.calls) fail('no-worldmap build started a locked level');
else ok('a build with no GoToWorldmap still refuses cleanly');

// A call can carry more than one level (restart passes thisLevelsID).
G.reset({ worldGates: G.gates() });
KL = G.makeKeyListener();
G.installLevelGateHook(KL);
KL.goToLevel(['egypt1', 'egypt26']);
if (KL.calls) fail('a batch containing a locked level was allowed');
else ok('a batch is refused if any level in it is locked');

// Not every caller passes an array.
G.reset({ worldGates: G.gates() });
KL = G.makeKeyListener();
G.installLevelGateHook(KL);
KL.goToLevel('egypt9');
if (KL.calls) fail('a bare level id bypassed the gate');
else ok('a bare level id is gated too, not just an array');

// Once the unlock arrives the same call goes through.
G.reset({ worldGates: G.gates(), worldUnlocks: held(EGYPT, 1) });
KL = G.makeKeyListener();
G.installLevelGateHook(KL);
KL.goToLevel(['egypt9']);
if (KL.calls !== 1) fail('the unlock did not let the level start');
else ok('the level starts once its unlock has arrived');

// ── installing the hook ──────────────────────────────────────────────────────
G.reset({ worldGates: G.gates() });
KL = G.makeKeyListener();
G.installLevelGateHook(KL);
const wrapped = KL.goToLevel;
G.installLevelGateHook(KL);
if (KL.goToLevel !== wrapped) fail('installing twice wrapped goToLevel twice');
else ok('installing twice is a no-op');

// goToLevel is assigned while the module runs, so the export can be captured
// before it exists. The poll retries, and the retry has to work.
const bare = G.makeKeyListener({ missing: true });
G.installLevelGateHook(bare);
if (bare._ap_hooked_levelgate) fail('claimed to hook a KeyListener with no goToLevel');
else {
  bare.goToLevel = function (levels) { bare.started.push(levels); bare.calls++; return Promise.resolve(); };
  G.installLevelGateHook(bare);
  bare.goToLevel(['egypt9']);
  if (bare.calls) fail('the retried hook did not gate');
  else ok('a KeyListener whose goToLevel arrives late is hooked on the retry');
}

G.installLevelGateHook(null);
G.installLevelGateHook(undefined);
ok('installing on nothing does not throw');

// ── counting the unlocks ─────────────────────────────────────────────────────
G.reset({ worldGates: G.gates() });
if (G.worldOf(EGYPT) !== 'Ancient Egypt')
  fail('the unlock item was not mapped back to its world');
else if (G.worldOf('Progressive Sun Shovel'))
  fail('an upgrade item was taken for a world unlock');
else ok('unlock items map back to their world, and upgrades do not');

G.reset({ worldGates: G.gates(), worldUnlocks: held(EGYPT, 3) });
if (G.unlocksHeld(EGYPT) !== 3) fail('the unlock count was not read back');
else if (G.unlocksHeld('nothing') !== 0) fail('an unheld item did not count 0');
else ok('unlock counts are read per item, and default to 0');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nWORLD GATES OK');
process.exit(failed ? 1 : 0);
