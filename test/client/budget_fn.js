// Copies of the budget zombie roll functions from build_pvzge_ap.py, kept in
// sync by drift_test.py. Do not edit the copied functions here: edit the client
// and re-copy (everything between the "Budget zombie roll" banner and
// window._AP_initApLogo). Everything above and below them is harness scaffolding.
const window = {};
const st = {};
const AP_BESPOKE_MODULES = /Minigame|Beghouled|Rhythm/;
const _AP_RTID = /^RTID\(([^@()]+)@([^()]*)\)$/;

// Harness stubs. _apLevelKey reads the game's LevelPlay statics in the client;
// here the test sets the level id directly. _apLog writes to the console and,
// once the client's panel exists, to window._AP_log; here it just records.
let _levelKey = '';
function setLevelKey(id) { _levelKey = id; }
function _apLevelKey() { return _levelKey; }
const logs = [];
function _apLog(msg) { logs.push(msg); }

function _apHash(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// ── Budget zombie roll (zombie_budget_roll, experimental) ───────────────────
// The client half of pvz2gardendless/zombie_roll.py. Generation rolled every
// level from zombie_seed and built its logic from the result; this re-rolls
// the identical plan from the level's own objects and writes it into
// currentLevelObjects before the game reads the level. Everything is integer
// arithmetic on one mulberry32 stream per attempt, in the same order as the
// Python, and test/data/zombie_roll_vectors.json holds the two together: a
// change to either side that does not change both fails budget_test.js.
//
// The hook point: readLevelJson deep-copies the level into
// currentLevelObjects and then awaits module_SetLevelDefinition, which reads
// the modules and builds the wave manager. Every RTID(x@CurrentLevel)
// resolves live against currentLevelObjects, so rewriting it on entry to
// module_SetLevelDefinition is seen by everything after, and the deep copy
// means nothing restores the authored data. The game's own danger-room
// designers push wave objects into the same list the same way.
const APB = {
  NOISE_LO: 1000, NOISE_HI: 1200, FEASIBLE_PERMILLE: 1100, NOVEL_WEIGHT: 3,
  CAP_MULT: 3, CAP_ADD: 4, LEVEL_OK: [900, 1100], LEVEL_HARD: [750, 1333], TRIES: 8,
  SHARE_KNEE: 200, SHARE_HALF: 50, DINO_BUDGET_PERMILLE: 100,
  DINO_TYPES: ['ankylo', 'ptero', 'raptor', 'stego', 'tyranno'],
  DINO_LEVEL_PERMILLE_BY_GOAL: [262, 232, 236],
  DINO_BANDS: [[4192, 500, 600, 3, [0, 7, 24, 8, 11]],
               [5331, 500, 777, 3, [3, 12, 34, 10, 5]],
               [6462, 500, 1000, 2, [8, 11, 35, 8, 15]],
               [1073741824, 777, 1400, 2, [8, 26, 51, 6, 27]]],
  DINO_TEST_BEACH: false, DINO_TEST_PIRATE: false, GRAVE_DEFAULT_HP: 700,
  LIST_KINDS: ['jittered', 'ground', 'storm', 'grave_spawn'],
  FIELD_KINDS: ['raid', 'beach', 'spider', 'parachute'],
  BUCKETS: ['generic|land', 'generic|water', 'skycity|land'],
  HAZARD_TAGS: ['jester', 'iceblock', 'air'],
  // [user] Nothing new before egypt6: a run's opening is played with
  // whatever the multiworld has handed over by then, so these levels field
  // only the hazards they shipped with, and never gain dinos. Mirrors
  // OPENING_LEVELS in zombie_roll.py.
  OPENING_LEVELS: ['tutorial1', 'tutorial2', 'tutorial3', 'tutorial4', 'tutorial5',
                   'egypt1', 'egypt2', 'egypt3', 'egypt4', 'egypt5'],
  // [user] A rocket imp reaches the house before the player can plant, so it
  // never opens a level. Wave 1 only. Mirrors FIRST_WAVE_BANNED.
  FIRST_WAVE_BANNED: ['kongfu_rocket_imp'],
  // Level objclass -> how many lanes the lawn really has. The tutorial lawn
  // rolls its sod out a strip at a time and disables the rest; tutorial4 is
  // absent because it sets five lanes before it animates, and nothing else in
  // the game narrows the lawn. Mirrors TUTORIAL_LANES in gen_level_model.py.
  TUTORIAL_LANES: {
    TutorialLevel1Properties: 1,
    TutorialLevel2Properties: 3,
    TutorialLevel3Properties: 3,
  },
  FAR_FUTURE_FLYERS: ['future_jetpack', 'future_jetpack_disco', 'future_jetpack_veteran'],
  RAID_DEFAULT: 'swashbuckler',
  KINDS: {
    SpawnZombiesJitteredWaveActionProps: 'jittered',
    SpawnZombiesFromGroundSpawnerProps: 'ground',
    StormZombieSpawnerProps: 'storm',
    QigongStrikeWaveActionProps: 'qigong',
    RaidingPartyZombieSpawnerProps: 'raid',
    BeachStageEventZombieSpawnerProps: 'beach',
    SpiderRainZombieSpawnerProps: 'spider',
    ParachuteRainZombieSpawnerProps: 'parachute',
    DropShipZombieSpawnerProps: 'dropship',
    SpawnZombiesFromGridItemSpawnerProps: 'grave_spawn',
  },
};

function _apbHas(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }

function _apbByName(a, b) { return a[0] < b[0] ? -1 : (a[0] > b[0] ? 1 : 0); }

function _apbCmpEvent(a, b) {
  if (a[0] !== b[0]) return a[0] - b[0];
  if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
  return a[2] - b[2];
}

// mulberry32 as integers: below(n) is floor(u32 * n / 2^32), which is exact
// in a double for every n the roll uses.
function _apbStream(seed) {
  let a = seed >>> 0;
  const next = function () {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return (t ^ (t >>> 14)) >>> 0;
  };
  return { below: function (n) { return n > 0 ? Math.floor(next() * n / 4294967296) : 0; } };
}

// Python's rt(): the name out of RTID(name@table), a bare string trimmed.
function _apbRt(value) {
  if (typeof value !== 'string') return null;
  const s = value.trim();
  const m = _AP_RTID.exec(s);
  return m ? m[1] : s;
}

// Python's as_int(): int(float(value)), or the default when that would raise.
function _apbInt(value, dflt) {
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (typeof value === 'number') return isFinite(value) ? Math.trunc(value) : dflt;
  if (typeof value === 'string' && value.trim() !== '') {
    const f = Number(value.trim());
    return isFinite(f) ? Math.trunc(f) : dflt;
  }
  return dflt;
}

function _apbListEntries(entries, key) {
  const counts = Object.create(null);
  for (const e of Array.isArray(entries) ? entries : []) {
    if (!e || typeof e !== 'object' || Array.isArray(e)) continue;
    const name = _apbRt(e[key]);
    if (!name) continue;
    counts[name] = (counts[name] || 0) + 1;
  }
  return Object.keys(counts).sort().map(function (c) { return [c, counts[c]]; });
}

function _apbGroup(kind, alias, data) {
  const out = { k: kind, id: alias };
  let z = [];
  if (kind === 'jittered' || kind === 'ground' || kind === 'storm' ||
      kind === 'grave_spawn' || kind === 'qigong') {
    z = _apbListEntries(data.Zombies, 'Type');
  } else if (kind === 'raid') {
    const name = _apbRt(data.ZombieType) || APB.RAID_DEFAULT;
    z = [[name, _apbInt(data.SwashbucklerCount, 0)]];
    out.f = 'SwashbucklerCount'; out.p = name;
  } else if (kind === 'beach') {
    z = [[data.ZombieName, _apbInt(data.ZombieCount, 0)]];
    out.f = 'ZombieCount'; out.p = data.ZombieName;
  } else if (kind === 'spider' || kind === 'parachute') {
    const primary = data.SpiderZombieName;
    z = primary ? [[primary, _apbInt(data.SpiderCount, 0)]] : [];
    if (kind === 'parachute') out.bring = _apbListEntries(data.ZombiesToBringWith, 'Type');
    out.f = 'SpiderCount'; out.p = primary;
  } else if (kind === 'dropship') {
    const shifted = data.DropShipShiftedProperties || {};
    const imps = shifted.ImpCount || {};
    z = [[data.DropShipType, 1], [shifted.ImpType, _apbInt(imps.Max, 0)]]
      .filter(function (e) { return e[0]; });
    out.f = 'DropShipShiftedProperties.ImpCount';
  }
  out.z = z.filter(function (e) { return e[1] > 0; });
  let pf = 0;
  if (Array.isArray(data.DynamicPlantfood) && data.DynamicPlantfood.length) {
    for (const v of data.DynamicPlantfood) pf = Math.max(pf, _apbInt(v, 0));
  } else {
    pf = _apbInt(data.AdditionalPlantfood, 0);
  }
  if (pf > 0) out.pf = pf;
  return out;
}

function _apbGravePool(data) {
  const pool = Object.create(null);
  for (const e of Array.isArray(data.GravestonePool) ? data.GravestonePool : []) {
    if (e && typeof e === 'object' && !Array.isArray(e) && _apbRt(e.Type)) {
      const k = _apbRt(e.Type);
      pool[k] = (pool[k] || 0) + _apbInt(e.Count, 0);
    }
  }
  for (const key of Object.keys(data)) {
    if (key.indexOf('RTID(') === 0) {
      const k = _apbRt(key);
      pool[k] = (pool[k] || 0) + _apbInt(data[key], 0);
    }
  }
  const out = {};
  for (const k of Object.keys(pool).sort()) if (pool[k] > 0) out[k] = pool[k];
  return out;
}

function _apbAliases(objs) {
  const byAlias = Object.create(null);
  for (const o of objs) for (const al of (o && o.aliases) || []) byAlias[al] = o;
  return byAlias;
}

function _apbFirst(objs, cls) {
  for (const o of objs) if (o && o.objclass === cls) return o.objdata || {};
  return {};
}

function _apbManager(objs, byAlias) {
  const target = _apbRt(_apbFirst(objs, 'WaveManagerModuleProperties').WaveManagerProps);
  const obj = target ? byAlias[target] : undefined;
  if (obj && obj.objclass === 'WaveManagerProperties') return obj.objdata || {};
  return _apbFirst(objs, 'WaveManagerProperties');
}

// The level model tools/gen_level_model.py writes, rebuilt from live objects.
// Only the fields the roll reads.
function _apbModel(objs) {
  const byAlias = _apbAliases(objs);
  const definition = _apbFirst(objs, 'LevelDefinition');
  const manager = _apbManager(objs, byAlias);
  const waves = Array.isArray(manager.Waves) ? manager.Waves : [];
  const seedbank = _apbFirst(objs, 'SeedBankProperties');
  const conveyor = (Array.isArray(definition.Modules) ? definition.Modules : [])
    .some(function (m) { return String(_apbRt(m)).indexOf('Conveyor') >= 0; });
  const groups = [], dinos = [], spawned = [];
  const visit = function (wave, ref, rep, seen) {
    const alias = _apbRt(ref);
    if (!alias || seen.indexOf(alias) >= 0) return;
    const obj = byAlias[alias];
    if (obj === undefined) return;
    const next = seen.concat([alias]);
    const cls = obj.objclass || '';
    const data = obj.objdata || {};
    if (cls === 'WaveSchedulerProps') {
      const r = _apbInt((data.Repeat || {}).Max, 1);
      for (const inner of Array.isArray(data.Events) ? data.Events : []) visit(wave, inner, r, next);
      return;
    }
    if (_apbHas(APB.KINDS, cls)) {
      const g = _apbGroup(APB.KINDS[cls], alias, data);
      if (g.z.length) {
        g.w = wave;
        if (rep && rep > 1) g.rep = rep;
        groups.push(g);
      }
      return;
    }
    if (cls === 'DinoWaveActionProps') dinos.push([wave, data.DinoType, _apbInt(data.DinoRow, -1)]);
    else if (cls === 'SpawnGravestonesWaveActionProps') spawned.push([wave, _apbGravePool(data)]);
  };
  waves.forEach(function (wave, index) {
    if (Array.isArray(wave)) for (const ref of wave) visit(index + 1, ref, null, []);
  });
  const dynamic = [];
  for (const e of Array.isArray(_apbFirst(objs, 'WaveManagerModuleProperties').DynamicZombies)
                  ? _apbFirst(objs, 'WaveManagerModuleProperties').DynamicZombies : []) {
    dynamic.push({ w: _apbInt(e.StartingWave, 0), p: _apbInt(e.StartingPoints, 0),
                   inc: _apbInt(e.PointIncrementPerWave, 0),
                   pool: (Array.isArray(e.ZombiePool) ? e.ZombiePool : [])
                     .map(_apbRt).filter(function (c) { return c; }) });
  }
  const initial = Object.create(null);
  let randomInitial = 0;
  for (const o of objs) {
    if (!o || o.objclass !== 'GravestoneProperties') continue;
    const data = o.objdata || {};
    for (const e of Array.isArray(data.ForceSpawnData) ? data.ForceSpawnData : []) {
      if (e && typeof e === 'object' && e.TypeName) initial[e.TypeName] = (initial[e.TypeName] || 0) + 1;
    }
    randomInitial += _apbInt(data.GravestoneCount, 0);
  }
  const count = manager.WaveCount;
  return {
    waves: waves.length || (Number.isInteger(count) ? count : 0),
    stage: _apbRt(definition.StageModule) || '',
    bespoke: objs.some(function (o) { return o && AP_BESPOKE_MODULES.test(o.objclass || ''); }),
    generated: objs.some(function (o) {
      return o && /^(WaveGeneratorProperties|DangerRoom\w+)$/.test(o.objclass || '');
    }),
    own_plants: seedbank.SelectionMethod === 'chooser' && !conveyor,
    // Playable lanes. The tutorial lawn rolls its sod out a strip at a time
    // and disables the rest; nothing else in the game narrows the lawn.
    lanes: Math.min.apply(null, objs.map(function (o) {
      return (o && APB.TUTORIAL_LANES[o.objclass]) || 5;
    }).concat([5])),
    planks: (Array.isArray(_apbFirst(objs, 'PiratePlankProperties').PlankRows)
             ? _apbFirst(objs, 'PiratePlankProperties').PlankRows.slice() : [])
      .sort(function (x, y) { return x - y; }),
    groups: groups, dynamic: dynamic, dinos: dinos,
    graves: { initial: initial, random_initial: randomInitial,
              spawned: spawned.filter(function (s) { return Object.keys(s[1]).length; }) },
  };
}

// The tables zombie_roll.py builds from the level model, rebuilt from the
// zombie_budget slot_data table (budget_logic.client_tables).
function _apbTables(data) {
  const zombies = (data && data.zombies) || {};
  const names = Object.keys(zombies).sort();
  const t = { hp: Object.create(null), cost: Object.create(null), tier: Object.create(null),
              excluded: Object.create(null), pools: {}, poolHp: {}, tiers: Object.create(null),
              hazard: Object.create(null), field: {}, graveHp: (data && data.grave_hp) || {},
              carry: Object.create(null), multilane: Object.create(null) };
  for (const c of names) {
    const z = zombies[c];
    t.hp[c] = z[0]; t.cost[c] = z[1]; t.tier[c] = z[2] || ''; t.excluded[c] = z[3] || '';
    // A short entry is a seed rolled before that flag existed, and reads as
    // what the roll assumed then: every zombie able to carry plant food, and
    // none of them putting bodies into a neighbouring lane.
    t.carry[c] = z.length > 4 ? !!z[4] : true;
    t.multilane[c] = z.length > 5 ? !!z[5] : false;
  }
  for (const b of APB.BUCKETS) t.pools[b] = [];
  for (const c of names) {
    const key = _apbBucket(t, c);
    if (key && t.hp[c] > 0) t.pools[key].push(c);
    if (t.tier[c]) (t.tiers[t.tier[c]] = t.tiers[t.tier[c]] || []).push(c);
    if (APB.HAZARD_TAGS.some(function (tag) { return t.tier[c].indexOf('-' + tag) >= 0; }) ||
        APB.FAR_FUTURE_FLYERS.indexOf(c) >= 0) t.hazard[c] = true;
  }
  for (const b of APB.BUCKETS) {
    t.pools[b].sort(function (x, y) { return (t.hp[x] - t.hp[y]) || (x < y ? -1 : (x > y ? 1 : 0)); });
    t.poolHp[b] = t.pools[b].map(function (c) { return t.hp[c]; });
  }
  for (const k of APB.FIELD_KINDS) {
    t.field[k] = Object.create(null);
    for (const c of ((data && data.field_names) || {})[k] || []) t.field[k][c] = true;
  }
  return t;
}

function _apbBucket(t, c) {
  if (typeof c !== 'string' || !(c in t.hp)) return null;
  if (t.tier[c]) return t.tier[c].indexOf('-water') >= 0 ? 'generic|water' : 'generic|land';
  if (t.excluded[c] === 'skycity') return 'skycity|land';
  return null;
}

function _apbGroupsHp(t, groups) {
  let s = 0;
  for (const g of groups) for (const e of g.z) s += (t.hp[e[0]] || 0) * e[1] * (g.rep || 1);
  return s;
}

function _apbDynamicHp(t, level, mapping) {
  let total = 0;
  for (const entry of level.dynamic) {
    const ratios = [];
    for (const c0 of entry.pool) {
      const c = _apbHas(mapping, c0) ? mapping[c0] : c0;
      if (t.hp[c] && t.cost[c]) ratios.push(Math.floor(t.hp[c] * 1000 / t.cost[c]));
    }
    if (!ratios.length) continue;
    const milli = Math.floor(ratios.reduce(function (a, b) { return a + b; }, 0) / ratios.length);
    let points = 0;
    for (let w = entry.w; w <= level.waves; w++) {
      const p = entry.p + entry.inc * (w - entry.w);
      if (p > 0) points += p;
    }
    total += Math.floor(points * milli / 1000);
  }
  return total;
}

function _apbGravesHp(t, level) {
  const g = level.graves;
  let s = 0;
  for (const k of Object.keys(g.initial)) s += (t.graveHp[k] || 0) * g.initial[k];
  s += g.random_initial * APB.GRAVE_DEFAULT_HP;
  for (const sp of g.spawned) for (const k of Object.keys(sp[1])) s += (t.graveHp[k] || 0) * sp[1][k];
  return s;
}

function _apbMaxShare(groups) {
  const counts = Object.create(null);
  for (const g of groups) for (const e of g.z) counts[e[0]] = (counts[e[0]] || 0) + e[1] * (g.rep || 1);
  let top = 0, total = 0;
  for (const c in counts) { total += counts[c]; if (counts[c] > top) top = counts[c]; }
  return [top, total];
}

function _apbAccept(over) {
  const q = Math.floor(over / APB.SHARE_HALF), r = over % APB.SHARE_HALF;
  const base = q < 11 ? (1000 >> q) : 0;
  return base - Math.floor(base * r / (2 * APB.SHARE_HALF));
}

function _apbDinosAllowed(level) {
  if (level.bespoke || level.generated || level.dinos.length || !level.waves || !level.own_plants) return false;
  if (level.stage.indexOf('Beach') >= 0) return APB.DINO_TEST_BEACH;
  if (level.stage.indexOf('Pirate') >= 0) return APB.DINO_TEST_PIRATE && level.planks.length > 0;
  return true;
}

function _apbDinoEvents(rng, level, budget) {
  const waves = level.waves;
  const perWave = Math.floor(budget / waves);
  let band = APB.DINO_BANDS[APB.DINO_BANDS.length - 1];
  for (const b of APB.DINO_BANDS) if (perWave <= b[0]) { band = b; break; }
  const rate = band[1] + rng.below(band[2] - band[1] + 1);
  const first = Math.min(band[3], waves);
  const weights = band[4];
  const wsum = weights.reduce(function (a, b) { return a + b; }, 0);
  const rows = level.stage.indexOf('Pirate') >= 0 ? level.planks : [0, 1, 2, 3, 4];
  const events = [];
  const n = Math.max(1, Math.floor(waves * rate / 1000));
  for (let i = 0; i < n; i++) {
    const wave = first + rng.below(waves - first + 1);
    let r = rng.below(wsum), kind = 0;
    while (r >= weights[kind]) { r -= weights[kind]; kind++; }
    events.push([wave, APB.DINO_TYPES[kind], rows[rng.below(rows.length)]]);
  }
  return events.sort(_apbCmpEvent);
}

function _apbPick(rng, cands, vanilla) {
  const old = [];
  for (let i = 0; i < cands.length; i++) if (vanilla[cands[i]]) old.push(i);
  const W = APB.NOVEL_WEIGHT;
  const r = rng.below(W * cands.length - (W - 1) * old.length);
  let lo = 0, hi = cands.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    let le = 0;
    while (le < old.length && old[le] <= mid) le++;
    if (W * (mid + 1) - (W - 1) * le > r) hi = mid; else lo = mid + 1;
  }
  return cands[lo];
}

