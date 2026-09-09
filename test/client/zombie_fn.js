// Copies of the zombie-shuffle functions from build_pvzge_ap.py, kept in sync
// by drift_test.py. Do not edit the copied functions here -- edit the client
// and re-copy. Everything above and below them is harness scaffolding.
const window = {};
const st = {};

// The tier table generation ships and sends in slot_data. Trimmed to the
// shapes the tests exercise: a big land tier, a Gargantuar-only tier, the two
// threat tiers whose whole point is that they cannot leak into another tier,
// and a single-member tier that must never swap. Every member of a tier is
// the same weight in TEST_HP below, except where a case wants otherwise.
const TEST_TIERS = {
  't1-land-h17': ['mummy', 'cowboy', 'pirate', 'future', 'dark', 'iceage',
                  'lostcity', 'eighties', 'dino', 'sky', 'beach', 'kongfu'],
  't3-land-jester-h20': ['birthday_juggler', 'dark_juggler', 'foodfight_chefster'],
  't3-land-iceblock-h21': ['iceage_troglobite', 'iceage_troglobite_1block',
                           'iceage_troglobite_2block', 'birthday_troglobite'],
  't5-water-garg-h27': ['dark_gargantuar', 'egypt_gargantuar', 'future_gargantuar'],
  't1-water-h17': ['beach_snorkel'],
};

// Effective HP, as slot_data's zombie_hp sends it. Flat within a tier so the
// budget guard is a no-op unless a case deliberately unbalances one.
const TEST_HP = {};
for (const tier of Object.keys(TEST_TIERS)) {
  const weight = { 't1-land-h17': 190, 't3-land-jester-h20': 420,
                   't3-land-iceblock-h21': 470, 't5-water-garg-h27': 3600,
                   't1-water-h17': 190 }[tier];
  for (const z of TEST_TIERS[tier]) TEST_HP[z] = weight;
}

