// Drives the REAL syncGrantedUpgrades() lifted out of build_pvzge_ap.py.
const { setSt, syncGrantedUpgrades, window } = require('./upgrade_fn.js');

const MAP = {
  'Progressive Starting Sun':    ['upgrade_starting_sun_lvl1', 'upgrade_starting_sun_lvl2'],
  'Progressive Plant Food Slot': ['upgrade_pf_slots_lvl1', 'upgrade_pf_slots_lvl2'],
  'Progressive Seed Slot':       ['upgrade_7_slots', 'upgrade_8_slots'],
  'Progressive Sun Shovel':      ['upgrade_sunshovel_lvl1', 'upgrade_sunshovel_lvl2', 'upgrade_sunshovel_lvl3'],
  'Progressive Manual Mower':    ['upgrade_manual_mowers_1', 'upgrade_manual_mowers_2'],
  'Wall-nut First Aid':          ['upgrade_wallnut_firstaid'],
  'Plant Food Refresh':          ['upgrade_pf_refresh'],
  'Sky Shield':                  ['upgrade_sky_shield'],
};
const ALL = Object.fromEntries(Object.entries(MAP).map(([k, v]) => [k, v.length]));

let failed = 0;
function check(label, state, expectSize, mustHave) {
  setSt(state);
  const g = syncGrantedUpgrades();
  const errs = [];
  if (g.size !== expectSize) errs.push(`size ${g.size} != ${expectSize}`);
  for (const cn of (mustHave || [])) if (!g.has(cn)) errs.push(`missing ${cn}`);
  if ([...g].some(x => x === undefined)) errs.push('undefined in granted set');
  if (errs.length) { failed++; console.log(`  FAIL  ${label}: ${errs.join('; ')}`); }
  else console.log(`  ok    ${label}  (granted ${g.size})`);
  return g;
}

const on = (counts) => ({ shuffleUpgrades: true, upgradeItems: MAP, upgradeCounts: counts });

check('nothing received',       on({}), 0);
check('1 sun shovel',           on({ 'Progressive Sun Shovel': 1 }), 1, ['upgrade_sunshovel_lvl1']);
check('2 sun shovels',          on({ 'Progressive Sun Shovel': 2 }), 2, ['upgrade_sunshovel_lvl1', 'upgrade_sunshovel_lvl2']);
check('3 sun shovels',          on({ 'Progressive Sun Shovel': 3 }), 3, ['upgrade_sunshovel_lvl3']);
check('over-delivered (9)',     on({ 'Progressive Sun Shovel': 9 }), 3);
check('one-shot upgrade',       on({ 'Sky Shield': 1 }), 1, ['upgrade_sky_shield']);
check('unknown item ignored',   on({ 'Nonsense': 4 }), 0);
check('mixed partials',         on({ 'Progressive Starting Sun': 1, 'Progressive Seed Slot': 2, 'Plant Food Refresh': 1 }), 4,
                                ['upgrade_starting_sun_lvl1', 'upgrade_7_slots', 'upgrade_8_slots', 'upgrade_pf_refresh']);
check('everything',             on(ALL), 14);

// Prefixes must be monotonic: N+1 copies grants a superset of what N grants.
for (const [name, cns] of Object.entries(MAP)) {
  let prev = new Set();
  for (let n = 0; n <= cns.length; n++) {
    setSt(on({ [name]: n }));
    const g = syncGrantedUpgrades();
    if (g.size !== n) { failed++; console.log(`  FAIL  ${name} @${n}: size ${g.size}`); }
    for (const cn of prev) if (!g.has(cn)) { failed++; console.log(`  FAIL  ${name} @${n} lost ${cn}`); }
    prev = g;
  }
}
console.log('  ok    prefixes monotonic across all 8 groups');

// Backwards compatibility: a seed predating the option sends no map at all.
check('legacy seed, no slot_data', { receivedItems: ['Progressive Sun Shovel'] }, 0);
if (window._AP_shuffleUpgrades !== false) { failed++; console.log('  FAIL  legacy seed must read as not shuffled'); }
else console.log('  ok    legacy seed reads as not shuffled');

// knownUpgradeCns must cover all 14 whatever the granted set is.
setSt(on({}));
syncGrantedUpgrades();
if (window._AP_knownUpgradeCns.size !== 14) { failed++; console.log(`  FAIL  knownUpgradeCns ${window._AP_knownUpgradeCns.size} != 14`); }
else console.log('  ok    knownUpgradeCns covers all 14');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCLIENT PROGRESSIVE LOGIC OK');
process.exit(failed ? 1 : 0);
