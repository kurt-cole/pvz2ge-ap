// Drives the REAL budget zombie roll functions from build_pvzge_ap.py against
// the parity vectors the Python roll wrote (tools/gen_roll_vectors.py).
//
// Generation builds logic from zombie_roll.py's plans; this client has to field
// exactly those plans, or logic describes levels nobody plays. So every check
// here is equality with what Python produced: the level model extracted from
// raw level objects, the plan rolled from it, and the level objects after the
// plan is written back into them.
const fs = require('fs');
const path = require('path');
const B = require('./budget_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok   = m => console.log('  ok    ' + m);

const V = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'data', 'zombie_roll_vectors.json'), 'utf8'));
const clone = x => JSON.parse(JSON.stringify(x));

// Key order and undefined-vs-absent are not differences.
function canon(x) {
  if (Array.isArray(x)) return x.map(canon);
  if (x && typeof x === 'object') {
    const o = {};
    for (const k of Object.keys(x).sort()) if (x[k] !== undefined && x[k] !== null) o[k] = canon(x[k]);
    return o;
  }
  return x;
}
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));

const GROUP_KEYS = ['k', 'id', 'w', 'z', 'f', 'p', 'rep', 'bring', 'pf'];
function view(plan) {
  if (!plan) return null;
  return {
    attempt: plan.attempt, vanilla: plan.vanilla, budget: plan.budget, ratio: plan.ratio,
    dynamic: plan.dynamic, dinos: plan.dinos,
    groups: plan.groups.map(g => {
      const o = {};
      for (const k of GROUP_KEYS) if (g[k] !== undefined) o[k] = g[k];
      return o;
    }),
  };
}

function firstDiff(a, b) {
  const x = JSON.stringify(canon(a)), y = JSON.stringify(canon(b));
  let i = 0;
  while (i < x.length && x[i] === y[i]) i++;
  return `at char ${i}: js ...${x.slice(Math.max(0, i - 60), i + 60)}... py ...${y.slice(Math.max(0, i - 60), i + 60)}...`;
}

const tables = B._apbTables(V.tables);

// ── extraction ───────────────────────────────────────────────────────────────
{
  const bad = [];
  for (const fx of V.fixtures) {
    const model = B._apbModel(clone(fx.objects));
    if (!same(model, fx.model)) bad.push(`${fx.level}: ${firstDiff(model, fx.model)}`);
  }
  if (bad.length) fail(`${bad.length} fixtures extract a different model: ${bad[0]}`);
  else ok(`all ${V.fixtures.length} fixtures extract the Python level model from raw objects`);
}

// ── the roll ─────────────────────────────────────────────────────────────────
{
  const bad = [];
  let count = 0, rolled = 0, dinos = 0;
  for (const c of V.fixtures.concat(V.rolls)) {
    const model = c.objects ? B._apbModel(clone(c.objects)) : c.model;
    for (const p of c.plans) {
      count++;
      const js = view(B._apbRoll(tables, p.seed, c.level, model, p.dinos, p.goal));
      if (!same(js, p.plan)) bad.push(`${c.level} seed ${p.seed}: ${firstDiff(js, p.plan)}`);
      if (p.plan && !p.plan.vanilla) rolled++;
      if (p.plan && p.plan.dinos.length) dinos++;
    }
  }
  if (bad.length) fail(`${bad.length} of ${count} plans differ from Python: ${bad[0]}`);
  else ok(`all ${count} plans match Python bit for bit (${rolled} rolled, ${dinos} with dino events)`);
}

