// Drives the REAL restoreLostCurrency() / observeCurrency() from
// build_pvzge_ap.py.
//
// The bug being defended against, measured 2026-08-16: the game holds exactly
// one write to a player's coin or gem in the entire bundle, the coin HUD's
// value setter --
//     onValueSet(n) { currentPlayer.coin = n; savePP(); }
// -- and the component's load runs `this.value = this._shownValue` against a
// currentPlayer that is not the loaded save yet. It reads 0 and writes that 0
// through. Confirmed by writing 12345, reloading the page with no shutdown at
// all, and reading 0 back.
const {
  restoreLostCurrency, observeCurrency, st, window, reset, savedCount,
} = require('./currency_fn.js');

let failed = 0;
const ok = m => console.log('  ok    ' + m);
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const is = (got, want, m) =>
  JSON.stringify(got) === JSON.stringify(want)
    ? ok(m) : fail(`${m}  (got ${JSON.stringify(got)}, want ${JSON.stringify(want)})`);

// A player as the game leaves it, plus a stand-in for the HUD component whose
// setter is the only thing that may write the field.
const players = (coin, gem) => {
  const cp = { coin, gem };
  return { currentPlayer: cp, saves: 0, savePP() { this.saves++; } };
};
// The real component: addCoinCount adds to its own value, and the setter
// writes through to the player. Modelled because restore must go through it,
// not around it -- writing cp directly leaves the HUD holding a stale number
// that the next add would push back over the save.
const hud = (cp, field, addName, start) => {
  const c = { value: start };
  c[addName] = function (n) { this.value += n; cp[field] = this.value; };
  return { component: c };
};

console.log('\n  the boot wipe is put back');

reset({ coinSeen: 500, gemSeen: 20 }, players(0, 0));
let out = restoreLostCurrency();
is(out, ['coin +500', 'gem +20'], 'a wiped balance is restored from what was seen');
is(window._AP_AllPlayerProperties.currentPlayer.coin, 500, '...coin is back');
is(window._AP_AllPlayerProperties.currentPlayer.gem, 20, '...gem is back');
is(window._AP_AllPlayerProperties.saves, 1, '...and it saved once');

console.log('\n  it goes through the HUD when there is one');

let p = players(0, 0);
reset({ coinSeen: 500 }, p);
window._AP_CoinCount = hud(p.currentPlayer, 'coin', 'addCoinCount', 0);
restoreLostCurrency();
is(p.currentPlayer.coin, 500, 'the component setter wrote the player');
is(window._AP_CoinCount.component.value, 500,
   'the displayed value matches, so the next add cannot clobber the save');

// A throwing component must not lose the balance.
p = players(0, 0);
reset({ coinSeen: 750 }, p);
window._AP_CoinCount = { component: { addCoinCount() { throw new Error('boom'); } } };
restoreLostCurrency();
is(p.currentPlayer.coin, 750, 'a throwing component falls back to a direct write');

console.log('\n  it never invents currency');

reset({ coinSeen: 0, gemSeen: 0 }, players(0, 0));
is(restoreLostCurrency(), [], 'nothing seen, nothing restored');

reset({}, players(0, 0));
is(restoreLostCurrency(), [], 'no seen record at all, nothing restored');

reset({ coinSeen: 100 }, players(400, 0));
is(restoreLostCurrency(), [], 'holding more than was seen restores nothing');
is(window._AP_AllPlayerProperties.currentPlayer.coin, 400, '...and does not lower it');

console.log('\n  spending is not undone');

// The wipe happens once, at boot. Everything after it that lowers the balance
// is the player spending, and must stand.
p = players(0, 0);
reset({ coinSeen: 500 }, p);
restoreLostCurrency();
is(p.currentPlayer.coin, 500, 'restored at boot');
p.currentPlayer.coin = 200;                       // spent 300 in the store
is(restoreLostCurrency(), [], 'a later shortfall is not restored');
is(p.currentPlayer.coin, 200, '...the spend stands');
observeCurrency();
is(st.coinSeen, 200, '...and the new balance is what gets remembered');

console.log('\n  no player yet means try again later');

reset({ coinSeen: 500 }, null);
is(restoreLostCurrency(), [], 'no AllPlayerProperties: nothing happens');
reset({ coinSeen: 500 }, { currentPlayer: null });
is(restoreLostCurrency(), [], 'no currentPlayer: nothing happens');
// Crucially it must NOT burn its one attempt while the player is missing.
window._AP_AllPlayerProperties = players(0, 0);
is(restoreLostCurrency(), ['coin +500'], 'the retry still fires once the player arrives');

console.log('\n  observing records the truth');

p = players(1234, 56);
reset({}, p);
observeCurrency();
is([st.coinSeen, st.gemSeen], [1234, 56], 'records what the player holds');
is(savedCount(), 1, 'saved once');
observeCurrency();
is(savedCount(), 1, 'an unchanged balance does not save again');
p.currentPlayer.coin = 1300;
observeCurrency();
is([st.coinSeen, savedCount()], [1300, 2], 'a change is recorded and saved');

p = players(undefined, undefined);
reset({}, p);
observeCurrency();
is([st.coinSeen, st.gemSeen], [0, 0], 'a player with no coin field reads as 0');

// The ordering the caller relies on: restore, then observe. Observing first
// would record the wiped 0 and the balance would be gone for good.
p = players(0, 0);
reset({ coinSeen: 900 }, p);
restoreLostCurrency();
observeCurrency();
is(st.coinSeen, 900, 'restore-then-observe keeps the balance');

p = players(0, 0);
reset({ coinSeen: 900 }, p);
observeCurrency();
is(st.coinSeen, 0,
   'observe-first would destroy it -- this is why order matters in rebuildAPSave');

if (failed) {
  console.log(`\n${failed} FAILURE(S)`);
  process.exit(1);
}
console.log('\nCURRENCY RESTORE OK');