function _apHash(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function _apRng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The level's plan: which codename becomes which, worked out ONCE per level
// rather than one codename at a time. Rolling the level as a whole is what
// lets the swap weigh the roster it is about to produce (the budget guard
// below) and hand distinct zombies distinct replacements; a lazy per-codename
// roll can do neither, because it never sees more than one zombie at a time.
let _apZombiePlan = null;

// Levels built AROUND particular zombies are left alone completely. A
// minigame module drives its zombies structurally rather than merely
// spawning them, so a swap there can leave the level unwinnable rather than
// just different:
//   CamelMinigameProperties   egypt7/16/23 -- you win by MATCHING camels on
//                             hump count. Swapping them left nothing to
//                             match. Found in play testing.
//   CannonMinigameProperties  pirate3/11/20 field nothing but seagulls, and
//                             a seagull flies in -- its flight is behaviour
//                             on PirateSeagullZombie, not a property, so
//                             there is no flag to partition it by.
//   Beghouled / Bowling / LastStand / Cowboy / Future / Rhythm -- same
//                             shape: the level is a set piece.
// 73 of the shipped levels carry one of these. Every other level still
// shuffles, which is the overwhelming majority of the game.
//
// This is the general answer to a class of bug that excluding zombie
// families one at a time only ever patches case by case.
const AP_BESPOKE_MODULES = /Minigame|Beghouled|Rhythm/;

// Where a level names a zombie. Only a Zombies[].Type entry is a spawn -- one
// zombie, once. The pool keys are candidates a wave generator may or may not
// draw from, so they are mapped like everything else but weigh nothing.
const AP_ZOMBIE_POOL_KEYS = /^(ZombiePool|MustContainZombie|AddToZombiePool)$/;

// Wave data does NOT name zombies by bare codename. Of the ~62000 type
// references in the shipped levels, 57855 are RTID(codename@ZombieTypes) and
// only ~4800 are bare -- the bare ones being the LawnProps role slots and a
// few scripted spawns. The tier table is keyed by bare codename, so the
// wrapper has to come off before the lookup and go back on after it.
// Matching on the raw string instead means every wave spawn misses, which
// looks exactly like the option doing nothing.
const _AP_RTID = /^RTID\(([^@()]+)@([^()]*)\)$/;

function _apZombieBare(type) {
  const wrapped = _AP_RTID.exec(type);
  return wrapped ? wrapped[1] : type;
}

// The level's object list, or null if it cannot be read. Read through rather
// than cached: it is the identity the whole plan is keyed on, because
// thisLevelsID alone is not enough -- see _apZombiePlanFor.
function _apLevelObjects() {
  try {
    const lc = window._AP_levelController;
    const objs = lc && lc.component && lc.component.currentLevelObjects;
    return (Array.isArray(objs) && objs.length) ? objs : null;
  } catch (e) { return null; }
}

function _apLevelKey() {
  try {
    const ids = window._AP_levelController && window._AP_levelController.thisLevelsID;
    if (ids && ids.length) return ids.join(',');
  } catch (e) { /* fall through to the shared key */ }
  // Levels with no ID -- local test levels, Level of the Day -- share one
  // key. They still roll deterministically, just not per level.
  return '';
}

// Every zombie the level names, with a count of how many it actually spawns.
// Walks the level's own objects, so it sees exactly what the level will
// field: wave actions, storm spawners, gravestone props and the wave
// generator's pools alike.
function _apLevelRoster(objs) {
  const counts = {};
  const note = function (value, spawn) {
    if (typeof value !== 'string') return;
    const name = _apZombieBare(value);
    if (!window._AP_zombieTierOf[name]) return;
    counts[name] = (counts[name] || 0) + (spawn ? 1 : 0);
  };
  const walk = function (node, inPool, depth) {
    if (!node || depth > 12) return;
    if (Array.isArray(node)) {
      for (const value of node) {
        if (typeof value === 'string') { if (inPool) note(value, false); }
        else walk(value, inPool, depth + 1);
      }
    } else if (typeof node === 'object') {
      for (const key of Object.keys(node)) {
        if (AP_ZOMBIE_POOL_KEYS.test(key)) walk(node[key], true, depth + 1);
        else if (key === 'Type') note(node[key], !inPool);
        else walk(node[key], inPool, depth + 1);
      }
    }
  };
  for (const obj of objs) walk(obj && obj.objdata, false, 0);
  return counts;
}

// One roll of the whole level. `salt` is the attempt number: attempt 0 keys
// exactly as the per-codename roll always did, so a level the guard does not
// have to touch fields the roster it would have fielded before the guard
// existed.
function _apRollPlan(levelKey, roster, salt) {
  const map = {};
  const used = {};
  // Sorted, so the plan does not depend on the order the level happened to
  // name its zombies in.
  for (const codename of Object.keys(roster).sort()) {
    const pool = window._AP_zombieTiers[window._AP_zombieTierOf[codename]];
    if (!pool || pool.length < 2) { map[codename] = codename; continue; }
    const rnd = _apRng(_apHash(String(window._AP_zombieSeed || 0) + '|' +
                               levelKey + '|' + codename +
                               (salt ? '|a' + salt : '')));
    let pick = pool[Math.floor(rnd() * pool.length)];
    // Distinct zombies prefer distinct replacements: without this a level
    // that fields four types can collapse them onto one, which is a duller
    // lawn than either the original or the shuffle intends. Probes forward
    // rather than rerolling so it stays a pure function of the codename.
    for (let i = 0; i < pool.length && used[pick]; i++) {
      pick = pool[(pool.indexOf(pick) + 1) % pool.length];
    }
    used[pick] = true;
    map[codename] = pick;
  }
  return map;
}

// How much killing a roster takes, as the sum of every spawn's effective HP.
// Returns 0 when the HP table is missing -- a seed generated before the
// budget guard existed sends no zombie_hp -- which the caller reads as "no
// guard", and it then behaves exactly as it did before.
function _apRosterWeight(roster, map) {
  const hp = window._AP_zombieHp;
  if (!hp) return 0;
  let total = 0;
  for (const codename of Object.keys(roster)) {
    const weight = hp[map ? map[codename] : codename];
    if (!weight) continue;
    total += weight * roster[codename];
  }
  return total;
}

// Budget guard. Every individual swap is already inside an HP band, but a
// level rolls many at once and the errors can all land the same way, so the
// level as a whole is weighed and re-rolled if it drifted. Deterministic:
// the attempt number is part of the key, so a retry is still not a reroll.
const AP_BUDGET_OK   = [0.85, 1.15];  // good enough, stop rolling
const AP_BUDGET_HARD = [0.60, 1.60];  // outside this, do not ship the level
const AP_BUDGET_TRIES = 6;

function _apPlanFor(levelKey, roster) {
  const before = _apRosterWeight(roster, null);
  let best = null, bestErr = Infinity;
  for (let attempt = 0; attempt < AP_BUDGET_TRIES; attempt++) {
    const map = _apRollPlan(levelKey, roster, attempt);
    if (!before) return map;            // no HP table: take the first roll
    const ratio = _apRosterWeight(roster, map) / before;
    if (ratio >= AP_BUDGET_OK[0] && ratio <= AP_BUDGET_OK[1]) return map;
    // How far off, in a way that treats twice as heavy and half as heavy as
    // equally wrong.
    const err = Math.abs(Math.log(ratio || 1e-6));
    if (err < bestErr) { bestErr = err; best = { map: map, ratio: ratio }; }
  }
  if (best && best.ratio >= AP_BUDGET_HARD[0] && best.ratio <= AP_BUDGET_HARD[1])
    return best.map;
  // Nothing rolled was close enough. The level keeps exactly what it shipped
  // with, which is never wrong, only unshuffled. Spelled out as an identity
  // map rather than returned empty: an empty plan is not "leave these alone",
  // it is "these were never planned", and the lazy path would then roll every
  // one of them individually -- which is the roll this just refused.
  const identity = {};
  for (const codename of Object.keys(roster)) identity[codename] = codename;
  return identity;
}

// The plan for the level being played, built once and reused.
//
// Keyed on the object list as well as the level ID, and that is not belt and
// braces: thisLevelsID is assigned when the level data loads, while
// currentLevelObjects is filled in by the component afterwards, so between
// the two the ID is the new level's and the object list is still the
// PREVIOUS level's. Keying on the ID alone let a resolve landing in that
// window pin the wrong answer for the whole level, in both directions -- an
// ordinary level entered from egypt7 silently stopped shuffling, and egypt7
// entered from an ordinary level got shuffled, which is the unwinnable camel
// bug all over again.
function _apZombiePlanFor(objs) {
  const levelKey = _apLevelKey();
  if (_apZombiePlan && _apZombiePlan.objs === objs &&
      _apZombiePlan.levelKey === levelKey) return _apZombiePlan;
  // Fails CLOSED: if the level's object list cannot be read, assume it is
  // bespoke and do not shuffle. currentLevelObjects is filled in by
  // readLevelJson before any zombie is resolved, so an unreadable one means
  // something has moved -- and a level that does not shuffle is a far
  // cheaper mistake than one that cannot be beaten.
  let bespoke = true, map = {};
  if (objs) {
    bespoke = false;
    for (const o of objs) {
      if (o && AP_BESPOKE_MODULES.test(o.objclass || '')) { bespoke = true; break; }
    }
    if (!bespoke) map = _apPlanFor(levelKey, _apLevelRoster(objs));
  }
  _apZombiePlan = { objs: objs, levelKey: levelKey, bespoke: bespoke, map: map };
  return _apZombiePlan;
}

function _apZombieSwap(type) {
  const tierOf = window._AP_zombieTierOf;
  if (!tierOf) return type;
  const wrapped = _AP_RTID.exec(type);
  const codename = wrapped ? wrapped[1] : type;
  const tier = tierOf[codename];
  if (!tier) return type;
  const pool = window._AP_zombieTiers[tier];
  // A tier of one has nothing to trade for, so the level keeps what it had.
  if (!pool || pool.length < 2) return type;
  const plan = _apZombiePlanFor(_apLevelObjects());
  if (plan.bespoke) return type;
  let pick = plan.map[codename];
  if (pick === undefined) {
    // Not in the level's own object list: a lawn placeholder resolving to
    // the stage's zombie, a redirection, a scripted spawn. Rolled the old
    // way, on the same key the plan's first attempt uses, and remembered on
    // the plan so the answer cannot change mid-level.
    const rnd = _apRng(_apHash(String(window._AP_zombieSeed || 0) + '|' +
                               plan.levelKey + '|' + codename));
    pick = pool[Math.floor(rnd() * pool.length)];
    plan.map[codename] = pick;
  }
  // Always re-wrapped as @ZombieTypes rather than the scope it arrived in.
  // Every codename in the tier table is an alias in the game's global
  // ZombieTypes table, so that scope always resolves; a level that defines
  // its own type (RTID(x@CurrentLevel), 69 of those) has no entry for the
  // replacement under its local scope and would resolve to nothing.
  return wrapped ? 'RTID(' + pick + '@ZombieTypes)' : pick;
}
// Module-level state the copied functions close over, declared here for the
// same reason: it lives outside any function, so drift_test does not see it.
let _apZombieDepth = 0;


function installZombieHook(Z) {
  if (!Z || Z._ap_hooked_zombies ||
      typeof Z.getZombieEnumWithPropByZombieTypes !== 'function') return;
  const _origGetZombieEnum = Z.getZombieEnumWithPropByZombieTypes;
  Z.getZombieEnumWithPropByZombieTypes = function (type) {
    const args = Array.prototype.slice.call(arguments);
    try {
      if (window._AP_shuffleZombies && typeof type === 'string' &&
          _apZombieDepth < 8) {
        args[0] = _apZombieSwap(type);
      }
    } catch (e) { /* never stop a zombie from spawning over this */ }
    _apZombieDepth++;
    try {
      return _origGetZombieEnum.apply(this, args);
    } finally {
      _apZombieDepth--;
    }
  };
  Z._ap_hooked_zombies = true;
}

function syncZombieConfig() {
  window._AP_shuffleZombies = !!st.shuffleZombies;
  window._AP_zombieSeed     = st.zombieSeed || 0;
  window._AP_zombieTiers    = st.zombieTiers || {};
  // Absent on a seed generated before the per-level budget guard existed.
  // Null rather than {} on purpose: the guard reads a missing table as "do
  // not weigh anything" and takes its first roll, which is exactly what
  // those seeds always did.
  window._AP_zombieHp       = (st.zombieHp && Object.keys(st.zombieHp).length)
                              ? st.zombieHp : null;
  const tierOf = {};
  for (const tier of Object.keys(window._AP_zombieTiers)) {
    for (const cn of window._AP_zombieTiers[tier]) tierOf[cn] = tier;
  }
  window._AP_zombieTierOf = tierOf;
}

// Stands in for the game's static zombie class. Records what the original
// resolver was finally called with, which is the only thing the hook changes.
function makeZombiesClass() {
  const calls = [];
  return {
    calls,
    getZombieEnumWithPropByZombieTypes: function (type) {
      calls.push(type);
      return { z: type, prop: {} };
    },
  };
}

// modules: the objclasses the level carries, as readLevelJson would leave them
// on levelController.component.currentLevelObjects. waves: the level's own
// zombie roster, written the way a SpawnZombiesJitteredWaveActionProps writes
// it, so the plan sees what the level will actually field. Defaults to one
// ordinary module with no waves, which is a level that names no zombies of its
// own -- every codename then resolves down the lazy path.
function setLevel(id, modules, waves) {
  const objs = (modules || ['WaveManagerProperties'])
    .map(c => ({ objclass: c, objdata: {} }));
  if (waves) {
    const list = [];
    for (const z of Object.keys(waves)) {
      for (let i = 0; i < waves[z]; i++) list.push({ Type: `RTID(${z}@ZombieTypes)` });
    }
    objs.push({ objclass: 'SpawnZombiesJitteredWaveActionProps',
                objdata: { Zombies: list } });
  }
  window._AP_levelController = {
    thisLevelsID: id ? [id] : [],
    component: { currentLevelObjects: objs },
  };
  // A new object list is a new level as far as the plan is concerned, which is
  // the whole point of keying on it.
  return objs;
}

module.exports = {
  window, st, TEST_TIERS, TEST_HP,
  syncZombieConfig, installZombieHook, makeZombiesClass, setLevel,
  resetCache: function () { _apZombiePlan = null; },
};