// ── writing a plan back ──────────────────────────────────────────────────────
{
  const bad = [];
  let checked = 0;
  for (const fx of V.fixtures) {
    for (const p of fx.plans) {
      if (!p.plan || p.plan.vanilla) continue;
      const objs = clone(fx.objects);
      const before = B._apbModel(clone(fx.objects));
      B._apbApply(tables, objs, p.plan);
      const after = B._apbModel(objs);
      const seen = {};
      for (const g of p.plan.groups) {
        if (seen[g.id] || !(B.APB.LIST_KINDS.includes(g.k) || B.APB.FIELD_KINDS.includes(g.k))) continue;
        seen[g.id] = true;
        const got = after.groups.find(x => x.id === g.id && x.w === g.w);
        if (!got || !same(got.z, g.z)) {
          bad.push(`${fx.level}/${g.id}: wrote ${JSON.stringify(got && got.z)}, planned ${JSON.stringify(g.z)}`);
        }
      }
      if (after.dinos.length !== before.dinos.length + p.plan.dinos.length) {
        bad.push(`${fx.level}: ${p.plan.dinos.length} dino events planned, ${after.dinos.length - before.dinos.length} written`);
      }
      checked++;
    }
  }
  if (bad.length) fail(`applying plans: ${bad.length} mismatches, first ${bad[0]}`);
  else ok(`${checked} applied plans read back as exactly the planned groups and dino events`);
}

// ── the hook ─────────────────────────────────────────────────────────────────
{
  const fx = V.fixtures.find(f => f.plans.some(p => p.plan && !p.plan.vanilla && p.goal === 2 && p.dinos));
  const p = fx.plans.find(q => q.plan && !q.plan.vanilla && q.goal === 2 && q.dinos);
  let calls = 0;
  function LC() {}
  LC.prototype.module_SetLevelDefinition = function () { calls++; return 'orig'; };
  B.installBudgetHook(LC);
  B.installBudgetHook(LC);   // idempotent: a second wrap would roll a rolled level

  B.st.zombieBudgetRoll = false;
  B.st.zombieBudget = Object.assign({}, V.tables, { goal: 2, dinos: true });
  B.st.zombieSeed = p.seed;
  B.syncBudgetConfig();
  B.setLevelKey(fx.level);
  const off = new LC();
  off.currentLevelObjects = clone(fx.objects);
  off.module_SetLevelDefinition();
  if (!same(off.currentLevelObjects, fx.objects)) fail('budget roll off, but the hook rewrote the level');
  else ok('with zombie_budget_roll off the hook leaves the level as authored');

  B.st.zombieBudgetRoll = true;
  B.syncBudgetConfig();
  const on = new LC();
  on.currentLevelObjects = clone(fx.objects);
  const result = on.module_SetLevelDefinition();
  const expected = clone(fx.objects);
  B._apbApply(tables, expected, p.plan);
  if (result !== 'orig' || calls !== 2) fail(`the original module_SetLevelDefinition ran ${calls} times`);
  else if (!same(B._apbModel(on.currentLevelObjects), B._apbModel(expected))) {
    fail(`${fx.level}: the hook fielded something other than the Python plan`);
  } else ok(`${fx.level}: the hook rewrites the level to the Python plan, then runs the game's own code`);

  const snapshot = clone(on.currentLevelObjects);
  on.module_SetLevelDefinition();
  if (!same(on.currentLevelObjects, snapshot)) fail('a second module_SetLevelDefinition re-rolled the level');
  else ok('a level is rolled once, however often the game reads it');

  // A seed from before the option: no keys at all.
  delete B.st.zombieBudgetRoll; delete B.st.zombieBudget;
  B.syncBudgetConfig();
  if (B.window._AP_zombieBudget !== null) fail('slot_data with no budget keys did not read as off');
  else ok('slot_data with no budget keys reads as off');
}