function _apbRollBucket(t, rng, key, entries, vanilla, scale, fieldKind, cap, pools) {
  let pool = pools[key][0], poolHp = pools[key][1];
  if (fieldKind) {
    const p2 = [], h2 = [];
    for (let i = 0; i < pool.length; i++) {
      if (t.field[fieldKind][pool[i]]) { p2.push(pool[i]); h2.push(poolHp[i]); }
    }
    pool = p2; poolHp = h2;
  }
  if (pool.length < 2) return entries.map(function (e) { return [e[0], e[1]]; });
  let h = 0;
  for (const e of entries) h += t.hp[e[0]] * e[1];
  const noise = APB.NOISE_LO + rng.below(APB.NOISE_HI - APB.NOISE_LO + 1);
  const target = Math.floor(Math.floor(h * noise / 1000) * scale / 1000);
  const k = fieldKind ? 1 : 1 + rng.below(entries.length);
  const weights = [];
  for (let i = 0; i < k; i++) weights.push(1 + rng.below(4));
  const wsum = weights.reduce(function (a, b) { return a + b; }, 0);
  const picks = Object.create(null);
  for (const weight of weights) {
    const part = Math.floor(target * weight / wsum);
    const limit = Math.floor(part * APB.FEASIBLE_PERMILLE / 1000);
    let cut = 0;
    while (cut < poolHp.length && poolHp[cut] <= limit) cut++;
    const c = _apbPick(rng, cut ? pool.slice(0, cut) : pool.slice(0, 1), vanilla);
    picks[c] = (picks[c] || 0) + Math.max(1, Math.floor((part + Math.floor(t.hp[c] / 2)) / t.hp[c]));
  }
  let sum = 0;
  for (const c in picks) sum += picks[c];
  while (sum > cap) {
    const names = Object.keys(picks).sort();
    let best = names[0];
    for (const n of names) if (picks[n] > picks[best]) best = n;
    picks[best] -= 1; sum -= 1;
    if (picks[best] === 0 && Object.keys(picks).length > 1) delete picks[best];
  }
  return Object.keys(picks).sort().filter(function (c) { return picks[c] > 0; })
    .map(function (c) { return [c, picks[c]]; });
}

