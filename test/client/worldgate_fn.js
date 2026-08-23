// Harness for the progressive world unlocks: the gate that stops a level being
// STARTED before its unlock has arrived. See drift_test.py: the functions below
// the dashed line are verbatim copies from build_pvzge_ap.py; everything above
// it stands in for the live client.
const window = {};
let st = {};
let levelGates = {};
let unlockWorldOf = {};

// The real client's location-name -> game-level-id map, trimmed to the names
// these cases use. eighties* on purpose: Neon Mixtape Tour's AP locations are
// neon*, and the game level ids are not, which is exactly the translation
// rebuildLevelGates has to do.
const LOC_LEVELS = {
  egypt1: 'egypt1', egypt8: 'egypt8', egypt9: 'egypt9', egypt25: 'egypt25',
  egypt26: 'egypt26', egypt35: 'egypt35',
  egypt_dangerroom: 'egypt_dangerroom',
  neon17: 'eighties17', neon33: 'eighties33',
  // A shop card: in the location list, but not a level. Its slot_data entry
  // must not become a gate on `undefined`.
  'Shop: chomper': undefined,
};

const toasts = [], logs = [];

// ── copied verbatim from build_pvzge_ap.py ───────────────────────────────────
function rebuildLevelGates(){
  const gates = st.worldGates || {};
  const out = {}, items = {};
  for(const world of Object.keys(gates)){
    const g = gates[world] || {};
    const stretches = g.stretches || [];
    for(let i = 0; i < stretches.length; i++){
      for(const locName of (stretches[i] || [])){
        const level = LOC_LEVELS[locName];
        // A name with no level is a location that is not a level at all (a
        // shop card), or one this client is too old to know. Skipping it
        // leaves that level playable rather than locking something the
        // client cannot name.
        if(!level) continue;
        out[level] = { world: world, item: g.item, need: i + 1 };
      }
    }
    if(g.item) items[g.item] = world;
  }
  levelGates = out;
  unlockWorldOf = items;
  return out;
}

function unlocksHeld(item){
  return (st.worldUnlocks && st.worldUnlocks[item]) || 0;
}

function levelBlockedBy(level){
  const gate = levelGates[level];
  if(!gate) return null;
  const have = unlocksHeld(gate.item);
  if(have >= gate.need) return null;
  return { world: gate.world, item: gate.item, need: gate.need, have: have };
}

function installLevelGateHook(KL) {
  if (!KL || KL._ap_hooked_levelgate || typeof KL.goToLevel !== 'function') return;
  const orig = KL.goToLevel;
  KL.goToLevel = function (levels) {
    const ask = window._AP_levelBlockedBy;
    if (ask) {
      const list = Array.isArray(levels) ? levels : (levels ? [levels] : []);
      for (const lvl of list) {
        const why = ask(lvl);
        if (why) {
          if (window._AP_reportLevelBlocked) window._AP_reportLevelBlocked(why);
          // Go to the world map rather than just resolving. Callers await
          // this AFTER running darken(), and several of them (the
          // next-level button, resume-into-forceLevel) have already torn the
          // current scene down -- resolving without loading anything leaves
          // a black screen with no way out. The world map is the one
          // destination that is always valid, and it is what the same
          // callers fall back to when there is no level to go to.
          return (typeof KL.GoToWorldmap === 'function')
            ? KL.GoToWorldmap() : Promise.resolve();
        }
      }
    }
    return orig.apply(this, arguments);
  };
  KL._ap_hooked_levelgate = true;
}

// ── harness controls ─────────────────────────────────────────────────────────
// Rebuilds module scope between cases. `state` is what slot_data and the
// received items would have left on st; omitting worldGates models a seed
// generated before the unlocks existed.
function reset(state){
  st = Object.assign({}, state || {});
  levelGates = {}; unlockWorldOf = {};
  toasts.length = 0; logs.length = 0;
  window._AP_levelBlockedBy = levelBlockedBy;
  window._AP_reportLevelBlocked = why => {
    toasts.push(why.world + ' ' + why.have + '/' + why.need);
    logs.push('Blocked: ' + why.world);
  };
  rebuildLevelGates();
}

// Stands in for the game's KeyListener. Records what actually reached the real
// goToLevel, which is the only thing that says whether a level started.
function makeKeyListener(opts){
  const started = [];
  const KL = { started: started, calls: 0, worldmaps: 0 };
  KL.GoToWorldmap = function(){ KL.worldmaps++; return Promise.resolve('worldmap'); };
  if (!(opts && opts.missing)) {
    KL.goToLevel = function (levels) {
      started.push(levels);
      KL.calls++;
      return Promise.resolve('started');
    };
  }
  return KL;
}

// A seed's worth of gates, in the shape fill_slot_data sends.
function gates(){
  return {
    'Ancient Egypt': {
      item: 'Progressive Ancient Egypt',
      stretches: [['egypt9', 'egypt25', 'egypt_dangerroom'], ['egypt26', 'egypt35']],
    },
    'Neon Mixtape Tour': {
      item: 'Progressive Neon Mixtape Tour',
      stretches: [['neon17', 'Shop: chomper'], ['neon33']],
    },
  };
}

module.exports = { rebuildLevelGates, unlocksHeld, levelBlockedBy,
                   installLevelGateHook, reset, makeKeyListener, gates,
                   toasts, logs, LOC_LEVELS, window,
                   worldOf: item => unlockWorldOf[item],
                   gateCount: () => Object.keys(levelGates).length };
