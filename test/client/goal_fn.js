// Harness for the win condition and Modern Day access. See drift_test.py: the
// functions below the dashed line are verbatim copies from build_pvzge_ap.py;
// everything above it stands in for the live client.
let st = {};
let conn = true, sessionActive = true, goalSent = false;

const sent = [], logs = [];
function send(pkts){ for(const p of pkts) sent.push(p); }
function log(m){ logs.push(String(m)); }
// Persisting st. Only that it is called matters here: the ledger has to reach
// localStorage or a reload would forget what was played.
let saves = 0;
function svSt(){ saves++; }
function toast(){}
// The merge calls the full save rebuild; only its level-progress step matters
// here, and that step IS a copy and is checked.
function rebuildAPSave(){ restoreLevelProgress(cp); }
// What the Connected packet left behind, and the DataPackage's id -> name map.
let serverCheckedIds = [], idToLoc = {};
function setServerChecked(names){
  idToLoc = {}; serverCheckedIds = [];
  names.forEach((n, i) => { idToLoc[100 + i] = n; serverCheckedIds.push(100 + i); });
}

// Every location this harness can name. The client's LOC_LEVELS is generated
// from constants.py; here a fixed handful is enough, and being a fixed list is
// what lets reset() model a client that has never heard of one of them.
const KNOWN_LOCS = ['egypt8', 'pirate8', 'cowboy8', 'dark10', 'modern16',
                    'egypt6', 'tutorial1'];

// ── copied verbatim from build_pvzge_ap.py ───────────────────────────────────
let _playedSet = null, _playedSrc = null, _playedLen = -1;
function playedList(){
  // Absent means state written by a client from before this ledger existed.
  // Seed it from st.checked: for a run already in progress those levels were
  // played, and it keeps the wiped-localStorage recovery in
  // mergeServerChecks() working exactly as it did. A new run starts [].
  if(!st.played) st.played = (st.checked || []).slice();
  return st.played;
}

function isPlayed(loc){
  const arr = playedList();
  if(_playedSrc !== arr || _playedLen !== arr.length){
    _playedSet = new Set(arr);
    _playedSrc = arr;
    _playedLen = arr.length;
  }
  return _playedSet.has(loc);
}

function recordPlayed(loc){
  if(isPlayed(loc)) return false;
  playedList().push(loc);
  svSt();
  return true;
}

function restoreLevelProgress(cp){
  if(!cp.levelProps) cp.levelProps = {};
  for(const lvl of new Set(Object.values(LOC_LEVELS))) delete cp.levelProps[lvl];
  for(const locName of playedList()) {
    const lvl = LOC_LEVELS[locName];
    if(lvl) cp.levelProps[lvl] = { progress: 3 };
  }
  return cp.levelProps;
}

function mergeServerChecks(){
  if(!serverCheckedIds.length) return;
  // Needs the DataPackage; Connected and DataPackage can arrive in either
  // order, so this is called from both and no-ops until the map exists.
  if(!idToLoc || !Object.keys(idToLoc).length) return;
  let added = 0;
  // A save with NO play history of its own is a run being resumed, not a run
  // in progress: wiped localStorage, a second machine, an AP state reset. The
  // server's list is then the only record that those levels were ever played,
  // so it is taken as one and the map progression comes back as it always
  // did. Once this save has played anything, server checks stop implying
  // play -- which is what stops /send_location handing out a goal world.
  const resuming = playedList().length === 0;
  // Local Set rather than isChecked(): this loop pushes as it goes, which
  // would invalidate the shared mirror on every iteration and rebuild it
  // each time. One Set built up front stays O(n + m).
  const known = new Set(st.checked);
  for(const id of serverCheckedIds){
    const name = idToLoc[id];
    if(name && !known.has(name)){
      st.checked.push(name); known.add(name); added++;
      if(resuming) st.played.push(name);
    }
  }
  serverCheckedIds = [];
  if(added){
    svSt();
    rebuildAPSave();
    log('Restored ' + added + ' check(s) from server');
    toast('↺ Restored ' + added + ' check(s)', '#4af');
  }
}

