// Drives the REAL installStoreHook() from build_pvzge_ap.py against a
// StoreCommodity shaped like the game's: readCommodity() destroys its own node
// when the thing is already owned, unlockable() gates buying, unlockCommodity()
// performs it.
const { installStoreHook, window } = require('./store_fn.js');

// ── the AP client side, as the real one behaves ──────────────────────────────
const checked = new Set();
let shopsanity = true;
window._AP_onShopPurchase = n => { if (shopsanity) checked.add('Shop: ' + n); };
window._AP_isShopCommodityChecked = n => shopsanity && checked.has('Shop: ' + n);

// ── a stand-in for the game's StoreCommodity ─────────────────────────────────
// owned[] stands for getPlantProgressByID/getUpgradeProgressByID > 0. Under AP
// this stays empty: the plant and upgrade guards block the unlock and
// rebuildAPSave resets it every poll. That is the whole bug.
const owned = new Set();
function SC() { this.node = { destroyed: false, destroy() { this.destroyed = true; } }; }
SC.prototype.readCommodity = function (props) {
  this.currentCommodity = props;
  if (owned.has(props.CommodityName)) { this.node.destroy(); return Promise.resolve(); }
  this.built = true;
  return Promise.resolve();
};
SC.prototype.unlockable = function () {
  if (this.soldout) return false;
  return gems >= 100;
};
SC.prototype.unlockCommodity = function () {
  // the game grants, then marks sold out. AP blocks the grant, so `owned`
  // deliberately never gains the name here.
  this.soldout = true;
};
SC.prototype.buy = function () { if (this.unlockable()) { this.unlockCommodity(); gems -= 100; } };

let gems = 1000;
installStoreHook(SC);
installStoreHook(SC); // must be idempotent

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);

const PROPS = { CommodityType: 'upgrade', CommodityName: 'upgrade_8_slots' };
const openStore = () => { const c = new SC(); c.readCommodity(PROPS); return c; };

// ── the reported bug ─────────────────────────────────────────────────────────
gems = 1000;
let card = openStore();
if (!card.built) fail('card should be offered before purchase');
card.buy();
if (!checked.has('Shop: upgrade_8_slots')) fail('check did not fire');
if (gems !== 900) fail('gems not spent');
ok('first purchase: card offered, check fired, 100 gems spent');

// same screen, no refresh: must not be buyable again
card.buy();
if (gems !== 900) fail(`bought twice on the live screen (gems ${gems})`);
else ok('second purchase on the same screen is blocked');
if (card.unlockable() !== false) fail('unlockable() should be false once checked');
else ok('buy button reads as unavailable');

// refresh the screen: the card must not come back
const refreshed = openStore();
if (refreshed.built) fail('card came back after refresh (the reported bug)');
else if (!refreshed.node.destroyed) fail('card node was not destroyed on refresh');
else ok('card is gone after refreshing the screen');

// and stays gone across many refreshes
let reappeared = 0;
for (let i = 0; i < 25; i++) if (openStore().built) reappeared++;
if (reappeared) fail(`card reappeared on ${reappeared}/25 refreshes`);
else ok('card stays gone across 25 refreshes');

// ── an unchecked commodity is untouched ──────────────────────────────────────
const OTHER = { CommodityType: 'plant', CommodityName: 'jalapeno' };
const other = new SC(); other.readCommodity(OTHER);
if (!other.built) fail('an unchecked commodity must still be offered');
else ok('unchecked commodities are still offered');
gems = 1000; other.buy();
if (gems !== 900 || !checked.has('Shop: jalapeno')) fail('unchecked commodity could not be bought');
else ok('unchecked commodity buys normally and fires its check');

// ── shopsanity off: hands off entirely ───────────────────────────────────────
shopsanity = false;
const off = new SC(); off.readCommodity({ CommodityType: 'upgrade', CommodityName: 'upgrade_8_slots' });
if (!off.built) fail('shopsanity off must not hide store cards');
else ok('shopsanity off leaves the store alone');
shopsanity = true;

// ── the game's own hiding still works ────────────────────────────────────────
owned.add('upgrade_pf_slots_lvl2');
const vanilla = new SC(); vanilla.readCommodity({ CommodityType: 'upgrade', CommodityName: 'upgrade_pf_slots_lvl2' });
if (vanilla.built) fail("the game's own owned-check should still hide the card");
else ok("the game's own owned-check still hides cards");

// ── defensive ────────────────────────────────────────────────────────────────
new SC().readCommodity({ CommodityType: 'gem', CommodityCount: 50 });  ok('a commodity with no name is handled');
const p = openStore().constructor === SC;
if (!(openStore() instanceof SC)) fail('readCommodity broke construction');
const ret = new SC().readCommodity(PROPS);
if (!(ret && typeof ret.then === 'function')) fail('readCommodity must still return a promise');
else ok('readCommodity still returns a promise on the hidden path');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nSTORE HOOK OK');
process.exit(failed ? 1 : 0);
