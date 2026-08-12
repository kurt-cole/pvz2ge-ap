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
        return _origReadCommodity.apply(this, arguments);
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
module.exports={installStoreHook, window};
