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
function SC() {
  this.node = { destroyed: false, destroy() { this.destroyed = true; } };
  // The real card's label, which readCommodity() fills in with the plant or
  // upgrade name partway through its own async body.
  this.nameLabel = { string: '' };
}
SC.prototype.readCommodity = function (props) {
  this.currentCommodity = props;
  if (owned.has(props.CommodityName)) { this.node.destroy(); return Promise.resolve(); }
  this.built = true;
  // Async and late, exactly like the game's: anything relabelling the card has
  // to run after this resolves or it just gets overwritten.
  return Promise.resolve().then(() => { this.nameLabel.string = props.CommodityName; });
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

// ── shopsanity card labels ───────────────────────────────────────────────────
// A shop card is a location, so what the player pays for is whatever the
// multiworld put there -- not the plant on the front of the card.
const {
  st, sent, shopRewardLabel, scoutShopLocations,
  resetShopState, setLocations, applyLocationInfo, setGames, setSlots, getScout,
} = require('./store_fn.js');

const SHOP = ['Shop: iceweed', 'Shop: chomper', 'Shop: upgrade_8_slots'];

function setupRoom(opts) {
  resetShopState(Object.assign({ shopsanity: true, apSlotId: 1 }, opts));
  setLocations(SHOP.concat(['egypt10', 'World Key - Ancient Egypt']));
  setSlots({ 1: 'PvZ2 Gardendless', 2: 'Super Metroid' },
           { 1: 'kurt', 2: 'friend' });
}

setupRoom();
scoutShopLocations();
{
  const scout = sent.find(p => p.cmd === 'LocationScouts');
  if (!scout) fail('no LocationScouts sent with shopsanity on');
  else if (scout.locations.length !== SHOP.length)
    fail(`scouted ${scout.locations.length} locations, expected ${SHOP.length}`);
  else if (scout.create_as_hint !== 0)
    fail('scout must not create hints (create_as_hint !== 0)');
  else ok(`scouts exactly the ${SHOP.length} shop locations, without hinting`);
}

resetShopState({ shopsanity: false, apSlotId: 1 });
setLocations(SHOP);
scoutShopLocations();
if (sent.length) fail('scouted with shopsanity off');
else ok('shopsanity off sends no scout');

setupRoom();
applyLocationInfo([
  { location: 3520000, item: 77, player: 1 },   // Shop: iceweed  -> ours
  { location: 3520001, item: 55, player: 2 },   // Shop: chomper  -> friend's
  { location: 3520003, item: 99, player: 1 },   // egypt10, not a shop card
]);
if (Object.keys(getScout()).length !== 2)
  fail('a non-shop location was recorded as a shop reward');
else ok('only shop locations are recorded from LocationInfo');

if (shopRewardLabel('iceweed') !== null)
  fail('labelled a card before the DataPackage arrived');
else ok('no DataPackage yet leaves the card as the game built it');

{
  const req = sent.filter(p => p.cmd === 'GetDataPackage').pop();
  if (!req) fail('no DataPackage requested for the scouted games');
  else if ([...req.games].sort().join(',') !== 'PvZ2 Gardendless,Super Metroid')
    fail('requested the wrong games: ' + req.games);
  else ok('requests names for exactly the games owning scouted items');
}

setGames({
  'PvZ2 Gardendless': { 77: 'Cherry Bomb' },
  'Super Metroid':    { 55: 'Morph Ball' },
});

if (shopRewardLabel('iceweed') !== 'Cherry Bomb')
  fail('own item mislabelled: ' + shopRewardLabel('iceweed'));
else ok('an item for this slot shows as just the item name');

if (shopRewardLabel('chomper') !== 'friend: Morph Ball')
  fail('other player mislabelled: ' + shopRewardLabel('chomper'));
else ok('another slot\'s item shows as "player: item"');

if (shopRewardLabel('upgrade_8_slots') !== null)
  fail('labelled a commodity that was never scouted');
else ok('an unscouted commodity keeps its own name');

if (shopRewardLabel('not_a_commodity') !== null)
  fail('labelled an unknown commodity');
else ok('an unknown commodity is handled');

setGames({ 'PvZ2 Gardendless': { 77: 'Cherry Bomb' } });
if (shopRewardLabel('chomper') !== null)
  fail('a missing game datapackage produced a label anyway');
else ok('an unnamed game leaves that card alone');

st.shopsanity = false;
if (shopRewardLabel('iceweed') !== null) fail('labelled a card with shopsanity off');
else ok('shopsanity off never relabels');
st.shopsanity = true;

// ── the hook actually writes the label onto the card ─────────────────────────
// The relabel runs off readCommodity()'s promise, so this has to be awaited.
(async () => {
  setupRoom();
  applyLocationInfo([{ location: 3520000, item: 77, player: 1 }]);
  setGames({ 'PvZ2 Gardendless': { 77: 'Cherry Bomb' } });

  const card = new SC();
  await card.readCommodity({ CommodityType: 'plant', CommodityName: 'iceweed' });
  if (card.nameLabel.string !== 'Cherry Bomb')
    fail(`card shows "${card.nameLabel.string}", expected "Cherry Bomb"`);
  else ok('the card ends up labelled with the reward, not the plant');

  const plain = new SC();
  await plain.readCommodity({ CommodityType: 'plant', CommodityName: 'chomper' });
  if (plain.nameLabel.string !== 'chomper')
    fail(`unscouted card was overwritten with "${plain.nameLabel.string}"`);
  else ok('an unscouted card keeps the name the game gave it');

  // a label lookup that throws must not stop the card being built
  const boom = new SC();
  const saved = window._AP_shopRewardLabel;
  window._AP_shopRewardLabel = () => { throw new Error('boom'); };
  let threw = null;
  try { await boom.readCommodity({ CommodityType: 'plant', CommodityName: 'iceweed' }); }
  catch (e) { threw = e; }
  window._AP_shopRewardLabel = saved;
  if (threw) fail('a throwing label lookup took the card down: ' + threw.message);
  else if (!boom.built) fail('a throwing label lookup stopped the card being built');
  else ok('a throwing label lookup cannot stop a card being built');

  console.log(failed ? `\n${failed} FAILURE(S)` : '\nSTORE HOOK OK');
  process.exit(failed ? 1 : 0);
})();
