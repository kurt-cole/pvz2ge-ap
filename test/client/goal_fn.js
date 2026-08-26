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

// ── stubs, not copies ────────────────────────────────────────────────────────
// The live client maps AP location names to game level ids and reads level
// progress off the save. Here both are driven by the harness: st.levels is the
// set of level ids the player has actually beaten, which is the whole point of
// the distinction goalPlayed() draws.
// st.unknownLocs names the locations this "client" has no level for, which is
// how an old client meeting a new seed is modelled.
const LOC_LEVELS = new Proxy({}, { get: (_, k) =>
  ((st.unknownLocs || []).indexOf(String(k)) >= 0 ? undefined
                                                  : 'lvl:' + String(k)) });
function isFinished(levelId){ return (st.levels || []).indexOf(levelId) >= 0; }

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
  return isFinished(levelId);
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
  st = Object.assign({ checked: [], levels: [] }, state || {});
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

// Records a check the way fireCheck does, so the cache invalidation is
// exercised rather than bypassed.
function check(loc){ st.checked.push(loc); }

// Beating a level in game, which is what goalPlayed() actually asks about.
function play(loc){ (st.levels = st.levels || []).push(LOC_LEVELS[loc]); }

module.exports = { canAccessModernDay, goalMet, goalProgress, goalPlayed,
                   updateGoalTracker, goalEl: () => goalEl,
                   maybeSendGoal, victoryLoc,
                   isChecked, reset, check, play, sent, logs,
                   state: () => st,
                   disconnect: () => { conn = false; },
                   reconnect: () => { conn = true; },
                   sentGoal: () => goalSent };
