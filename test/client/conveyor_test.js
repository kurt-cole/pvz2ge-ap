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
// Sun costs, read from the game's own PlantProperties export used to build the
// groups. Literal here on purpose: deriving them from CONVEYOR_GROUPS would be
// checking the table against itself.
const COST_OF = require('./conveyor_costs.json');

const { CONVEYOR_SHADOW, CONVEYOR_BELT_LOCKED } = require('./conveyor_fn.js');
const SHADOW = new Set(CONVEYOR_SHADOW);
// A shadow belt is a whole-belt reroll, not a per-slot swap, so it is exempt
// from the group rule by design -- it is checked on its own terms below. A
// level counts as one only if EVERY swappable slot came out a shadow plant;
// anything less would mean the two paths had mixed, which must never happen.
// Read from the hook's own stamp rather than inferred from the belt: a
// one-slot belt whose plant happens to swap to a Shadow plant looks exactly
// like a shadow deck, which made this detector report 5 false positives and
// two failures that were the test's fault, not the client's.
const lastWasShadow = () => window._AP_conveyorLastShadow === true;
// How many slots the hook would consider swappable, for the min-slots rule.
const slotCountOf = (before) => {
  let slots = 0;
  for (let i = 0; i < before.length; i++) {
    const a = before[i] && before[i].PlantType;
    if (!KNOWN.has(a) || !GROUP_OF[a] || CONVEYOR_BELT_LOCKED.has(a) ||
        window._AP_conveyorTerrainLocked.has(a)) continue;
    slots++;
  }
  return slots;
};

let crossings = 0, sameGroup = 0, ungrouped = 0, roleBreaks = 0;
let shadowBelts = 0, shadowNoMoon = 0, shadowLevels = [];
const roleOf = k => k.split(':')[0];
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList;
  const after = run(clone(l)).InitialPlantList;
  if (lastWasShadow()) {
    shadowBelts++;
    shadowLevels.push({ picks: after.map(e => e.PlantType), slots: slotCountOf(before) });
    if (!after.some(e => e.PlantType === 'moonflower')) shadowNoMoon++;
    continue;
  }
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

// spot-check the constraint that matters most for a level being winnable: a
// plant that is used up must not become one that stays on the lawn, or the
// level's pacing is gone. Shadow belts are exempt for the reason above.
let oneShot = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  if (lastWasShadow()) continue;
  for (let i = 0; i < before.length; i++) {
    const g = GROUP_OF[before[i].PlantType];
    if (!g || roleOf(g) !== 'instant') continue;
    oneShot++;
    if (roleOf(GROUP_OF[after[i].PlantType] || '') !== 'instant') {
      fail(`one-shot ${before[i].PlantType} became ${after[i].PlantType}`);
    }
  }
}
ok(`${oneShot} one-shot entries stayed one-shots`);

// Moonflower is belt-locked: the three levels that put it on a belt are built
// around the Shadow plants it empowers, so it must never be traded away.
let moonSeen = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < before.length; i++) {
    if (before[i].PlantType !== 'moonflower') continue;
    moonSeen++;
    if (after[i].PlantType !== 'moonflower') {
      fail(`belt-locked moonflower became ${after[i].PlantType}`);
    }
  }
}
ok(`${moonSeen} moonflower entries were left exactly where the level put them`);

// ── every band is one scale ──────────────────────────────────────────────────
// The key must band on sun cost alone. It once banded by derived DPS where a
// plant had one and by sun cost otherwise, which put Nightshade (75 sun, 100
// derived dps) in with Banana and Gatling Pea at 500, and Winter Melon (500)
// in with Bonk Choy (150). Asserted as "no group spans more than a 4x sun
// spread", which those two both broke.
const SUN = { budget: [0, 50], low: [75, 125], mid: [150, 225], high: [250, 500] };
let bandBreaks = [];
for (const k of Object.keys(CONVEYOR_GROUPS)) {
  const band = k.split(':')[1];
  const want = SUN[band];
  if (!want) continue;
  for (const cn of CONVEYOR_GROUPS[k]) {
    const cost = COST_OF[cn];
    if (cost === undefined) continue;
    if (cost < want[0] || cost > want[1]) bandBreaks.push(`${cn} (${cost}) in ${k}`);
  }
}
if (bandBreaks.length) fail(`${bandBreaks.length} plant(s) outside their band's sun range: ${bandBreaks.slice(0,4)}`);
else ok('every group holds one sun-cost band and nothing else');