let _checkedSet = null, _checkedSrc = null, _checkedLen = -1;
function isChecked(loc){
  const arr = st.checked || [];
  if(_checkedSrc !== arr || _checkedLen !== arr.length){
    _checkedSet = new Set(arr);
    _checkedSrc = arr;
    _checkedLen = arr.length;
  }
  return _checkedSet.has(loc);
}

function victoryLoc(){ return st.victoryLoc || 'modern_zomboss_01_egypt'; }

// ── stubs, not copies ────────────────────────────────────────────────────────
// The live client maps AP location names to game level ids and reads level
// progress off the save. Here both are driven by the harness: st.levels is the
// set of level ids the player has actually beaten, which is the whole point of
// the distinction goalPlayed() draws.
// A real object rather than a Proxy: restoreLevelProgress() walks
// Object.values(LOC_LEVELS) to clear stale entries, and a Proxy with only a get
// trap answers that with [] -- the model would silently skip the clearing half.
// Names absent from it are the locations this "client" has no level for, which
// is how an old client meeting a new seed is modelled (st.unknownLocs).
let LOC_LEVELS = {};

// The save. cp.levelProps is the game's own record of what has been beaten, and
// is the only thing isFinished() reads -- exactly as in the live client, which
// is what makes "a check must not write here" a testable claim.
let cp = { levelProps: {} };

function isFinished(levelId){
  const e = cp.levelProps[levelId];
  return !!(e && (e.progress || 0) >= 3);
}

// The #ap-goal div. Only what updateGoalTracker writes.
let goalEl = { innerHTML: '', className: '', style: { display: '' } };



const MODERN_DAY_KEY_ITEM = 'Modern Day Key';

function unlocksHeld(item){
  return (st.worldUnlocks && st.worldUnlocks[item]) || 0;
}

function canAccessModernDay(){
  if(st.modernKeyed){
    // The first Progressive Modern Day opens it, and a Modern Day Key still
    // does on a seed that shipped one -- the key stopped being generated on
    // 2026-08-23 but a run started before then keeps working.
    const gate = (st.worldGates || {})['Modern Day'];
    if(gate && gate.item && unlocksHeld(gate.item) >= 1) return true;
    return (st.receivedKeys||[]).indexOf(MODERN_DAY_KEY_ITEM) >= 0;
  }
  const goalLocs  = st.goalLocs || [];
  const worldsReq = st.worldsReq || 7;
  if(!goalLocs.length) return false; // slot_data not in yet; don't open early
  const completed = goalLocs.filter(goalPlayed).length;
  return completed >= worldsReq;
}

const unknownGoalLocs = {};
function goalPlayed(loc){
  const levelId = LOC_LEVELS[loc];
  if(!levelId){
    if(!unknownGoalLocs[loc]){
      unknownGoalLocs[loc] = 1;
      log('Goal location "' + loc + '" is not a level this client knows; ' +
          'it can never count. Rebuild the client against the apworld ' +
          'this seed was rolled with.');
    }
    return false;
  }
  // The ledger is the persistent answer; isFinished() is the live one, for a
  // level beaten in this session before the poll has recorded it. Neither can
  // be forged by a check any more, now that rebuildAPSave() restores from
  // st.played.
  return isPlayed(loc) || isFinished(levelId);
}

function goalProgress(){
  const goalLocs  = st.goalLocs || [];
  const worldsReq = st.worldsReq || 0;
  let done = 0;
  for(const l of goalLocs) if(goalPlayed(l)) done++;
  return { done: done, need: worldsReq, total: goalLocs.length };
}

function goalMet(){
  const goalLocs  = st.goalLocs || [];
  const worldsReq = st.worldsReq || 0;
  // Nothing to compare against until slot_data lands. Claiming the goal off
  // a default would end someone else's run for them.
  if(!goalLocs.length || !worldsReq) return false;
  return goalProgress().done >= worldsReq;
}

