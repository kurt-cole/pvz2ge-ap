// Drives the REAL restoreLostCurrency() / observeCurrency() from
// build_pvzge_ap.py.
//
// The bug being defended against, measured 2026-08-16: the game holds exactly
// one write to a player's coin or gem in the entire bundle, the HUD's value
// setter --
//     addCoinCount(n) { this.value += n; }   // adds to the COMPONENT
//     onValueSet(n)   { currentPlayer.coin = n; savePP(); }
// -- and the component seeds its own `value` from the player once, at load.
// Whenever it loads without the real save as currentPlayer it holds 0, and the
// next coin event of any size writes that absolute total over the balance.
// Measured directly: cp.coin 2000 while component.value sat at 0, ten seconds
// apart, with nothing else touching cp.
const {
  restoreLostCurrency, observeCurrency, currencyComponentChanged,
  syncCurrencyDisplay, applyCurrencyTraps, st, window, reset, restoreDone,
  savedCount,
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

// The restore is spent after one run. Everything after it that lowers the
// balance is the player spending, and must stand -- only a rebuilt component
// re-arms it (see below).
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

console.log('\n  zero is a spend unless a new display explains it');

// A balance at zero is ambiguous on its face: either the display stamped over
// the save, or the player spent their last coin. Only a NEWLY BUILT component
// can have stamped one, so the caller passes that in. Both halves measured:
// 2620 lost at a session boundary (a wipe), and 40 gems spent in the store
// coming straight back (a spend wrongly read as a wipe).

// Spend: no new component, so the zero stands and is recorded.
p = players(0, 0);
reset({ coinSeen: 500, gemSeen: 40 }, p);
observeCurrency(false);
is([st.coinSeen, st.gemSeen], [0, 0], 'spending the last of it is recorded');

// Wipe: a new component appeared this pass, so the ledger is kept.
p = players(0, 0);
reset({ coinSeen: 2620, gemSeen: 0 }, p);
observeCurrency(true);
is(st.coinSeen, 2620, 'a wipe does not overwrite the ledger');
is(savedCount(), 0, '...and nothing is written');
is(restoreLostCurrency(), ['coin +2620'], '...so the balance is still recoverable');

// A wipe is always to exactly zero, so a partial drop is spending either way.
p = players(120, 0);
reset({ coinSeen: 2620, gemSeen: 0 }, p);
observeCurrency(true);
is(st.coinSeen, 120, 'a partial drop is a purchase even when a display was rebuilt');

// Zero from a zero ledger is not a wipe, it is a player with no money.
p = players(0, 0);
reset({}, p);
observeCurrency(true);
is(st.coinSeen, 0, 'zero from a zero ledger records fine');

// Coins and gems are independent: a coin wipe must not freeze the gem ledger.
p = players(0, 40);
reset({ coinSeen: 500, gemSeen: 10 }, p);
observeCurrency(true);
is([st.coinSeen, st.gemSeen], [500, 40],
   'the coin wipe is ignored while the gem gain is recorded');

console.log('\n  the stale display, which is the actual bug');

// The real component: `value` is its own number, and its setter writes that
// ABSOLUTE value over the player. addCoinCount adds to the component, not to
// the player -- measured: cp.coin 2000 + addCoinCount(2000) left cp.coin at
// 2000, because the component went 0 -> 2000 and wrote 2000.
const realHud = (cp, field, addName, start) => {
  const c = {
    _v: start,
    get value() { return this._v; },
    set value(n) { this._v = n; cp[field] = n; },
  };
  c[addName] = function (n) { this.value = this.value + n; };
  return { component: c };
};

p = players(2000, 0);
reset({ coinSeen: 2000 }, p);
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
is(window._AP_CoinCount.component.value, 0, 'component loaded stale at 0 while the player holds 2000');
// This is the loss, reproduced: one coin picked up in a level.
window._AP_CoinCount.component.addCoinCount(10);
is(p.currentPlayer.coin, 10, 'a single 10-coin pickup overwrites the whole balance');

// ...and with the display kept seeded, the same pickup behaves.
p = players(2000, 0);
reset({ coinSeen: 2000 }, p);
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
is(syncCurrencyDisplay(), ['coin'], 'the stale display is re-seeded from the player');
is(window._AP_CoinCount.component.value, 2000, '...to the real balance');
window._AP_CoinCount.component.addCoinCount(10);
is(p.currentPlayer.coin, 2010, 'now a 10-coin pickup adds instead of erasing');

// Seeding is idempotent and silent once they agree.
is(syncCurrencyDisplay(), [], 'nothing to fix when display and player agree');

// No component on this screen is not an error.
reset({}, players(500, 0));
is(syncCurrencyDisplay(), [], 'no component: nothing to sync');
reset({}, null);
is(syncCurrencyDisplay(), [], 'no player: nothing to sync');

console.log('\n  a rebuilt component re-arms the restore');

// The component is torn down and rebuilt on every scene change, so "once per
// launch" is not enough -- each new one can have stamped its 0 over the save
// before the client's next poll.
p = players(0, 0);
reset({ coinSeen: 900 }, p);
restoreLostCurrency();
is(restoreDone(), true, 'the restore is spent after running once');
is(currencyComponentChanged(), false, 'no component at all is not a change');

window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
is(currencyComponentChanged(), true, 'a component appearing counts as a change');
is(currencyComponentChanged(), false, '...but only the first time it is seen');

const firstComp = window._AP_CoinCount;
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
is(window._AP_CoinCount !== firstComp, true, 'scene change built a new component');
is(currencyComponentChanged(), true, 'a REBUILT component counts again (identity, not presence)');

// The whole sequence rebuildAPSave runs, against a component that just wiped.
p = players(900, 0);
reset({ coinSeen: 900 }, p);
restoreLostCurrency();                               // spends the one restore
is(p.currentPlayer.coin, 900, 'balance intact before the scene change');
// A scene change builds a new component, which seeds itself at 0 and stamps
// that over the player -- the loss this whole mechanism exists to catch.
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
window._AP_CoinCount.component.value = 0;
is(p.currentPlayer.coin, 0, 'the new display wiped the balance');
if (currencyComponentChanged()) restoreDone(false);
const again = restoreLostCurrency();
is(again, ['coin +900'], 'the rebuilt component let the restore run again');
syncCurrencyDisplay();
observeCurrency();
is([p.currentPlayer.coin, window._AP_CoinCount.component.value, st.coinSeen],
   [900, 900, 900], 'player, display and ledger all agree afterwards');

// And the reason an unrepaired zero can be trusted as a spend: a real wipe is
// always repaired earlier in the same pass, before observeCurrency sees it.
p = players(2620, 0);
reset({ coinSeen: 2620, gemSeen: 0 }, p);
restoreLostCurrency();                               // spends the one restore
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 0);
window._AP_CoinCount.component.value = 0;            // new display stamps 0
const wiped = currencyComponentChanged();
if (wiped) restoreDone(false);
restoreLostCurrency();
syncCurrencyDisplay();
observeCurrency(wiped);
is([p.currentPlayer.coin, st.coinSeen], [2620, 2620],
   'wipe repaired in-pass, ledger intact');