// _ensure_carriers(), as the Python. addPlantFood hands a wave's plant food
// to zombies picked at random from the ones it spawned, skipping those that
// cannot carry it, and the grave spawner never comes back for them. So a
// group owing plant food has to field enough zombies able to take it.
// Nothing is drawn here, so the stream stays in step with generation.
function _apbEnsureCarriers(t, entries, need, pools) {
  if (!(need > 0) || !entries.length) return entries;
  const counts = Object.create(null);
  for (const e of entries) counts[e[0]] = e[1];
  let carried = 0;
  for (const c of Object.keys(counts)) if (t.carry[c] !== false) carried += counts[c];
  if (carried >= need) return entries;
  const nearest = function (bucket, hp) {
    let best = null;
    for (const c of pools[bucket][0]) {
      if (t.carry[c] === false) continue;
      const d = Math.abs((t.hp[c] || 0) - hp);
      if (best === null || d < best.d || (d === best.d && c < best.c)) best = { d: d, c: c };
    }
    return best && best.c;
  };
  while (carried < need) {
    const swappable = Object.keys(counts).filter(function (c) {
      return counts[c] > 0 && t.carry[c] === false && _apbBucket(t, c);
    }).sort(function (x, y) { return (counts[y] - counts[x]) || (x < y ? -1 : (x > y ? 1 : 0)); });
    const source = swappable.length ? swappable[0]
      : Object.keys(counts).sort().filter(function (c) { return _apbBucket(t, c); })[0];
    if (source === undefined) break;
    const pick = nearest(_apbBucket(t, source), t.hp[source] || 0);
    if (!pick) break;
    if (swappable.length) {          // convert one body rather than add one
      counts[source] -= 1;
      if (counts[source] === 0) delete counts[source];
    }
    counts[pick] = (counts[pick] || 0) + 1;
    carried += 1;
  }
  return Object.keys(counts).sort().filter(function (c) { return counts[c] > 0; })
    .map(function (c) { return [c, counts[c]]; });
}