// ── step three: similar output ───────────────────────────────────────────────
// A preference like Family, and only for the 35 plants the tables can price.
// Checked as "a rated plant does not trade for one more than 2x away", which
// is what the filter promises, and only where the pool had a choice.
const { CONVEYOR_DPS, CONVEYOR_FAMILIES: FAMS } = require('./conveyor_fn.js');
const FAM_OF = {};
for (const f of Object.keys(FAMS)) for (const cn of FAMS[f]) FAM_OF[cn] = f;
let dpsChecked = 0, dpsFar = [];
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  if (lastWasShadow()) continue;
  for (let i = 0; i < before.length; i++) {
    const a = before[i].PlantType, b = after[i].PlantType;
    if (a === b || !CONVEYOR_DPS[a] || !CONVEYOR_DPS[b]) continue;
    const group = CONVEYOR_GROUPS[GROUP_OF[a]] || [];
    const isNear = cn => CONVEYOR_DPS[cn] && CONVEYOR_DPS[cn] >= CONVEYOR_DPS[a] / 2 &&
                                             CONVEYOR_DPS[cn] <= CONVEYOR_DPS[a] * 2;
    // Family outranks output, which is the order the option promises. So a
    // similar-output choice only has to exist in the pool step two actually
    // hands over -- and when the preference fires that pool is the Family kin.
    // Coconut Cannon is the case: the only other expensive Lobbers are Apple
    // Mortar and Melon-pult, neither within 2x of its 60 dps.
    const kin = group.filter(cn => FAM_OF[cn] === FAM_OF[a]);
    if (group.filter(isNear).length < 2) continue;      // no choice at all
    if (kin.length >= 2 && kin.filter(isNear).length < 2) continue;  // none among kin
    dpsChecked++;
    const ratio = CONVEYOR_DPS[b] / CONVEYOR_DPS[a];
    if (ratio > 2 || ratio < 0.5) dpsFar.push(`${a}(${CONVEYOR_DPS[a]}) -> ${b}(${CONVEYOR_DPS[b]})`);
  }
}
if (!dpsChecked) fail('no rated swap had a similar-output choice, so step three is untested');
else if (dpsFar.length) fail(`${dpsFar.length}/${dpsChecked} rated swaps ignored similar output: ${dpsFar.slice(0,3)}`);
else ok(`all ${dpsChecked} rated swaps with a choice landed within 2x of the original's dps`);

// ── the shadow belt ──────────────────────────────────────────────────────────
// It has to fire sometimes, never without Moonflower, and never on a belt too
// small to be a deck. "Sometimes" is checked as a range: zero would mean the
// roll is dead, and everything would mean it had swallowed the normal path.
if (!shadowBelts) fail('the shadow belt never fired across ' + LEVELS.length + ' levels');
else if (shadowBelts > LEVELS.length * 0.30) {
  fail(`the shadow belt fired on ${shadowBelts}/${LEVELS.length} levels, far past its 12% chance`);
} else ok(`shadow belt fired on ${shadowBelts}/${LEVELS.length} levels ` +
          `(${(shadowBelts / LEVELS.length * 100).toFixed(0)}%)`);