console.log('\n  currency traps take, but never below zero');

// "-500 Coins" / "-20 Gems" arrive as a debt on st, because currentPlayer is
// often absent during the post-connect Sync replay.
p = players(3190, 60);
reset({ coinSeen: 3190, gemSeen: 60, coinDebt: 500, gemDebt: 20 }, p);
is(applyCurrencyTraps(), [['coin', 500], ['gem', 20]], 'both debts are taken');
is([p.currentPlayer.coin, p.currentPlayer.gem], [2690, 40], 'balances drop by the amount');
is([st.coinSeen, st.gemSeen], [2690, 40], 'the ledger follows the trap down');
is([st.coinDebt, st.gemDebt], [0, 0], 'the debt is cleared');

// The whole point: a trap bigger than the balance empties it and stops.
p = players(200, 5);
reset({ coinSeen: 200, gemSeen: 5, coinDebt: 500, gemDebt: 20 }, p);
is(applyCurrencyTraps(), [['coin', 200], ['gem', 5]], 'only what is there is taken');
is([p.currentPlayer.coin, p.currentPlayer.gem], [0, 0], 'the balance floors at zero');
is([st.coinSeen, st.gemSeen], [0, 0], 'and the ledger floors with it');

// The remainder is forgiven, not carried -- a hidden debt eating later income
// would be a far nastier item than the option describes.
is([st.coinDebt, st.gemDebt], [0, 0], 'the excess is forgiven, not held');
is(applyCurrencyTraps(), [], 'nothing is taken from an empty balance afterwards');

// An emptied balance must survive the restore, or the trap refunds itself.
// This is why the ledger is lowered by hand in applyCurrencyTraps:
// observeCurrency refuses to record a drop to exactly zero when a display was
// rebuilt, so nothing else would lower it.
//
// In rebuildAPSave order: restore runs first, so the trap always applies to a
// repaired balance rather than a wiped one.
p = players(0, 0);                       // wiped by a rebuilt display
reset({ coinSeen: 500, gemSeen: 20, coinDebt: 500, gemDebt: 20 }, p);
is(restoreLostCurrency(), ['coin +500', 'gem +20'], 'the wipe is repaired first');
is(applyCurrencyTraps(), [['coin', 500], ['gem', 20]], '...then the trap takes it');
is([p.currentPlayer.coin, st.coinSeen], [0, 0], 'balance and ledger both at zero');
restoreDone(false);
is(restoreLostCurrency(), [], 'a trapped-to-zero balance is not handed back');

// Already broke: nothing to take, nothing reported.
p = players(0, 0);
reset({ coinSeen: 0, gemSeen: 0, coinDebt: 500 }, p);
is(applyCurrencyTraps(), [], 'no balance, nothing taken');
is(st.coinDebt, 0, '...and the debt still clears rather than lurking');

// Goes through the display where there is one, so the counter agrees.
p = players(1000, 0);
reset({ coinSeen: 1000, gemSeen: 0, coinDebt: 400 }, p);
window._AP_CoinCount = realHud(p.currentPlayer, 'coin', 'addCoinCount', 1000);
applyCurrencyTraps();
is([p.currentPlayer.coin, window._AP_CoinCount.component.value], [600, 600],
   'the on-screen counter drops with the balance');

// No player yet: the debt is kept for the next poll rather than lost.
reset({ coinSeen: 500, gemSeen: 0, coinDebt: 500 }, null);
is(applyCurrencyTraps(), [], 'no player: nothing happens yet');
is(st.coinDebt, 500, '...and the debt survives for the retry');
window._AP_AllPlayerProperties = players(500, 0);
is(applyCurrencyTraps(), [['coin', 500]], 'applied once the player arrives');

// Debts accumulate when several traps land together.
p = players(3000, 0);
reset({ coinSeen: 3000, gemSeen: 0, coinDebt: 1500 }, p);   // three -500 traps
is(applyCurrencyTraps(), [['coin', 1500]], 'stacked traps are taken together');
is(p.currentPlayer.coin, 1500, '...for the full amount');

if (failed) {
  console.log(`\n${failed} FAILURE(S)`);
  process.exit(1);
}
console.log('\nCURRENCY RESTORE OK');