function _apbAttempt(t, seed, levelId, level, attempt, scale, vanilla, pools,
                     poolsFirst) {
  const rng = _apbStream(_apHash(String(seed) + '|' + levelId + '|budget|' + attempt));
  const groups = [];
  const done = Object.create(null);
  for (const g of level.groups) {
    const kind = g.k;
    const out = { id: g.id, w: g.w, k: kind, z: g.z.map(function (e) { return [e[0], e[1]]; }) };
    if (_apbHas(g, 'f')) out.f = g.f;
    if (_apbHas(g, 'rep')) out.rep = g.rep;
    const rolls = APB.LIST_KINDS.indexOf(kind) >= 0 || APB.FIELD_KINDS.indexOf(kind) >= 0;
    if (rolls && done[g.id]) {
      const prev = done[g.id];
      out.z = prev.z.map(function (e) { return [e[0], e[1]]; });
      if (_apbHas(prev, 'p')) out.p = prev.p;
      if (_apbHas(g, 'bring')) out.bring = g.bring;
    } else if (rolls) {
      // Wave 1 draws from the pool that has no level-opening zombie in it.
      const gp = (g.w === 1 && poolsFirst) ? poolsFirst : pools;
      const buckets = Object.create(null), fixed = [];
      for (const e of g.z) {
        const key = _apbBucket(t, e[0]);
        if (key) (buckets[key] = buckets[key] || []).push([e[0], e[1]]);
        else fixed.push([e[0], e[1]]);
      }
      let rolled = fixed.slice();
      let swappable = 0;
      for (const key in buckets) for (const e of buckets[key]) swappable += e[1];
      const groupCap = Math.max(swappable * APB.CAP_MULT, swappable + APB.CAP_ADD);
      for (const key of APB.BUCKETS) {
        if (!buckets[key]) continue;
        let n0 = 0;
        for (const e of buckets[key]) n0 += e[1];
        rolled = rolled.concat(_apbRollBucket(
          t, rng, key, buckets[key], vanilla, scale,
          APB.FIELD_KINDS.indexOf(kind) >= 0 ? kind : null,
          Math.max(1, Math.floor(groupCap * n0 / swappable)), gp));
      }
      const merged = Object.create(null);
      for (const e of rolled) merged[e[0]] = (merged[e[0]] || 0) + e[1];
      out.z = Object.keys(merged).sort().map(function (c) { return [c, merged[c]]; });
      // Field sources name one codename in a field the spawner is written
      // around, so they are left alone: a swap could name something the
      // field may not hold.
      if (APB.LIST_KINDS.indexOf(kind) >= 0) {
        out.z = _apbEnsureCarriers(t, out.z, g.pf || 0, gp);
      }
      if (APB.FIELD_KINDS.indexOf(kind) >= 0 && out.z.length) out.p = out.z[0][0];
      if (_apbHas(g, 'bring')) out.bring = g.bring;
      done[g.id] = out;
    }
    groups.push(out);
  }
  const mapping = {};
  const names = Object.create(null);
  for (const e of level.dynamic) for (const c of e.pool) names[c] = true;
  for (const c of Object.keys(names).sort()) {
    const members = t.tiers[t.tier[c] || ''] || [];
    if (members.length >= 2) {
      const pick = members[rng.below(members.length)];
      if (pick !== c) mapping[c] = pick;
    }
  }
  return { rng: rng, groups: groups, mapping: mapping };
}