if (shadowNoMoon) fail(`${shadowNoMoon} shadow belt(s) came out without moonflower`);
else ok(`all ${shadowBelts} shadow belts contain moonflower`);
const tooSmall = shadowLevels.filter(r => r.slots < 2).length;
if (tooSmall) fail(`${tooSmall} shadow belt(s) fired on a belt with fewer than 2 slots`);
else ok('no shadow belt fired on a belt too small to be a deck');
const offSet = shadowLevels.flatMap(r => r.picks)
  .filter(p => !SHADOW.has(p) && KNOWN.has(p) && GROUP_OF[p]).length;
if (offSet) fail(`${offSet} plant(s) on a shadow belt are not in the shadow set`);
else ok('every plant on a shadow belt is one of the 8 haveDarkMode plants');

// ── Family preference ────────────────────────────────────────────────────────
// Step two of the three. It is a preference, not a filter, so this asserts it
// BITES rather than that it always holds: with 75% weighting a same-Family
// trade should be far more common than picking uniformly from the group would
// give. Measured against that uniform baseline, so it cannot pass by accident
// on a pool that happens to be family-heavy.
const { CONVEYOR_FAMILIES } = require('./conveyor_fn.js');
let famSame = 0, famTotal = 0, baseline = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  if (lastWasShadow()) continue;
  for (let i = 0; i < before.length; i++) {
    const a = before[i].PlantType, b = after[i].PlantType;
    if (!KNOWN.has(a) || !GROUP_OF[a] || a === b) continue;
    const group = CONVEYOR_GROUPS[GROUP_OF[a]];
    const kin = group.filter(cn => FAM_OF[cn] === FAM_OF[a]);
    if (kin.length < 2) continue;  // no partner: the preference cannot apply
    famTotal++;
    baseline += (kin.length - 1) / (group.length - 1);
    if (FAM_OF[b] === FAM_OF[a]) famSame++;
  }
}
if (!famTotal) fail('no swap had a same-Family partner, so the preference is untested');
else if (famSame <= baseline) {
  fail(`Family preference does nothing: ${famSame} same-Family of ${famTotal}, ` +
       `uniform picking would give ${baseline.toFixed(1)}`);
} else ok(`Family preference bites: ${famSame}/${famTotal} same-Family trades, ` +
          `vs ${baseline.toFixed(1)} expected from uniform picking`);

// ── terrain: a belt must never hand out a plant the lawn cannot host ─────────
// Regression, found in play testing: an Ancient Egypt level dealt out Lily Pad
// and Tangle Kelp. Both are water-only, so on a waterless lawn they are dead
// slots -- the player is handed a plant with nowhere to put it. lilypad sat in
// sustained:budget beside wallnut and tanglekelp in single-use:budget beside
// potatomine, so any belt holding either could receive them.
const { setLevelWater, CONVEYOR_WATER_ONLY, CONVEYOR_TILE_LOCKED } = require('./conveyor_fn.js');
const LOCKED = new Set([...CONVEYOR_WATER_ONLY, ...CONVEYOR_TILE_LOCKED]);

// Levels whose own belt shows no water plant: the hook must treat these as dry,
// so nothing water-only may appear in the output that was not already there.
const dryLevels = LEVELS.filter(
  l => !l.InitialPlantList.some(e => e && CONVEYOR_WATER_ONLY.has(e.PlantType)));

function terrainViolations() {
  const bad = [];
  setLevelWater(false);
  for (const l of dryLevels) {
    const before = clone(l).InitialPlantList;
    const after = run(clone(l)).InitialPlantList;
    for (let i = 0; i < after.length; i++) {
      if (LOCKED.has(after[i].PlantType) && after[i].PlantType !== before[i].PlantType) {
        bad.push(`${l._file}[${i}]: ${before[i].PlantType} -> ${after[i].PlantType}`);
      }
    }
  }
  return bad;
}

const dryBad = terrainViolations();
if (dryBad.length) fail(`${dryBad.length} water/tile plant(s) placed on a dry lawn: ${dryBad.slice(0, 3).join('; ')}`);
else ok(`no water-only or tile-locked plant reached a dry lawn (${dryLevels.length} levels)`);

