// Drives the REAL zombie-shuffle functions from build_pvzge_ap.py through a
// stand-in for the game's static `zombies` class.
//
// The hook rewrites the codename handed to getZombieEnumWithPropByZombieTypes,
// so what the stand-in records IS the level's roster after shuffling. Every
// assertion below reads off that.
const {
  window, st, TEST_TIERS,
  syncZombieConfig, installZombieHook, makeZombiesClass, setLevel, resetCache,
} = require('./zombie_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok   = m => console.log('  ok    ' + m);

const TIER_OF = {};
for (const t of Object.keys(TEST_TIERS)) for (const z of TEST_TIERS[t]) TIER_OF[z] = t;
const ALL = Object.keys(TIER_OF);

// Resolve one codename and report what the original was actually called with.
function resolve(Z, type) { Z.calls.length = 0; Z.getZombieEnumWithPropByZombieTypes(type); return Z.calls[0]; }

function fresh() {
  const Z = makeZombiesClass();
  installZombieHook(Z);
  // Must be idempotent: the module can register more than once, and a second
  // wrap would shuffle an already-shuffled codename.
  installZombieHook(Z);
  resetCache();
  return Z;
}

st.shuffleZombies = true;
st.zombieSeed     = 987654321;
st.zombieTiers    = TEST_TIERS;
syncZombieConfig();

// ── off ──────────────────────────────────────────────────────────────────────
st.shuffleZombies = false;
syncZombieConfig();
{
  const Z = fresh();
  setLevel('egypt10');
  const changed = ALL.filter(z => resolve(Z, z) !== z);
  if (changed.length) fail('option off changed ' + changed.join(', '));
  else ok(`option off leaves all ${ALL.length} zombies untouched`);
}

// A seed predating the option sends no zombie keys at all, and that has to
// read as off rather than as "shuffle with an empty tier table".
{
  delete st.shuffleZombies; delete st.zombieSeed; delete st.zombieTiers;
  syncZombieConfig();
  const Z = fresh();
  setLevel('egypt10');
  const changed = ALL.filter(z => resolve(Z, z) !== z);
  if (changed.length) fail('missing slot_data changed ' + changed.join(', '));
  else ok('slot_data with no zombie keys reads as off');
}

st.shuffleZombies = true;
st.zombieSeed     = 987654321;
st.zombieTiers    = TEST_TIERS;
syncZombieConfig();

// ── the form the game actually passes ────────────────────────────────────────
// THE regression this file exists for. Wave data names zombies as
// RTID(codename@ZombieTypes), not bare -- 57855 of the ~62000 type references
// in the shipped levels are wrapped, and only ~4800 are bare. An earlier
// version matched the raw string against a table keyed by bare codename, so
// every wave spawn missed and the option looked like it did nothing at all.
// This whole suite passed, because every case in it used bare names.
{
  const Z = fresh();
  setLevel('egypt10');
  const rtid = z => `RTID(${z}@ZombieTypes)`;

  // Not "every one changed" -- a pool contains the zombie itself, so landing
  // back on it is a legitimate roll and that check would be flaky. The bug
  // being guarded against left EVERY wrapped name byte-identical.
  const swappable = ALL.filter(z => TEST_TIERS[TIER_OF[z]].length > 1);
  const changed = swappable.filter(z => resolve(Z, rtid(z)) !== rtid(z));
  if (!changed.length)
    fail('not one RTID-wrapped zombie was swapped -- the wrapper is not being ' +
         'stripped before the tier lookup, so every wave spawn misses');
  else ok(`${changed.length} of ${swappable.length} RTID-wrapped zombies swapped ` +
          `(the rest rolled back onto themselves, which is legal)`);

  // the result has to come back wrapped, or the game cannot resolve it
  const out = resolve(Z, rtid('mummy'));
  const m = /^RTID\(([^@]+)@ZombieTypes\)$/.exec(out);
  if (!m) fail(`an RTID went in and "${out}" came out -- it must stay wrapped`);
  else if (TIER_OF[m[1]] !== TIER_OF['mummy']) fail(`RTID swap left the tier: ${out}`);
  else ok('an RTID goes in and a correctly wrapped RTID of the same tier comes out');

  // both spellings of one zombie must agree, or a level's preview cards show
  // different zombies from the ones that actually walk on
  const disagree = ALL.filter(z => {
    const bare = resolve(Z, z);
    const w = /^RTID\(([^@]+)@/.exec(resolve(Z, rtid(z)));
    return !w || w[1] !== bare;
  });
  if (disagree.length)
    fail(`${disagree.length} zombies resolve differently bare vs wrapped, e.g. ${disagree[0]}`);
  else ok('bare and RTID spellings of a zombie resolve to the same replacement');

  // a level-local type is re-scoped to @ZombieTypes, which always resolves;
  // the replacement has no entry under the level's own scope
  const local = resolve(Z, 'RTID(dark_juggler@CurrentLevel)');
  if (!/^RTID\([^@]+@ZombieTypes\)$/.test(local))
    fail(`a @CurrentLevel type came back as "${local}"`);
  else ok('a level-local RTID is re-scoped to @ZombieTypes so it resolves');

  // an unknown codename inside a wrapper is still left exactly as it came
  const untouched = resolve(Z, 'RTID(zomboss_egypt@ZombieTypes)');
  if (untouched !== 'RTID(zomboss_egypt@ZombieTypes)')
    fail(`a wrapped Zomboss was swapped: ${untouched}`);
  else ok('a wrapped untiered codename passes through unchanged');
}

// ── levels built around their zombies are skipped whole ─────────────────────
// A minigame module drives its zombies structurally, so a swap can leave the
// level unwinnable rather than merely different. Both of these were found in
// play testing, not by this suite.
{
  const cases = [
    ['egypt7',   'CamelMinigameProperties',    'camel matching -- you win by matching hump counts'],
    ['egypt16',  'CamelMinigameProperties',    'camel matching'],
    ['egypt23',  'CamelMinigameProperties',    'camel matching'],
    ['pirate3',  'CannonMinigameProperties',   'nothing but seagulls, which fly in'],
    ['pirate11', 'CannonMinigameProperties',   'nothing but seagulls'],
    ['pirate20', 'CannonMinigameProperties',   'nothing but seagulls'],
    ['modern8',  'BeghouledZombieSpawnerProperties', 'match-3 set piece'],
    ['beach8',   'BowlingMinigameProperties',  'bowling set piece'],
    ['cowboy18', 'LastStandMinigameProperties','last stand set piece'],
    ['future10_1','FutureMinigameProperties',  'future set piece'],
    ['cowboy12', 'CowboyMinigameProperties',   'minecart set piece'],
  ];
  let bad = [];
  for (const [level, mod] of cases) {
    const Z = fresh();
    setLevel(level, ['WaveManagerProperties', mod]);
    const changed = ALL.filter(z => resolve(Z, z) !== z);
    if (changed.length) bad.push(`${level} (${mod}) swapped ${changed.length}`);
  }
  if (bad.length) fail('bespoke levels were shuffled: ' + bad.join('; '));
  else ok(`${cases.length} minigame levels are left entirely alone`);
}

// ...and an ordinary level right next door still shuffles, or the rule is a
// blanket off switch rather than a targeted one.
{
  const Z = fresh();
  setLevel('egypt8', ['WaveManagerProperties', 'SeedBankProperties']);
  const changed = ALL.filter(z => resolve(Z, z) !== z);
  if (!changed.length) fail('an ordinary level stopped shuffling too');
  else ok(`an ordinary level beside them still shuffles (${changed.length} swaps)`);
}

// Unreadable level objects must fail CLOSED. Not shuffling is a cheap
// mistake; shuffling a level that cannot then be beaten is not.
{
  for (const [label, lc] of [
    ['no levelController', undefined],
    ['no component',       { thisLevelsID: ['x'] }],
    ['no object list',     { thisLevelsID: ['x'], component: {} }],
    ['empty object list',  { thisLevelsID: ['x'], component: { currentLevelObjects: [] } }],
  ]) {
    const Z = fresh();
    setLevel('probe');
    window._AP_levelController = lc;
    const changed = ALL.filter(z => resolve(Z, z) !== z);
    if (changed.length) fail(`${label}: shuffled anyway, should fail closed`);
  }
  if (!failed) ok('an unreadable level fails closed and is not shuffled');
}

// ── swaps stay inside the tier ───────────────────────────────────────────────
{
  let checked = 0;
  for (const level of ['egypt10', 'dark3', 'beach22', 'modern16', 'iceage7']) {
    const Z = fresh();
    setLevel(level);
    for (const z of ALL) {
      const got = resolve(Z, z);
      checked++;
      if (TIER_OF[got] !== TIER_OF[z]) {
        fail(`${level}: ${z} (${TIER_OF[z]}) became ${got} (${TIER_OF[got]})`);
      }
    }
  }
  ok(`${checked} resolutions across 5 levels all stayed in tier`);
}

// This is the assertion the whole option rests on: a threat mechanic can
// neither appear in a world that had none nor vanish from one whose access
// rule is built on it. Both hold only because the threat tiers are closed.
{
  const JEST = new Set(TEST_TIERS['t3-land-jester']);
  const ICE  = new Set(TEST_TIERS['t3-land-iceblock']);
  const GARG = new Set(TEST_TIERS['t5-water-garg']);
  let jest = 0, ice = 0, garg = 0, leaked = 0;
  for (let i = 0; i < 200; i++) {
    const Z = fresh();
    setLevel('level' + i);
    for (const z of ALL) {
      const got = resolve(Z, z);
      if (JEST.has(z)) { jest++; if (!JEST.has(got)) leaked++; }
      if (ICE.has(z))  { ice++;  if (!ICE.has(got))  leaked++; }
      if (GARG.has(z)) { garg++; if (!GARG.has(got)) leaked++; }
      // and nothing ordinary may become one
      if (!JEST.has(z) && JEST.has(got)) leaked++;
      if (!ICE.has(z)  && ICE.has(got))  leaked++;
      if (!GARG.has(z) && GARG.has(got)) leaked++;
    }
  }
  if (leaked) fail(`${leaked} threat/Gargantuar leaks across 200 levels`);
  else ok(`over 200 levels no threat leaked either way ` +
          `(${jest} jester, ${ice} iceblock, ${garg} Gargantuar resolutions)`);
}

// A tier of one has nothing to trade for, so it must come back untouched
// rather than being "swapped" for itself through the RNG.
{
  const Z = fresh();
  setLevel('beach1');
  const got = resolve(Z, 'beach_snorkel');
  if (got !== 'beach_snorkel') fail(`single-member tier swapped: ${got}`);
  else ok('a tier with one member never swaps');
}

// Zomboss types, lawn placeholders and anything else absent from the table
// have no tier, so they must pass straight through. This is what keeps boss
// fights intact and lets a lawn placeholder resolve to its stage's zombie --
// that resolution re-enters the hook with a real codename, which does shuffle.
{
  const Z = fresh();
  setLevel('egypt35');
  const untiered = ['zomboss_egypt', 'lawn', 'lawn_armor1', 'lawn_gargantuar',
                    'not_a_real_zombie'];
  const changed = untiered.filter(z => resolve(Z, z) !== z);
  if (changed.length) fail('untiered codename was swapped: ' + changed.join(', '));
  else ok(`${untiered.length} untiered codenames (Zomboss, lawn placeholders) pass through`);
}

// ── stability ────────────────────────────────────────────────────────────────
// A retry must not be a reroll. Same level, fresh hook and cold cache: the
// roll has to land in the same place, because it is derived and not stored.
{
  const a = {}, b = {};
  let Z = fresh(); setLevel('egypt10');
  for (const z of ALL) a[z] = resolve(Z, z);
  Z = fresh(); setLevel('egypt10');
  for (const z of ALL) b[z] = resolve(Z, z);
  const drift = ALL.filter(z => a[z] !== b[z]);
  if (drift.length) fail('replaying a level rerolled ' + drift.join(', '));
  else ok('replaying a level gives the identical roster');
}

// Different levels must actually differ, or "per level" is a lie. Compared
// on the big tier only; a 3-member tier collides often by chance.
{
  const big = TEST_TIERS['t1-land'];
  const rosters = new Set();
  for (let i = 0; i < 60; i++) {
    const Z = fresh();
    setLevel('lvl' + i);
    rosters.add(big.map(z => resolve(Z, z)).join(','));
  }
  if (rosters.size < 30) fail(`60 levels produced only ${rosters.size} distinct rosters`);
  else ok(`60 levels produced ${rosters.size} distinct rosters`);
}

// The per-level cache must be dropped when the level changes, not carried
// into the next one -- that would pin the whole seed to the first level's roll.
{
  const Z = fresh();
  setLevel('egypt10');
  const first = ALL.map(z => resolve(Z, z)).join(',');
  setLevel('dark3');                       // same hook, no resetCache()
  const second = ALL.map(z => resolve(Z, z)).join(',');
  if (first === second) fail('the roster carried over from the previous level');
  else ok('changing level drops the cached roster');
}

// Two slots on one seed get different zombie_seed values and must not see the
// same lawn.
{
  const roster = () => {
    const Z = fresh(); setLevel('egypt10');
    return TEST_TIERS['t1-land'].map(z => resolve(Z, z)).join(',');
  };
  st.zombieSeed = 111; syncZombieConfig(); const one = roster();
  st.zombieSeed = 222; syncZombieConfig(); const two = roster();
  if (one === two) fail('two slot seeds produced the same roster');
  else ok('a different slot seed produces a different roster');
  st.zombieSeed = 987654321; syncZombieConfig();
}

// ── levels with no ID ────────────────────────────────────────────────────────
// Level of the Day and local test levels have an empty thisLevelsID. They
// still have to resolve, deterministically, rather than throw.
{
  const Z = fresh();
  setLevel(null);
  const a = ALL.map(z => resolve(Z, z)).join(',');
  const Z2 = fresh();
  setLevel(null);
  const b = ALL.map(z => resolve(Z2, z)).join(',');
  if (a !== b) fail('a level with no ID rolled inconsistently');
  else ok('a level with no ID still rolls deterministically');
}

// The hook must survive a levelController that is missing or half-built --
// it runs on every spawn, so throwing here would take the level down.
{
  const Z = fresh();
  window._AP_levelController = undefined;
  let threw = null;
  try { resolve(Z, 'mummy'); } catch (e) { threw = e; }
  window._AP_levelController = { };          // present, no thisLevelsID
  try { resolve(Z, 'mummy'); } catch (e) { threw = e; }
  if (threw) fail('a missing levelController threw: ' + threw.message);
  else ok('a missing or half-built levelController does not throw');
}

console.log(failed ? `\n${failed} FAILURE(S)` : '\nZOMBIE SHUFFLE HOOK OK');
process.exit(failed ? 1 : 0);