// roll_level(), as the Python. null for a level the roll never touches.
function _apbRoll(t, seed, levelId, level, dinos, goal) {
  if (!level || level.bespoke || level.generated) return null;
  const graves = _apbGravesHp(t, level);
  const budget = _apbGroupsHp(t, level.groups) + _apbDynamicHp(t, level, {}) + graves;
  const vanilla = Object.create(null);
  for (const g of level.groups) for (const e of g.z) vanilla[e[0]] = true;
  const pools = {};
  for (const b of APB.BUCKETS) pools[b] = [t.pools[b], t.poolHp[b]];
  // Conveyor or preset seed bank: the player cannot bring a counter, so only
  // hazards the level shipped with may appear. Fewer than five lanes: a
  // chicken thrower or a barrel drops bodies into the lanes either side of
  // its own without asking whether they are playable, and on the tutorial
  // lawn they are not. A level that ships one keeps it, either way.
  const narrow = (level.lanes || 5) < 5;
  // Before egypt6 the player has no counter yet, which asks of the pool
  // exactly what a preset seed bank does.
  const opening = APB.OPENING_LEVELS.indexOf(levelId) >= 0;
  const bring = level.own_plants && !opening;
  // [user] A level that picks the player's plants for them may field nothing
  // tougher than its own toughest zombie: the budget is still spent, as more
  // bodies rather than bigger ones.
  let ceiling = 0;
  if (!level.own_plants) {
    for (const c of Object.keys(vanilla)) ceiling = Math.max(ceiling, t.hp[c] || 0);
  }
  if (!bring || narrow || ceiling) {
    for (const b of APB.BUCKETS) {
      const names = t.pools[b].filter(function (c) {
        return vanilla[c] || ((bring || !t.hazard[c])
                              && (!narrow || !t.multilane[c])
                              && (!ceiling || t.hp[c] <= ceiling));
      });
      pools[b] = [names, names.map(function (c) { return t.hp[c]; })];
    }
  }
  // Wave 1 rolls out of a pool of its own. Same draws, one fewer candidate.
  const poolsFirst = {};
  let cutFirst = false;
  for (const b of APB.BUCKETS) {
    const names = pools[b][0].filter(function (c) {
      return vanilla[c] || APB.FIRST_WAVE_BANNED.indexOf(c) < 0;
    });
    if (names.length !== pools[b][0].length) cutFirst = true;
    poolsFirst[b] = [names, names.map(function (c) { return t.hp[c]; })];
  }
  const share0 = _apbMaxShare(level.groups);
  const knee = Math.min(1000, (share0[1] ? Math.floor(share0[0] * 1000 / share0[1]) : 0) + APB.SHARE_KNEE);
  const dinoRng = _apbStream(_apHash(String(seed) + '|' + levelId + '|dinos'));
  let added = [];
  // The draw runs first whatever the answer, so a level that cannot gain
  // dinos still leaves the stream where generation expects it.
  if (dinoRng.below(1000) < (APB.DINO_LEVEL_PERMILLE_BY_GOAL[goal] || 0) &&
      dinos && !opening && _apbDinosAllowed(level)) {
    added = _apbDinoEvents(dinoRng, level, budget);
  }
  const scale = added.length ? 1000 - APB.DINO_BUDGET_PERMILLE : 1000;
  let best = null;
  for (let attempt = 0; attempt < APB.TRIES; attempt++) {
    const a = _apbAttempt(t, seed, levelId, level, attempt, scale, vanilla, pools,
                          cutFirst ? poolsFirst : pools);
    let total = _apbGroupsHp(t, a.groups) + _apbDynamicHp(t, level, a.mapping) + graves;
    if (added.length) total = Math.floor(total * 1000 / (1000 - APB.DINO_BUDGET_PERMILLE));
    const ratio = budget ? Math.floor(total * 1000 / budget) : 1000;
    const sh = _apbMaxShare(a.groups);
    const share = sh[1] ? Math.floor(sh[0] * 1000 / sh[1]) : 0;
    if (share > knee && a.rng.below(1000) >= _apbAccept(share - knee)) continue;
    const plan = { attempt: attempt, vanilla: false, budget: budget, ratio: ratio,
                   groups: a.groups, dynamic: a.mapping, dinos: added.slice() };
    if (ratio >= APB.LEVEL_OK[0] && ratio <= APB.LEVEL_OK[1]) return plan;
    if (best === null || Math.abs(ratio - 1000) < Math.abs(best.ratio - 1000)) best = plan;
  }
  if (best !== null && best.ratio >= APB.LEVEL_HARD[0] && best.ratio <= APB.LEVEL_HARD[1]) return best;
  return { attempt: -1, vanilla: true, budget: budget, ratio: 1000,
           groups: level.groups, dynamic: {}, dinos: [] };
}