// The check above proves a NEGATIVE, so prove it can fail. Removing the terrain
// filter must make it fire -- otherwise it is passing vacuously and would not
// have caught the bug it exists for.
const realPlantable = window._AP_conveyorPlantable;
window._AP_conveyorPlantable = () => true;
const withoutFilter = terrainViolations();
window._AP_conveyorPlantable = realPlantable;
if (!withoutFilter.length) {
  fail('the terrain check passes even with the filter removed -- it proves nothing');
} else {
  ok(`terrain check verified against the old logic: ${withoutFilter.length} violation(s) ` +
     `without the filter, e.g. ${withoutFilter[0]}`);
}

// Fail closed: a level whose grid is not built yet reads as having no water,
// rather than defaulting to "anything goes".
setLevelWater(undefined);
let closedBad = 0;
for (const l of dryLevels) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < after.length; i++) {
    if (CONVEYOR_WATER_ONLY.has(after[i].PlantType) &&
        after[i].PlantType !== before[i].PlantType) closedBad++;
  }
}
if (closedBad) fail(`unreadable haveWater let ${closedBad} water plant(s) through`);
else ok('an unreadable level fails closed to "no water"');

// A water lawn may still receive water plants -- otherwise the gate above would
// be indistinguishable from deleting them from the pool entirely.
setLevelWater(true);
let wetGot = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < after.length; i++) {
    if (CONVEYOR_WATER_ONLY.has(after[i].PlantType) &&
        after[i].PlantType !== before[i].PlantType) wetGot++;
  }
}
if (!wetGot) fail('a water lawn never received a water plant -- the gate is always closed');
else ok(`a water lawn can still receive water plants (${wetGot} placements)`);

// goldleaf needs a goldtile and there is no level-wide flag for one, so it is
// never swapped in anywhere -- water lawns included.
let goldIn = 0;
for (const l of LEVELS) {
  const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
  for (let i = 0; i < after.length; i++) {
    if (after[i].PlantType === 'goldleaf' && before[i].PlantType !== 'goldleaf') goldIn++;
  }
}
if (goldIn) fail(`goldleaf swapped in ${goldIn} time(s) despite needing a gold tile`);
else ok('goldleaf is never swapped in, on any lawn');

// The other direction: a level that placed a terrain-locked plant itself keeps
// it. Swapping a Big Wave Beach belt's Lily Pad for a Wall-nut removes the only
// thing making its water columns usable.
let lockedKept = 0, lockedLost = 0;
for (const water of [false, true]) {
  setLevelWater(water);
  for (const l of LEVELS) {
    const before = clone(l).InitialPlantList, after = run(clone(l)).InitialPlantList;
    for (let i = 0; i < before.length; i++) {
      if (!LOCKED.has(before[i].PlantType)) continue;
      if (before[i].PlantType === after[i].PlantType) lockedKept++;
      else { lockedLost++; fail(`${l._file}[${i}]: terrain-locked ${before[i].PlantType} became ${after[i].PlantType}`); }
    }
  }
}
if (!lockedLost) ok(`${lockedKept} terrain-locked entries kept exactly as the level had them`);

// A belt carrying a water plant is itself proof the lawn has water, which is
// what keeps the gate working when haveWater cannot be read in time.
setLevelWater(undefined);
const wetByBelt = LEVELS.filter(
  l => l.InitialPlantList.some(e => e && CONVEYOR_WATER_ONLY.has(e.PlantType)));
let beltSignal = 0;
for (const l of wetByBelt) {
  const after = run(clone(l)).InitialPlantList;
  if (after.some(e => CONVEYOR_WATER_ONLY.has(e.PlantType))) beltSignal++;
}
ok(`${beltSignal}/${wetByBelt.length} levels recognised as wet from their own belt alone`);
setLevelWater(false);

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCONVEYOR HOOK OK');
process.exit(failed ? 1 : 0);