const GOAL_LABEL = {
  world_key:  'World Keys',
  zomboss:    'Zomboss Fights',
  completion: 'Worlds Cleared',
};

function updateGoalTracker(){
  if(!goalEl) return;
  const g = goalProgress();
  if(!g.total || !g.need){ goalEl.style.display='none'; return; }
  const label = GOAL_LABEL[st.goalType] || GOAL_LABEL.world_key;
  goalEl.style.display='block';
  goalEl.className = g.done >= g.need ? 'ap-goal-done' : '';
  goalEl.innerHTML = '<b>' + g.done + '/' + g.need + '</b> ' + label +
    '<span class="ap-goal-sub">' +
    (g.done >= g.need ? 'goal complete — ' : '') +
    g.total + ' available</span>';
}

function maybeSendGoal(){
  if(goalSent || !conn || !sessionActive) return false;
  if(!(st.modernKeyed ? goalMet() : isChecked(victoryLoc()))) return false;
  send([{cmd:'StatusUpdate',status:30}]);
  goalSent = true;
  log('Goal complete: reported to the multiworld');
  return true;
}

// ── harness controls ─────────────────────────────────────────────────────────
// Rebuilds module scope between cases. `state` is what slot_data would have
// left on st; omitting modernKeyed models a seed rolled before that flag.
function reset(state, opts){
  const o = opts || {};
  st = Object.assign({ checked: [], played: [] }, state || {});
  // Every location the harness may name, minus the ones this client is meant
  // not to know. KNOWN_LOCS is fixed rather than derived from goalLocs so a
  // non-goal level can still be played.
  LOC_LEVELS = {};
  const unknown = new Set(st.unknownLocs || []);
  for(const n of KNOWN_LOCS) if(!unknown.has(n)) LOC_LEVELS[n] = 'lvl:' + n;
  cp = { levelProps: {} };
  serverCheckedIds = []; idToLoc = {};
  _playedSet = null; _playedSrc = null; _playedLen = -1;
  conn = o.conn !== false;
  sessionActive = o.sessionActive !== false;
  goalSent = false;
  // isChecked caches on the identity AND length of st.checked, so the cache
  // has to be dropped with the state it was built from.
  _checkedSet = null; _checkedSrc = null; _checkedLen = -1;
  sent.length = 0; logs.length = 0;
  // The warn-once ledger is module scope in the real client too, so it has to
  // be emptied with everything else or case two sees case one's warning.
  for(const k of Object.keys(unknownGoalLocs)) delete unknownGoalLocs[k];
  goalEl = { innerHTML: '', className: '', style: { display: '' } };
}

// A check arriving from ANYWHERE -- fireCheck, /send_location, a release, the
// mergeServerChecks() reconnect merge. It touches st.checked and nothing else,
// which is the whole claim under test.
function check(loc){ st.checked.push(loc); }

// Beating the level in game: the GAME writes the save, not the client.
function play(loc){
  const lvl = LOC_LEVELS[loc];
  if(lvl) cp.levelProps[lvl] = { progress: 3 };
}

// One poll tick, in the client's order: observe what the save says was beaten,
// THEN rebuild the save from the ledger. The order is load-bearing -- rebuild
// first and the game's own write is erased before it is ever seen.
function poll(){
  for(const loc of Object.keys(LOC_LEVELS)){
    if(isFinished(LOC_LEVELS[loc])) recordPlayed(loc);
  }
  restoreLevelProgress(cp);
}

module.exports = { canAccessModernDay, goalMet, goalProgress, goalPlayed,
                   restoreLevelProgress, isPlayed, recordPlayed, poll,
                   levelProps: () => cp.levelProps, saves: () => saves,
                   mergeServerChecks, setServerChecked,
                   updateGoalTracker, goalEl: () => goalEl,
                   maybeSendGoal, victoryLoc,
                   isChecked, reset, check, play, sent, logs,
                   state: () => st,
                   disconnect: () => { conn = false; },
                   reconnect: () => { conn = true; },
                   sentGoal: () => goalSent };