// Rewrite a list source's Zombies[] to the rolled composition. A rolled
// codename clones the authored entries of its own bucket in turn, so a water
// zombie keeps a water entry's Row and every other field the entry carried.
function _apbApplyList(t, data, z) {
  const authored = (Array.isArray(data.Zombies) ? data.Zombies : [])
    .filter(function (e) { return e && typeof e === 'object' && _apbRt(e.Type); });
  const byBucket = Object.create(null), fixedByName = Object.create(null);
  for (const e of authored) {
    const c = _apbRt(e.Type), key = _apbBucket(t, c);
    if (key) (byBucket[key] = byBucket[key] || []).push(e);
    else (fixedByName[c] = fixedByName[c] || []).push(e);
  }
  const out = [];
  for (const entry of z) {
    const c = entry[0], n = entry[1], key = _apbBucket(t, c);
    if (!key) { for (const e of fixedByName[c] || []) out.push(e); continue; }
    const templates = byBucket[key] || authored;
    for (let i = 0; i < n; i++) {
      const tpl = templates[i % templates.length];
      const clone = Object.assign({}, tpl);
      clone.Type = _AP_RTID.test(String(tpl.Type).trim()) ? 'RTID(' + c + '@ZombieTypes)' : c;
      out.push(clone);
    }
  }
  data.Zombies = out;
}

