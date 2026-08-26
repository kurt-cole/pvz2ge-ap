const window={};
function installStoreHook(SC) {
  if (!SC || SC._ap_hooked_store || !SC.prototype || !SC.prototype.unlockCommodity) return;
  const _origUnlockCommodity = SC.prototype.unlockCommodity;
  SC.prototype.unlockCommodity = function() {
    try {
      const c = this.currentCommodity;
      // Only the one-time purchases are checks; gem/coin/sprout bundles are
      // repeatable and have no CommodityName at all.
      if (c && c.CommodityName && window._AP_onShopPurchase &&
          (c.CommodityType === 'plant' || c.CommodityType === 'upgrade')) {
        window._AP_onShopPurchase(c.CommodityName);
      }
    } catch (e) { /* never block the purchase itself */ }
    return _origUnlockCommodity.apply(this, arguments);
  };

  // readCommodity() is what builds a store card, and it destroys its own
  // node when the commodity is already owned. Under AP "owned" is never
  // true for a plant or a shuffled upgrade (see _AP_isShopCommodityChecked),
  // so an already-bought card came back on every refresh of the screen.
  // Destroying it here reproduces the game's own behaviour, keyed on the
  // check instead of on ownership.
  if (SC.prototype.readCommodity) {
    const _origReadCommodity = SC.prototype.readCommodity;
    SC.prototype.readCommodity = function (props) {
      try {
        if (props && props.CommodityName && window._AP_isShopCommodityChecked &&
            window._AP_isShopCommodityChecked(props.CommodityName)) {
          this.currentCommodity = props;
          if (this.node && this.node.destroy) this.node.destroy();
          // The original is async and its early-out still resolves, so hand
          // back a promise rather than undefined for anything chaining off it.
          return Promise.resolve();
        }
      } catch (e) { /* fall through and build the card as normal */ }
      // Under shopsanity the card is a location, not a purchase: buying it
      // sends the check and grants nothing, so the plant on the front of it
      // is not what the player is paying for. Relabel it with the item the
      // multiworld actually has there.
      //
      // Has to run AFTER the original, which sets nameLabel partway through
      // its own async body -- writing first would just be overwritten. The
      // label is left alone when there is nothing scouted yet, so the card
      // reads as the game built it rather than going blank.
      const _card = this;
      const _dress = function (result) {
        // The logo goes on ONLY when the name was actually replaced. The two
        // say the same thing -- "this card is a location, the art is not what
        // you get" -- so a card that kept the game's own name keeps the game's
        // own art with it. That leaves the logo off the coin, gem and sprout
        // bundles, which are repeatable purchases with no CommodityName and no
        // location behind them, and off a card whose reward is not scouted
        // yet, which would otherwise read as a blank Archipelago logo with the
        // game's plant name under it.
        let relabelled = false;
        try {
          const label = props && props.CommodityName &&
                        window._AP_shopRewardLabel &&
                        window._AP_shopRewardLabel(props.CommodityName);
          if (label && _card.nameLabel) {
            _card.nameLabel.string = label;
            relabelled = true;
          }
        } catch (e) { /* a card with the old label beats no card */ }
        // Separate try: a failure to swap the art must not cost the label,
        // and neither may stop the card being built.
        if (relabelled) {
          try { dressCardWithLogo(_card); }
          catch (e) { /* the game's own art is a fine fallback */ }
        }
        return result;
      };
      const done = _origReadCommodity.apply(this, arguments);
      return (done && typeof done.then === 'function')
        ? done.then(_dress) : _dress(done);
    };
  }

  // Belt and braces for the live screen: the card the player just bought
  // from is already built, so it is not going through readCommodity() again
  // until the screen is rebuilt. unlockable() gates both the buy handler and
  // the button's grey-out, so this is what stops an immediate second
  // purchase. The check lands before the original unlockCommodity() runs --
  // the hook above fires it first -- so this reads true straight away.
  if (SC.prototype.unlockable) {
    const _origUnlockable = SC.prototype.unlockable;
    SC.prototype.unlockable = function () {
      try {
        const c = this.currentCommodity;
        if (c && c.CommodityName && window._AP_isShopCommodityChecked &&
            window._AP_isShopCommodityChecked(c.CommodityName)) return false;
      } catch (e) { /* fall through to the game's own answer */ }
      return _origUnlockable.apply(this, arguments);
    };
  }

  SC._ap_hooked_store = true;
}
// ── shopsanity card labels ───────────────────────────────────────────────────
// Harness state standing in for the client's module scope. The copied
// functions below close over exactly these names.
const st = {};
let apSlotId = 0;
const sent = [];
function send(p){ sent.push(...p); }
function svSt(){ /* localStorage in the real client */ }

let itemNamesByGame = {};
let slotGame        = {};
let slotName        = {};
let shopScout       = {};
let locIds = {}, idToLoc = {};

