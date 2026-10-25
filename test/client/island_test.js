// Drives the REAL installRewardIslandGate() from build_pvzge_ap.py against a
// stand-in world map whose islands follow the game's LevelIsland rules:
// start() marks a level island finished from its saved progress and a reward
// island finished when its plant/upgrade is owned, and laterStart() has a
// finished island unlock the islands after it.
const { installRewardIslandGate } = require('./island_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);

function Island() {}
Island.prototype.laterStart = function () {
  if (this._finished) for (const n of this.next) if (!n._unlocked && !n._finished) n._unlocked = true;
};
Object.defineProperty(Island.prototype, 'formalIsland', {
  get() { return this.map.levelIslands.find(i => i.next.indexOf(this) !== -1); },
});
function WM() {}
WM.prototype.setIslandActive = function () {};
installRewardIslandGate(WM);
installRewardIslandGate(WM);   // idempotent

// wildwest-ish: level K -> Wall-nut First Aid node -> level K+1
function load(kBeaten, upgradeOwned) {
  const map = new WM();
  const k = Object.assign(new Island(), { map, _levelNode: {}, _finished: kBeaten, _unlocked: true, next: [] });
  const up = Object.assign(new Island(), { map, _upgradeOnDisplay: {}, _finished: upgradeOwned, next: [] });
  const k1 = Object.assign(new Island(), { map, _levelNode: {}, _finished: false, _unlocked: false, next: [] });
  k.next = [up]; up.next = [k1];
  map.levelIslands = [k, up, k1];
  map.setIslandActive();
  for (const i of map.levelIslands) i.laterStart();
  return k1._unlocked;
}
const cases = [
  [false, true,  false, 'upgrade received, level before it unbeaten: next level stays shut'],
  [true,  false, true,  'level beaten, upgrade not received yet: next level opens'],
  [true,  true,  true,  'both: next level opens'],
  [false, false, false, 'neither: next level stays shut'],
];
for (const [beaten, owned, want, what] of cases) {
  const got = load(beaten, owned);
  if (got !== want) fail(`${what} (got unlocked=${got})`); else ok(what);
}

// A plant island chained after another reward island still looks back to the level.
{
  const map = new WM();
  const k = Object.assign(new Island(), { map, _levelNode: {}, _finished: false, _unlocked: true, next: [] });
  const up = Object.assign(new Island(), { map, _upgradeOnDisplay: {}, _finished: true, next: [] });
  const pl = Object.assign(new Island(), { map, _plantOnDisplay: {}, _finished: true, next: [] });
  const k1 = Object.assign(new Island(), { map, _levelNode: {}, _finished: false, _unlocked: false, next: [] });
  k.next = [up]; up.next = [pl]; pl.next = [k1];
  map.levelIslands = [k, up, pl, k1];
  map.setIslandActive();
  for (const i of map.levelIslands) i.laterStart();
  if (k1._unlocked) fail('two reward islands in a row let an owned plant open the next level');
  else ok('two reward islands in a row both follow the level before them');
}

console.log(failed ? `\n${failed} FAILURE(S)` : '\nREWARD ISLANDS OK');
process.exit(failed ? 1 : 0);