function _apbApplyField(g, data) {
  if (!g.z.length || !g.p) return;
  const n = g.z[0][1];
  const same = function (old, v) { return typeof old === 'string' ? String(v) : v; };
  if (g.k === 'raid') {
    data.ZombieType = 'RTID(' + g.p + '@ZombieTypes)';
    data.SwashbucklerCount = same(data.SwashbucklerCount, n);
  } else if (g.k === 'beach') {
    data.ZombieName = g.p;
    data.ZombieCount = same(data.ZombieCount, n);
  } else {
    data.SpiderZombieName = g.p;
    data.SpiderCount = same(data.SpiderCount, n);
  }
}

// Write a plan into the level's objects: groups, the dynamic pools, and any
// dino events the roll added (as the game's own designers add wave objects).
function _apbApply(t, objs, plan) {
  const byAlias = _apbAliases(objs);
  const applied = Object.create(null);
  for (const g of plan.groups) {
    if (applied[g.id]) continue;
    applied[g.id] = true;
    const obj = byAlias[g.id];
    if (!obj) continue;
    const data = obj.objdata || (obj.objdata = {});
    if (APB.LIST_KINDS.indexOf(g.k) >= 0) _apbApplyList(t, data, g.z);
    else if (APB.FIELD_KINDS.indexOf(g.k) >= 0) _apbApplyField(g, data);
  }
  for (const o of objs) {
    if (!o || o.objclass !== 'WaveManagerModuleProperties') continue;
    for (const e of Array.isArray((o.objdata || {}).DynamicZombies) ? o.objdata.DynamicZombies : []) {
      if (!Array.isArray(e.ZombiePool)) continue;
      e.ZombiePool = e.ZombiePool.map(function (ref) {
        const c = _apbRt(ref);
        if (!c || !_apbHas(plan.dynamic, c)) return ref;
        return _AP_RTID.test(String(ref).trim()) ? 'RTID(' + plan.dynamic[c] + '@ZombieTypes)' : plan.dynamic[c];
      });
    }
    break;
  }
  if (plan.dinos.length) {
    const waves = _apbManager(objs, byAlias).Waves;
    plan.dinos.forEach(function (d, i) {
      if (!Array.isArray(waves) || !Array.isArray(waves[d[0] - 1])) return;
      const alias = 'APBudgetDino' + i;
      objs.push({ aliases: [alias], objclass: 'DinoWaveActionProps',
                  objdata: { DinoRow: d[2], DinoType: d[1], DinoWaveDuration: 3 } });
      waves[d[0] - 1].push('RTID(' + alias + '@CurrentLevel)');
    });
  }
  // A level can key a tutorial collectable to a zombie codename: egypt5's
  // Zen Garden sprout to `ra`, tutorial4's first coin to `tutorial_armor2`.
  // registerZombieInThisWave matches DropperZombieType against what spawned,
  // so rolling that type out of the level means the collectable never drops
  // and the tutorial never completes. Point it at something the level does
  // field: the earliest wave's first codename, by name on a tie.
  let earliest = null;
  const fielded = Object.create(null);
  for (const g of plan.groups) {
    for (const e of g.z) {
      fielded[e[0]] = true;
      if (!earliest || g.w < earliest.w || (g.w === earliest.w && e[0] < earliest.c)) {
        earliest = { w: g.w, c: e[0] };
      }
    }
  }
  if (earliest) {
    for (const o of objs) {
      if (!o || o.objclass !== 'PickupCollectableTutorialProperties') continue;
      const d = o.objdata || (o.objdata = {});
      if (d.DropperZombieType && !fielded[d.DropperZombieType]) {
        d.DropperZombieType = earliest.c;
      }
    }
  }
}

