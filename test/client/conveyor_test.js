// Drives the REAL installConveyorHook() from build_pvzge_ap.py against level
// data pulled out of the shipped game, through a stand-in levelController.
const fs = require('fs');
const { installConveyorHook, window } = require('./conveyor_fn.js');

const path = require('path');
const LEVELS = JSON.parse(fs.readFileSync(path.join(__dirname, 'conveyor_levels.json'), 'utf8'));

let seen = [];
function LC() {}
LC.prototype.module_SetConveyor = function (props) { seen.push(props); };
installConveyorHook(LC);
const lc = new LC();

// installConveyorHook must be idempotent: the module can register more than once.
installConveyorHook(LC);

function run(props) { seen = []; lc.module_SetConveyor(props); return seen[0]; }
const clone = o => JSON.parse(JSON.stringify(o));

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);

window._AP_conveyorSeed = 123456789;

// ── off by default ───────────────────────────────────────────────────────────
window._AP_randomizeConveyor = false;
for (const lvl of LEVELS) {
  const before = clone(lvl.InitialPlantList);
  const got = run(clone(lvl));
  if (JSON.stringify(got.InitialPlantList) !== JSON.stringify(before)) {
    fail('option off must not change ' + lvl._file); break;
  }
}
if (!failed) ok('option off leaves every level untouched (' + LEVELS.length + ' levels)');

// ── on ───────────────────────────────────────────────────────────────────────
window._AP_randomizeConveyor = true;
const KNOWN = window._AP_conveyorKnown;
let swapped = 0, preserved = 0, toolsKept = 0, mutated = 0;

for (const lvl of LEVELS) {
  const original = clone(lvl);
  const input = clone(lvl);
  const got = run(input);

  // the level's own properties object must not be written to
  if (JSON.stringify(input.InitialPlantList) !== JSON.stringify(original.InitialPlantList)) mutated++;

  const a = original.InitialPlantList, b = got.InitialPlantList;
  if (a.length !== b.length) { fail(lvl._file + ': entry count changed'); continue; }

  for (let i = 0; i < a.length; i++) {
    // pacing fields must survive untouched
    for (const k of ['MinCount', 'MaxCount', 'Weight', 'MinWeightFactor', 'MaxWeightFactor']) {
      if (JSON.stringify(a[i][k]) !== JSON.stringify(b[i][k])) {
        fail(`${lvl._file}[${i}]: ${k} changed ${a[i][k]} -> ${b[i][k]}`);
      }
    }
    if (KNOWN.has(a[i].PlantType)) {
      swapped++;
      if (!KNOWN.has(b[i].PlantType)) fail(`${lvl._file}[${i}]: swapped in unknown ${b[i].PlantType}`);
    } else {
      // tools / projectiles / powertiles / potions must be left exactly alone
      toolsKept++;
      if (a[i].PlantType !== b[i].PlantType) {
        fail(`${lvl._file}[${i}]: non-plant ${a[i].PlantType} became ${b[i].PlantType}`);
      }
    }
  }
  preserved++;
}
if (mutated) fail(mutated + ' level(s) had their source properties mutated');
else ok('source level properties never mutated');
ok(`${preserved} levels processed: ${swapped} plant entries swapped, ${toolsKept} non-plant entries preserved`);

// ── determinism ──────────────────────────────────────────────────────────────
const lvl = LEVELS.find(l => l.InitialPlantList.filter(e => KNOWN.has(e.PlantType)).length >= 3);
const r1 = run(clone(lvl)).InitialPlantList.map(e => e.PlantType).join(',');
const r2 = run(clone(lvl)).InitialPlantList.map(e => e.PlantType).join(',');
const r3 = run(clone(lvl)).InitialPlantList.map(e => e.PlantType).join(',');
if (r1 !== r2 || r2 !== r3) fail('retrying a level rerolled: ' + r1 + ' vs ' + r2 + ' vs ' + r3);
else ok('same level rolls identically on retry  [' + r1 + ']');

// different slot seed -> different belt
window._AP_conveyorSeed = 987654321;
const other = run(clone(lvl)).InitialPlantList.map(e => e.PlantType).join(',');
if (other === r1) fail('a different conveyor_seed produced the same belt');
else ok('different slot seed gives a different belt  [' + other + ']');
window._AP_conveyorSeed = 123456789;

