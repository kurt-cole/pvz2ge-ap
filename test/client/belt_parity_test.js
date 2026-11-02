// The client's belt swap against generation's port (belt_roll.py), bit for
// bit at the guard's attempts (0, rerolls, -1 as shipped). test/belt_roll_test.py writes the vectors and runs this:
//     node belt_parity_test.js <vectors.json>
const fs = require('fs');
const { installConveyorHook, _apBeltModProps, _apBuildConveyorSwaps, window, setLevelWater } = require('./conveyor_fn.js');

const V = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let seen = null;
function LC() {}
LC.prototype.module_SetConveyor = function (props) { seen = props; };
installConveyorHook(LC);
const lc = new LC();
window._AP_randomizeConveyor = true;

let failed = 0, n = 0;
const bad = [];
for (const v of V) {
  n++;
  window._AP_conveyorSeed = v.seed;
  window._testThreats = v.threats;
  window._testLevelKey = v.level;
  window._AP_beltAttempts = { [v.level]: v.attempt || 0 };
  window._AP_conveyorDamageRule = !!v.rule;
  window._AP_conveyorSwaps = _apBuildConveyorSwaps(!!v.rule);
  window._testLevelObjects = [{ objclass: 'LevelDefinition',
    objdata: { StageModule: v.sky ? 'RTID(SkyStage@LevelModules)' : 'RTID(EgyptStage@LevelModules)' } }];
  setLevelWater(v.water);
  seen = null;
  lc.module_SetConveyor({ InitialPlantList: JSON.parse(JSON.stringify(v.initial)) });
  const got = { initial: seen.InitialPlantList.map(e => e && e.PlantType), adds: [] };
  for (const [w, adds, removes] of v.mods) {
    // The client's wave hook skips puzzle belts before it reaches the swap.
    if (v.puzzle) { got.adds.push(adds.map(e => e.Type)); continue; }
    const p = _apBeltModProps(lc, {
      Add: adds.map(e => Object.assign({}, e, { Type: 'RTID(' + e.Type + '@PlantTypes)' })),
      Remove: removes.map(e => Object.assign({}, e, { Type: 'RTID(' + e.Type + '@PlantTypes)' })),
    });
    got.adds.push(p.Add.map(e => /^RTID\(([^@]+)@/.exec(e.Type)[1]));
  }
  if (JSON.stringify(got) !== JSON.stringify(v.want)) {
    bad.push(`${v.level} seed ${v.seed} threats ${v.threats}: js ${JSON.stringify(got)} py ${JSON.stringify(v.want)}`);
  }
}
if (bad.length) { failed++; console.log(`  FAIL  ${bad.length} of ${n} belts differ: ${bad[0]}`); }
else console.log(`  ok    all ${n} belts match the client bit for bit`);
process.exit(failed ? 1 : 0);