// Built here rather than by syncBudgetConfig, which lives in the AP client
// closure and so cannot see _apbTables. Keyed on the slot_data object itself,
// so a reconnect that hands over the same table does not rebuild it.
let _apbTableSrc = null, _apbTableCache = null;

function _apbPrepareLevel(lc) {
  const cfg = window._AP_zombieBudget;
  if (!cfg || !cfg.data) return;
  const objs = lc && lc.currentLevelObjects;
  if (!Array.isArray(objs) || !objs.length || objs._ap_budget_done) return;
  objs._ap_budget_done = true;
  const levelId = _apLevelKey();
  if (!levelId) return;
  if (_apbTableSrc !== cfg.data) {
    _apbTableCache = _apbTables(cfg.data);
    _apbTableSrc = cfg.data;
  }
  // Every field generation rolled from, so a log line from a real run says
  // whether the client rolled the same level, the same key and the same
  // model as generation did. A silent hook is what made a diverging roll
  // look like a logic bug rather than a parity one.
  const model = _apbModel(objs);
  const plan = _apbRoll(_apbTableCache, cfg.seed, levelId, model, cfg.dinos, cfg.goal);
  const shape = ' key=' + JSON.stringify(levelId) + ' seed=' + cfg.seed +
      ' own=' + (model.own_plants ? 1 : 0) + ' waves=' + model.waves +
      ' groups=' + model.groups.length + ' dyn=' + model.dynamic.length;
  // The vanilla fallback used to return in silence, which is the one outcome
  // a player can see (the level plays as authored) and could not report.
  if (!plan || plan.vanilla) {
    _apLog('[AP] zombie budget roll: left vanilla,' + shape);
    return;
  }
  _apbApply(_apbTableCache, objs, plan);
  _apLog('[AP] zombie budget roll: ' + plan.ratio + '/1000 HP, attempt=' + plan.attempt +
      ', ' + plan.dinos.length + ' dino events,' + shape);
}

// Fails OPEN to vanilla: if anything here throws, the level plays as
// authored, which is never harder than logic assumed for its hazards.
function installBudgetHook(LC) {
  if (!LC || LC._ap_hooked_budget || !LC.prototype ||
      typeof LC.prototype.module_SetLevelDefinition !== 'function') return;
  const _origSetLevelDefinition = LC.prototype.module_SetLevelDefinition;
  LC.prototype.module_SetLevelDefinition = function () {
    try { _apbPrepareLevel(this); } catch (e) {
      try { _apLog('[AP] zombie budget roll skipped: ' + e); } catch (e2) { /* unreachable */ }
    }
    return _origSetLevelDefinition.apply(this, arguments);
  };
  LC._ap_hooked_budget = true;
}

// Same again for the budget roll, which reads the whole zombie table rather
// than a tier map and builds its own lookups on the hook side. Absent keys
// read as off, which is what every seed before the option sends.
function syncBudgetConfig() {
  window._AP_zombieBudget = (st.zombieBudgetRoll && st.zombieBudget && st.zombieBudget.zombies)
    ? { data: st.zombieBudget, seed: st.zombieSeed || 0,
        goal: st.zombieBudget.goal | 0, dinos: !!st.zombieBudget.dinos }
    : null;
}

module.exports = {
  window, st, logs, APB, setLevelKey,
  _apbModel, _apbTables, _apbRoll, _apbApply, installBudgetHook, syncBudgetConfig,
};