// different levels -> different belts (not all levels collapsing to one roll)
const rolls = new Set(LEVELS.slice(0, 40).map(l => run(clone(l)).InitialPlantList.map(e => e.PlantType).join(',')));
if (rolls.size < 20) fail('rolls not varying across levels: only ' + rolls.size + ' distinct in 40');
else ok('rolls vary across levels (' + rolls.size + ' distinct in 40)');

// ── duplicate avoidance ──────────────────────────────────────────────────────
let dupLevels = 0, multiPlant = 0;
for (const l of LEVELS) {
  const plants = l.InitialPlantList.filter(e => KNOWN.has(e.PlantType));
  if (plants.length < 2) continue;
  multiPlant++;
  const out = run(clone(l)).InitialPlantList.filter(e => KNOWN.has(e.PlantType)).map(e => e.PlantType);
  if (new Set(out).size !== out.length) dupLevels++;
}
ok(`duplicate plants on a belt: ${dupLevels}/${multiPlant} multi-plant levels`);

// ── edge cases ───────────────────────────────────────────────────────────────
if (run({ InitialPlantList: [] }).InitialPlantList.length !== 0) fail('empty list');
else ok('empty InitialPlantList handled');
run({});                                  ok('missing InitialPlantList handled');
run(null);                                ok('null props handled');
run({ InitialPlantList: [null, { PlantType: 'peashooter' }] }); ok('null entry handled');
const noPool = window._AP_conveyorPool; window._AP_conveyorPool = [];
const untouched = run(clone(lvl));
if (untouched.InitialPlantList[0].PlantType !== lvl.InitialPlantList[0].PlantType) fail('empty pool must no-op');
else ok('empty pool leaves the level alone');
window._AP_conveyorPool = noPool;

// ── swaps stay inside the plant's own power band ─────────────────────────────
const { CONVEYOR_GROUPS } = require('./conveyor_fn.js');
const GROUP_OF = {};
for (const k of Object.keys(CONVEYOR_GROUPS)) for (const cn of CONVEYOR_GROUPS[k]) GROUP_OF[cn] = k;

let crossings = 0, sameGroup = 0, ungrouped = 0, roleBreaks = 0;
const roleOf = k => k.split(':')[0];
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList;
  const after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < before.length; i++) {
    const a = before[i].PlantType, b = after[i].PlantType;
    if (!KNOWN.has(a)) continue;
    if (!GROUP_OF[a]) {
      // no comparable plant to trade for: must be left exactly as it was
      ungrouped++;
      if (a !== b) fail(`ungrouped ${a} was swapped to ${b}`);
      continue;
    }
    if (GROUP_OF[a] === GROUP_OF[b]) sameGroup++;
    else { crossings++; if (roleOf(GROUP_OF[a]) !== roleOf(GROUP_OF[b] || '')) roleBreaks++; }
  }
}
if (crossings) fail(`${crossings} swap(s) left the original's group (${roleBreaks} changed role)`);
else ok(`all ${sameGroup} swaps stayed inside the original's power band`);
ok(`${ungrouped} entries had no comparable plant and were left alone`);

// spot-check the two constraints that matter most for a level being winnable
const sunCns = CONVEYOR_GROUPS['sun:budget'].concat(CONVEYOR_GROUPS['sun:low']);
let sunChecked = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < before.length; i++) {
    if (!sunCns.includes(before[i].PlantType)) continue;
    sunChecked++;
    if (!GROUP_OF[after[i].PlantType] || roleOf(GROUP_OF[after[i].PlantType]) !== 'sun') {
      fail(`sun producer ${before[i].PlantType} became ${after[i].PlantType}`);
    }
  }
}
ok(`${sunChecked} sun-producer entries stayed sun producers`);

let oneShot = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < before.length; i++) {
    const g = GROUP_OF[before[i].PlantType];
    if (!g || roleOf(g) !== 'single-use') continue;
    oneShot++;
    if (roleOf(GROUP_OF[after[i].PlantType] || '') !== 'single-use') {
      fail(`one-shot ${before[i].PlantType} became ${after[i].PlantType}`);
    }
  }
}
ok(`${oneShot} one-shot entries stayed one-shots`);

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCONVEYOR HOOK OK');
process.exit(failed ? 1 : 0);
