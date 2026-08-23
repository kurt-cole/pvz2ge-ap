// Harness for the win condition and Modern Day access. See drift_test.py: the
// functions below the dashed line are verbatim copies from build_pvzge_ap.py;
// everything above it stands in for the live client.
let st = {};
let conn = true, sessionActive = true, goalSent = false;

const sent = [], logs = [];
function send(pkts){ for(const p of pkts) sent.push(p); }
function log(m){ logs.push(String(m)); }

// ── copied verbatim from build_pvzge_ap.py ───────────────────────────────────
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

const MODERN_DAY_KEY_ITEM = 'Modern Day Key';

function canAccessModernDay(){
  if(st.modernKeyed)
    return (st.receivedKeys||[]).indexOf(MODERN_DAY_KEY_ITEM) >= 0;
  const goalLocs  = st.goalLocs || [];
  const worldsReq = st.worldsReq || 7;
  if(!goalLocs.length) return false; // slot_data not in yet; don't open early
  const completed = goalLocs.filter(l=>isChecked(l)).length;
  return completed >= worldsReq;
}

function goalMet(){
  const goalLocs  = st.goalLocs || [];
  const worldsReq = st.worldsReq || 0;
  // Nothing to compare against until slot_data lands. Claiming the goal off
  // a default would end someone else's run for them.
  if(!goalLocs.length || !worldsReq) return false;
  let done = 0;
  for(const l of goalLocs) if(isChecked(l)) done++;
  return done >= worldsReq;
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
  st = Object.assign({ checked: [] }, state || {});
  conn = o.conn !== false;
  sessionActive = o.sessionActive !== false;
  goalSent = false;
  // isChecked caches on the identity AND length of st.checked, so the cache
  // has to be dropped with the state it was built from.
  _checkedSet = null; _checkedSrc = null; _checkedLen = -1;
  sent.length = 0; logs.length = 0;
}

// Records a check the way fireCheck does, so the cache invalidation is
// exercised rather than bypassed.
function check(loc){ st.checked.push(loc); }

module.exports = { canAccessModernDay, goalMet, maybeSendGoal, victoryLoc,
                   isChecked, reset, check, sent, logs,
                   state: () => st,
                   disconnect: () => { conn = false; },
                   reconnect: () => { conn = true; },
                   sentGoal: () => goalSent };
