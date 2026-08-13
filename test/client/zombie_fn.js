// Copies of the zombie-shuffle functions from build_pvzge_ap.py, kept in sync
// by drift_test.py. Do not edit the copied functions here -- edit the client
// and re-copy. Everything above and below them is harness scaffolding.
const window = {};
const st = {};

// Module-level state the copied functions close over, declared here for the
// same reason: it lives outside any function, so drift_test does not see it.
let _apZombieCacheKey = null;
let _apZombieCache = {};
let _apZombieDepth = 0;

// The tier table generation ships and sends in slot_data. Trimmed to the
// shapes the tests exercise: a big land tier, a Gargantuar-only tier, the two
// threat tiers whose whole point is that they cannot leak into another tier,
// and a single-member tier that must never swap.
const TEST_TIERS = {
  't1-land': ['mummy', 'cowboy', 'pirate', 'future', 'dark', 'iceage',
              'lostcity', 'eighties', 'dino', 'sky', 'beach', 'kongfu'],
  't3-land-jester': ['birthday_juggler', 'dark_juggler', 'foodfight_chefster'],
  't3-land-iceblock': ['iceage_troglobite', 'iceage_troglobite_1block',
                       'iceage_troglobite_2block', 'birthday_troglobite'],
  't5-water-garg': ['dark_gargantuar', 'egypt_gargantuar', 'future_gargantuar'],
  't1-water': ['beach_snorkel'],
};

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

function _apLevelKey() {
  try {
    const ids = window._AP_levelController && window._AP_levelController.thisLevelsID;
    if (ids && ids.length) return ids.join(',');
  } catch (e) { /* fall through to the shared key */ }
  // Levels with no ID -- local test levels, Level of the Day -- share one
  // key. They still roll deterministically, just not per level.
  return '';
}

const _AP_RTID = /^RTID\(([^@()]+)@([^()]*)\)$/;

const AP_BESPOKE_MODULES = /Minigame|Beghouled|Rhythm/;
let _apZombieBespoke = false;

function _apLevelIsBespoke() {
  try {
    const lc = window._AP_levelController;
    const objs = lc && lc.component && lc.component.currentLevelObjects;
    // Fails CLOSED: if the level's object list cannot be read, assume it is
    // bespoke and do not shuffle. currentLevelObjects is filled in by
    // readLevelJson before any zombie is resolved, so an unreadable one
    // means something has moved -- and a level that does not shuffle is a
    // far cheaper mistake than one that cannot be beaten.
    if (!Array.isArray(objs) || !objs.length) return true;
    for (const o of objs) {
      if (o && AP_BESPOKE_MODULES.test(o.objclass || '')) return true;
    }
  } catch (e) { return true; }
  return false;
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
  const levelKey = _apLevelKey();
  // Cache per level: this runs on every spawn, and the answer cannot change
  // within a level. Dropped wholesale when the level changes rather than
  // grown forever. Keyed by CODENAME, so the same zombie resolves the same
  // way whether the caller named it bare or as an RTID -- the level's zombie
  // preview cards and its actual spawns come through both ways.
  if (_apZombieCacheKey !== levelKey) {
    _apZombieCacheKey = levelKey;
    _apZombieCache = {};
    // Worked out once per level, not once per spawn: it walks the level's
    // whole object list.
    _apZombieBespoke = _apLevelIsBespoke();
  }
  if (_apZombieBespoke) return type;
  let pick = _apZombieCache[codename];
  if (pick === undefined) {
    const rnd = _apRng(_apHash(String(window._AP_zombieSeed || 0) + '|' +
                               levelKey + '|' + codename));
    pick = pool[Math.floor(rnd() * pool.length)];
    _apZombieCache[codename] = pick;
  }
  // Always re-wrapped as @ZombieTypes rather than the scope it arrived in.
  // Every codename in the tier table is an alias in the game's global
  // ZombieTypes table, so that scope always resolves; a level that defines
  // its own type (RTID(x@CurrentLevel), 69 of those) has no entry for the
  // replacement under its local scope and would resolve to nothing.
  return wrapped ? 'RTID(' + pick + '@ZombieTypes)' : pick;
}

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
// on levelController.component.currentLevelObjects. Defaults to one ordinary
// module so a plain level is not mistaken for an unreadable one.
function setLevel(id, modules) {
  window._AP_levelController = {
    thisLevelsID: id ? [id] : [],
    component: {
      currentLevelObjects: (modules || ['WaveManagerProperties'])
        .map(c => ({ objclass: c })),
    },
  };
}

module.exports = {
  window, st, TEST_TIERS,
  syncZombieConfig, installZombieHook, makeZombiesClass, setLevel,
  resetCache: function () { _apZombieCacheKey = null; _apZombieCache = {}; },
};