// ── plant food ───────────────────────────────────────────────────────────────
// A wave owing plant food has to keep enough zombies able to carry it, and a
// collectable keyed to a zombie codename has to keep pointing at one the level
// still fields. Both are invisible in game until something never drops.
{
  const bad = [];
  let owed = 0;
  for (const c of V.fixtures.concat(V.rolls)) {
    const model = c.objects ? B._apbModel(clone(c.objects)) : c.model;
    const need = {};
    for (const g of model.groups) if (g.pf) need[g.id] = g.pf;
    for (const p of c.plans) {
      if (!p.plan || p.plan.vanilla) continue;
      for (const g of p.plan.groups) {
        const n = need[g.id];
        if (!n || !B.APB.LIST_KINDS.includes(g.k)) continue;
        owed++;
        let carriers = 0;
        for (const e of g.z) if (tables.carry[e[0]] !== false) carriers += e[1];
        if (carriers < n) {
          bad.push(`${c.level}/${g.id} owes ${n} plant food, fields ${carriers} carriers`);
        }
      }
    }
  }
  if (bad.length) fail(`${bad.length} of ${owed} groups cannot hand out their plant food: ${bad[0]}`);
  else ok(`all ${owed} plant food groups keep enough carriers to hand it out`);
}

{
  const fx = V.fixtures.find(f => f.objects.some(o => o.objclass === 'PickupCollectableTutorialProperties'
                                                 && (o.objdata || {}).DropperZombieType));
  if (!fx) {
    fail('no fixture keys a collectable to a zombie type');
  } else {
    const bad = [];
    let checked = 0;
    for (const p of fx.plans) {
      if (!p.plan || p.plan.vanilla) continue;
      const objs = clone(fx.objects);
      B._apbApply(tables, objs, p.plan);
      const fielded = new Set();
      for (const g of p.plan.groups) for (const e of g.z) fielded.add(e[0]);
      for (const o of objs) {
        if (o.objclass !== 'PickupCollectableTutorialProperties') continue;
        if (!o.objdata.DropperZombieType) continue;
        checked++;
        if (!fielded.has(o.objdata.DropperZombieType)) {
          bad.push(`${fx.level}: dropper ${o.objdata.DropperZombieType} is not in the rolled level`);
        }
      }
    }
    if (bad.length) fail(bad[0]);
    else ok(`${fx.level}: the collectable dropper follows the roll (${checked} plans)`);
  }
}

// ── narrow lawns ─────────────────────────────────────────────────────────────
// The tutorial levels play on part of the lawn, and a chicken thrower or a
// barrel puts bodies into the lanes either side of its own without asking
// whether they are playable. Nothing in game says which lane a body came from,
// so this is invisible until a level is unwinnable.
{
  const bad = [];
  let narrow = 0, wide = 0;
  for (const c of V.fixtures.concat(V.rolls)) {
    const model = c.objects ? B._apbModel(clone(c.objects)) : c.model;
    const isNarrow = (model.lanes || 5) < 5;
    if (isNarrow) narrow++;
    for (const p of c.plans) {
      if (!p.plan || p.plan.vanilla) continue;
      for (const g of p.plan.groups) {
        for (const e of g.z) {
          if (!tables.multilane[e[0]]) continue;
          if (isNarrow) bad.push(`${c.level} (${model.lanes} lanes) fields ${e[0]}`);
          else wide++;
        }
      }
    }
  }
  if (!narrow) fail('no fixture or roll level has fewer than five lanes');
  else if (bad.length) fail(`${bad.length} multi-lane spawns on a narrow lawn: ${bad[0]}`);
  else if (!wide) fail('multi-lane spawners appear nowhere at all, so nothing was proven');
  else ok(`${narrow} narrow levels field no multi-lane spawner (${wide} such spawns elsewhere)`);
}

// ── never rolled ─────────────────────────────────────────────────────────────
{
  const never = V.fixtures.filter(f => f.model.bespoke || f.model.generated);
  const rolled = never.filter(f => B._apbRoll(tables, 1, f.level, B._apbModel(clone(f.objects)), true, 2) !== null);
  if (!never.length) fail('no bespoke or generated fixture to check');
  else if (rolled.length) fail(`bespoke or generated levels were rolled: ${rolled.map(f => f.level)}`);
  else ok(`${never.map(f => f.level).join(', ')} (bespoke / runtime-generated) are never rolled`);
}

console.log(failed ? `\n${failed} FAILURE(S)` : '\nBUDGET ROLL CLIENT OK');
process.exit(failed ? 1 : 0);