function saveShopLabelCache(){
  st.itemNamesByGame = itemNamesByGame;
  st.slotGame        = slotGame;
  st.slotName        = slotName;
  st.shopScout       = shopScout;
  svSt();
}

let slotLocationIds = new Set();
function setSlotLocations(ids){ slotLocationIds = new Set(ids || []); }
// Copied verbatim from build_pvzge_ap.py.
function slotHasLocation(id){
  return !slotLocationIds.size || slotLocationIds.has(id);
}

function scoutShopLocations(){
  if(!st.shopsanity) return;
  const ids = Object.keys(locIds)
    .filter(n => n.startsWith('Shop: '))
    .map(n => locIds[n])
    .filter(id => id && slotHasLocation(id));
  if(!ids.length) return;   // DataPackage not in yet; it re-runs this on arrival
  send([{cmd:'LocationScouts', locations:ids, create_as_hint:0}]);
}

function fetchScoutedGames(){
  const wanted = new Set();
  for(const cn of Object.keys(shopScout)){
    const game = slotGame[shopScout[cn].player];
    if(game && !itemNamesByGame[game]) wanted.add(game);
  }
  if(wanted.size) send([{cmd:'GetDataPackage', games:[...wanted]}]);
}

function shopRewardLabel(commodityName){
  if(!st.shopsanity) return null;
  const scouted = shopScout[commodityName];
  if(!scouted) return null;
  const names = itemNamesByGame[slotGame[scouted.player]];
  const item  = names && names[scouted.item];
  if(!item) return null;
  // Own slot: just the item. Someone else's: whose it is matters more than
  // anything else on the card, so it leads.
  return scouted.player === apSlotId ? item
       : (slotName[scouted.player] || 'Player ' + scouted.player) + ': ' + item;
}

window._AP_shopRewardLabel = shopRewardLabel;

function resetShopState(opts){
  for(const k of Object.keys(st)) delete st[k];
  Object.assign(st, opts || {});
  apSlotId = (opts && opts.apSlotId) || 0;
  sent.length = 0;
  itemNamesByGame = {}; slotGame = {}; slotName = {}; shopScout = {};
  locIds = {}; idToLoc = {};
}

function setLocations(names){
  locIds = {}; idToLoc = {};
  let id = 3520000;
  for(const n of names){ locIds[n] = id; idToLoc[id] = n; id++; }
}

// Mirrors the client's LocationInfo case, which is a switch arm rather than a
// function and so cannot be copied verbatim. Kept deliberately thin.
function applyLocationInfo(locations){
  let found = 0;
  for(const it of locations){
    const name = idToLoc[it.location];
    if(!name || !name.startsWith('Shop: ')) continue;
    shopScout[name.slice(6)] = {item: it.item, player: it.player};
    found++;
  }
  if(found){ saveShopLabelCache(); fetchScoutedGames(); }
  return found;
}

module.exports = {
  setSlotLocations,
  installStoreHook, window, st, sent,
  shopRewardLabel, scoutShopLocations, fetchScoutedGames,
  resetShopState, setLocations, applyLocationInfo,
  setGames: g => { itemNamesByGame = g; },
  setSlots: (games, names) => { slotGame = games; slotName = names || {}; },
  getScout: () => shopScout,
};

// ── AP logo on the card ──────────────────────────────────────────────────────
let _apCC = null;
let _apLogoFrame = null;
const AP_LOGO_NODE = 'ap-logo';
const AP_LOGO_SIZE = 110;
const AP_LOGO_Y    = -40;

function dressCardWithLogo(card) {
  if (!window._AP_shopsanity || !_apCC || !_apLogoFrame) return;
  const slot = card && card.displaySlot;
  if (!slot || !slot.children) return;
  for (const child of slot.children.slice()) {
    if (child && child.name !== AP_LOGO_NODE) child.active = false;
  }
  let node = slot.getChildByName && slot.getChildByName(AP_LOGO_NODE);
  if (!node) {
    node = new _apCC.Node(AP_LOGO_NODE);
    const transform = node.addComponent(_apCC.UITransform);
    if (transform.setContentSize) transform.setContentSize(AP_LOGO_SIZE, AP_LOGO_SIZE);
    const sprite = node.addComponent(_apCC.Sprite);
    // CUSTOM, or Sprite sizes itself from the 128px source and ignores the
    // content size set above.
    if (_apCC.Sprite.SizeMode) sprite.sizeMode = _apCC.Sprite.SizeMode.CUSTOM;
    sprite.spriteFrame = _apLogoFrame;
    node.parent = slot;
  }
  if (node.setPosition) node.setPosition(0, AP_LOGO_Y, 0);
  node.active = true;
}

module.exports.dressCardWithLogo = dressCardWithLogo;
module.exports.setLogoDeps = (cc, frame) => { _apCC = cc; _apLogoFrame = frame; };
