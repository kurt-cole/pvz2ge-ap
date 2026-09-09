// Drives the REAL zombie-shuffle functions from build_pvzge_ap.py through a
// stand-in for the game's static `zombies` class.
//
// The hook rewrites the codename handed to getZombieEnumWithPropByZombieTypes,
// so what the stand-in records IS the level's roster after shuffling. Every
// assertion below reads off that.
const {
  window, st, TEST_TIERS, TEST_HP,
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
  const JEST = new Set(TEST_TIERS['t3-land-jester-h20']);
  const ICE  = new Set(TEST_TIERS['t3-land-iceblock-h21']);
  const GARG = new Set(TEST_TIERS['t5-water-garg-h27']);
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
  const big = TEST_TIERS['t1-land-h17'];
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
    return TEST_TIERS['t1-land-h17'].map(z => resolve(Z, z)).join(',');
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


// ── the level's own roster drives the plan ───────────────────────────────────
// The swap used to be rolled one codename at a time, which meant it never saw
// more than one zombie at once. Reading the level's object list is what lets
// it weigh the roster and hand distinct zombies distinct replacements.
{
  const Z = fresh();
  setLevel('egypt10', ['WaveManagerProperties'],
           { mummy: 10, cowboy: 6, pirate: 4, future: 2 });
  const picks = ['mummy', 'cowboy', 'pirate', 'future'].map(z => resolve(Z, z));
  if (new Set(picks).size !== picks.length)
    fail('two of the level\'s zombies collapsed onto one replacement: ' + picks.join(', '));
  else ok('distinct zombies in a roster get distinct replacements');

  // The pool is bigger than the roster, so nobody should have been forced to
  // reuse. A codename the level never names still resolves, down the lazy path.
  const stranger = resolve(Z, 'dark');
  if (!TEST_TIERS['t1-land-h17'].includes(stranger))
    fail('a codename outside the roster left its tier: ' + stranger);
  else ok('a codename the level never names still resolves, in tier');
}

// A roster longer than its tier cannot be injective, and must not deadlock or
// drop anybody trying to be.
{
  const Z = fresh();
  const roster = {};
  for (const z of TEST_TIERS['t3-land-jester-h20']) roster[z] = 1;
  roster['iceage_troglobite'] = 1;
  setLevel('crowded', ['WaveManagerProperties'], roster);
  const out = Object.keys(roster).map(z => resolve(Z, z));
  if (out.some(z => z === undefined || z === null)) fail('a crowded roster dropped a zombie');
  else ok('a roster as large as its tier still maps every zombie');
}

// ── the budget guard ─────────────────────────────────────────────────────────
// Every individual swap is inside an HP band, but a level rolls many at once
// and the errors can all land the same way. The guard weighs the roster the
// plan would produce and re-rolls if it drifted.
{
  // One member of the tier is made ten times as tough as the rest, so any plan
  // that hands it to a level of eight basic zombies is far too heavy.
  const HEAVY = 'kongfu';
  const hp = Object.assign({}, TEST_HP);
  hp[HEAVY] = TEST_HP[HEAVY] * 10;
  st.zombieHp = hp;
  syncZombieConfig();

  let overweight = 0, total = 0;
  for (let i = 0; i < 120; i++) {
    const Z = fresh();
    setLevel('budget' + i, ['WaveManagerProperties'], { mummy: 8 });
    const got = resolve(Z, 'mummy');
    total++;
    if (got === HEAVY) overweight++;
  }
  if (overweight) fail(`${overweight} of ${total} single-type levels took a 10x zombie`);
  else ok(`${total} levels all refused a swap that would have tripled their HP`);

  // ...and the guard must not be a blanket off switch: a swap that keeps the
  // weight is still made.
  let changed = 0;
  for (let i = 0; i < 120; i++) {
    const Z = fresh();
    setLevel('budget' + i, ['WaveManagerProperties'], { mummy: 8 });
    if (resolve(Z, 'mummy') !== 'mummy') changed++;
  }
  if (changed < 60) fail(`the guard stopped shuffling: only ${changed} of 120 levels changed`);
  else ok(`${changed} of 120 levels still shuffled under the guard`);

  // A level whose whole tier is too heavy has nowhere to go, so it keeps
  // exactly what it shipped with rather than shipping something unfair.
  {
    const only = { mummy: 1, cowboy: 1 };
    const heavyAll = {};
    for (const z of TEST_TIERS['t1-land-h17']) heavyAll[z] = TEST_HP[z] * 20;
    heavyAll['mummy'] = TEST_HP['mummy'];
    heavyAll['cowboy'] = TEST_HP['cowboy'];
    st.zombieHp = heavyAll;
    syncZombieConfig();
    const Z = fresh();
    setLevel('nowhere', ['WaveManagerProperties'], only);
    const got = Object.keys(only).map(z => resolve(Z, z));
    if (got.join(',') !== 'mummy,cowboy')
      fail('a level with no affordable swap shipped one anyway: ' + got.join(','));
    else ok('a level with no swap inside the budget keeps its own zombies');
  }

  // A seed generated before the guard existed sends no zombie_hp at all. That
  // has to read as "no guard", not as "every zombie weighs nothing".
  {
    delete st.zombieHp;
    syncZombieConfig();
    const Z = fresh();
    setLevel('egypt10', ['WaveManagerProperties'], { mummy: 8 });
    const withoutHp = resolve(Z, 'mummy');
    st.zombieHp = TEST_HP;                     // flat: the guard is a no-op
    syncZombieConfig();
    const Z2 = fresh();
    setLevel('egypt10', ['WaveManagerProperties'], { mummy: 8 });
    const withFlatHp = resolve(Z2, 'mummy');
    if (withoutHp !== withFlatHp)
      fail(`no HP table rolled ${withoutHp}, a flat one rolled ${withFlatHp} -- ` +
           'a seed predating the guard must roll as it always did');
    else ok('a seed with no zombie_hp rolls exactly as it did before the guard');
  }
  st.zombieHp = TEST_HP;
  syncZombieConfig();
}

// ── the stale object list ────────────────────────────────────────────────────
// THE regression this section exists for. thisLevelsID is assigned when the
// level data loads; currentLevelObjects is filled in by the component
// afterwards. Between the two, the ID is the new level's and the object list
// is still the previous level's. Keying the verdict on the ID alone let a
// resolve landing in that window pin the wrong answer for the whole level.
{
  // Entering egypt7 (camel matching) from an ordinary level: if the ordinary
  // level's objects are still in place when the first zombie resolves, the
  // plan must NOT stay built on them once the real list arrives.
  const Z = fresh();
  setLevel('egypt8', ['WaveManagerProperties'], { mummy: 4 });
  resolve(Z, 'mummy');                                  // plan built, ordinary
  window._AP_levelController.thisLevelsID = ['egypt7']; // ID moves first
  resolve(Z, 'mummy');                                  // resolve in the window
  setLevel('egypt7', ['WaveManagerProperties', 'CamelMinigameProperties'],
           { mummy: 4 });                               // objects catch up
  const got = resolve(Z, 'mummy');
  if (got !== 'mummy')
    fail('a bespoke level entered from an ordinary one was shuffled anyway ' +
         `(mummy -> ${got}) -- the stale object list pinned the wrong verdict`);
  else ok('a bespoke level is still spared when its object list arrives late');
}
{
  // ...and the other direction: an ordinary level entered from egypt7 must not
  // inherit egypt7's "do not shuffle".
  const Z = fresh();
  setLevel('egypt7', ['WaveManagerProperties', 'CamelMinigameProperties'],
           { mummy: 4 });
  resolve(Z, 'mummy');
  window._AP_levelController.thisLevelsID = ['egypt8'];
  resolve(Z, 'mummy');
  setLevel('egypt8', ['WaveManagerProperties'], { mummy: 4 });
  const changed = TEST_TIERS['t1-land-h17'].filter(z => resolve(Z, z) !== z);
  if (!changed.length)
    fail('an ordinary level inherited the previous level\'s bespoke verdict');
  else ok(`an ordinary level entered from a bespoke one still shuffles (${changed.length})`);
}
{
  // A level that reloads its own objects -- a retry -- is the same level, and
  // must roll the same way rather than being treated as new.
  const Z = fresh();
  setLevel('egypt10', ['WaveManagerProperties'], { mummy: 4, cowboy: 2 });
  const first = ['mummy', 'cowboy'].map(z => resolve(Z, z)).join(',');
  setLevel('egypt10', ['WaveManagerProperties'], { mummy: 4, cowboy: 2 });
  const again = ['mummy', 'cowboy'].map(z => resolve(Z, z)).join(',');
  if (first !== again) fail(`a retry rerolled: ${first} then ${again}`);
  else ok('a retry rebuilds the same plan from the same level');
}

console.log(failed ? `\n${failed} FAILURE(S)` : '\nZOMBIE SHUFFLE HOOK OK');
process.exit(failed ? 1 : 0);
