// Drives the REAL costume logic lifted out of build_pvzge_ap.py.
const M = require('./costume_fn.js');
const { grantRandomCostume, applyPendingCostumes, setSt, getSt, window, PLANT_COSTUMES } = M;

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);

const fresh = (over = {}) => {
  setSt(Object.assign({ costumes: {}, pendingCostumes: 0 }, over));
  return getSt();
};
const total = st => Object.values(st.costumes).reduce((a, v) => a + v.length, 0);

// ── nothing owned: must not invent a costume ────────────────────────────────
fresh();
window._AP_grantedPlantIds = new Set();
if (grantRandomCostume() !== false) fail('granted a costume with no plants owned');
else ok('no plants owned -> no costume granted');

// ── a plant with no costumes at all ─────────────────────────────────────────
const noCostume = Object.keys(M.ID_TO_CN).map(Number).find(id => !PLANT_COSTUMES[id]);
fresh();
window._AP_grantedPlantIds = new Set([noCostume]);
if (grantRandomCostume() !== false) fail(`granted a costume for plant ${noCostume}, which has none`);
else ok(`plant ${noCostume} has no costumes -> nothing granted`);

// ── one plant, grant up to its limit then stop ──────────────────────────────
const pid = 0, cap = PLANT_COSTUMES[0];           // peashooter, 10
let st = fresh();
window._AP_grantedPlantIds = new Set([pid]);
let n = 0;
while (grantRandomCostume()) n++;
if (n !== cap) fail(`granted ${n} costumes for a plant with ${cap}`);
else ok(`granted exactly ${cap} costumes for plant ${pid}, then stopped`);
const owned = getSt().costumes[pid];
if (new Set(owned).size !== owned.length) fail('granted a duplicate costume');
else ok('no duplicate costume for the same plant');
if (owned.some(i => i < 0 || i >= cap)) fail('costume index out of range');
else ok('every costume index is within 0..count-1');

// ── banking: received before any plant is owned ─────────────────────────────
st = fresh({ pendingCostumes: 3 });
window._AP_grantedPlantIds = new Set();
applyPendingCostumes();
if (getSt().pendingCostumes !== 3) fail('pending costumes lost when nothing could be granted');
else ok('3 costumes banked while no plant is owned');
window._AP_grantedPlantIds = new Set([0]);
applyPendingCostumes();
if (getSt().pendingCostumes !== 0) fail(`bank not drained: ${getSt().pendingCostumes} left`);
else if (total(getSt()) !== 3) fail(`drained bank granted ${total(getSt())} costumes, expected 3`);
else ok('bank drains to 3 costumes once a plant is owned');

// ── over-banking past what is available ─────────────────────────────────────
st = fresh({ pendingCostumes: 50 });
window._AP_grantedPlantIds = new Set([0]);          // only 10 costumes exist
applyPendingCostumes();
if (total(getSt()) !== cap) fail(`granted ${total(getSt())} of a possible ${cap}`);
else if (getSt().pendingCostumes !== 50 - cap) fail(`bank should hold the remaining ${50 - cap}`);
else ok(`50 banked against ${cap} available: granted ${cap}, kept ${50 - cap} for later plants`);
// a new plant arriving must let the bank keep draining
window._AP_grantedPlantIds = new Set([0, 1]);
applyPendingCostumes();
if (total(getSt()) !== cap + PLANT_COSTUMES[1]) fail('bank did not resume on a new plant');
else ok(`a second plant resumed the bank (+${PLANT_COSTUMES[1]})`);

// ── spread across many plants ───────────────────────────────────────────────
st = fresh();
const many = Object.keys(PLANT_COSTUMES).slice(0, 20).map(Number);
window._AP_grantedPlantIds = new Set(many);
for (let i = 0; i < 40; i++) grantRandomCostume();
const touched = Object.keys(getSt().costumes).length;
if (touched < 5) fail(`40 costumes landed on only ${touched} plants -- not spread`);
else ok(`40 costumes spread over ${touched} of ${many.length} owned plants`);
for (const [p, list] of Object.entries(getSt().costumes)) {
  if (list.length > PLANT_COSTUMES[p]) fail(`plant ${p} over its ${PLANT_COSTUMES[p]} costume cap`);
}
ok('no plant exceeded its costume count');

// ── Costume Shuffle Trap ────────────────────────────────────────────────────
const { shuffleCostumes, wornCostume } = M;

// nothing owned -> nothing to scramble, and it must say so rather than throw
fresh();
window._AP_grantedPlantIds = new Set();
if (shuffleCostumes() !== false) fail('shuffle claimed success with no costumes owned');
else ok('trap with no costumes owned reports nothing to scramble');

// build a real collection first
st = fresh();
const pids = Object.keys(PLANT_COSTUMES).slice(0, 25).map(Number);
window._AP_grantedPlantIds = new Set(pids);
for (let i = 0; i < 60; i++) grantRandomCostume();
const before = JSON.parse(JSON.stringify(getSt().costumes));
const ownedTotal = total(getSt());

// the trap must never take a costume away
let everMoved = 0;
for (let run = 0; run < 30; run++) {
  shuffleCostumes();
  if (total(getSt()) !== ownedTotal) { fail('shuffle changed how many costumes are owned'); break; }
  if (JSON.stringify(getSt().costumes) !== JSON.stringify(before)) { fail('shuffle mutated the collection'); break; }
  for (const [pid, list] of Object.entries(getSt().costumes)) {
    const w = wornCostume(pid);
    if (w !== -1 && list.indexOf(w) < 0) { fail(`plant ${pid} wearing costume ${w} it does not own`); break; }
  }
  const worn = Object.keys(getSt().wornCostume).length;
  if (worn) everMoved++;
}
ok(`30 shuffles: collection of ${ownedTotal} costumes across ${Object.keys(before).length} plants never changed`);
ok('every plant only ever wears a costume it owns, or none');

// it actually scrambles: worn set should differ across runs
const snaps = new Set();
for (let i = 0; i < 12; i++) { shuffleCostumes(); snaps.add(JSON.stringify(getSt().wornCostume)); }
if (snaps.size < 2) fail('12 shuffles produced an identical outfit every time');
else ok(`12 shuffles produced ${snaps.size} distinct outfits`);

// "none" is reachable, and so is putting one back on
let sawNone = false, sawWorn = false;
for (let i = 0; i < 40; i++) {
  shuffleCostumes();
  for (const pid of Object.keys(getSt().costumes)) {
    if (wornCostume(pid) === -1) sawNone = true; else sawWorn = true;
  }
}
if (!sawNone) fail('the trap can never take a costume off');
else if (!sawWorn) fail('the trap can never leave one on');
else ok('the trap both removes and re-applies costumes');

// a granted costume after a shuffle is still wearable
const pidA = Number(Object.keys(getSt().costumes)[0]);
getSt().wornCostume[pidA] = -1;
if (wornCostume(pidA) !== -1) fail('an explicit "wear none" was ignored');
else ok('"wear none" survives as a real choice, not treated as unset');
delete getSt().wornCostume[pidA];
if (wornCostume(pidA) !== getSt().costumes[pidA].slice(-1)[0]) fail('unset should wear the most recent');
else ok('unset falls back to the most recently granted costume');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCOSTUME + TRAP LOGIC OK');
process.exit(failed ? 1 : 0);
