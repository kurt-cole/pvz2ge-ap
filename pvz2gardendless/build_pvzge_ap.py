"""
PvZ2 Gardendless Archipelago - Automated Builder
=================================================
Clones the game source, patches tmpPatch.js with the AP client,
and builds a ready-to-run exe — all in a folder you choose.

Requirements:
  - Python 3.8+  (you have this if you have Archipelago)
  - Node.js 18+  (https://nodejs.org)
  - Git           (https://git-scm.com)
  - Internet connection for the initial clone (~500MB)

Usage: double-click this file, or run:
  python build_pvzge_ap.py
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog
import queue

# The Archipelago logo, inlined so the injected client stays a single
# self-contained file -- devrun.py rewrites only tmpPatch.js, so a sibling
# image would go missing on the fast path. 128x128 PNG, downscaled from the
# 512x512 icon.png that ships with the Archipelago install
# (C:/ProgramData/Archipelago/data/icon.png on Windows). Substituted into the
# client below, rather than pasted into it, to keep ~180 lines of base64 out
# of the JS.
AP_LOGO_PNG = "data:image/png;base64,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"

# ── AP client code to inject into tmpPatch.js ────────────────────────────────
# This replaces the original tmpPatch.js entirely.
TMPPATCH_CONTENT = r"""
// PvZ2 Gardendless — Archipelago Client
// Injected via automated build. See https://github.com/Twig6943/PVZGE-Electron

// ── Electron shim (original tmpPatch.js functionality) ───────────────────────
const electron = {
  isFullscreen: () => !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement),
  enterFullscreen: (el = document.documentElement) => { (el.requestFullscreen || el.mozRequestFullScreen || el.webkitRequestFullscreen || el.msRequestFullscreen || (() => {})).call(el); },
  exitFullscreen: () => { if (electron.isFullscreen()) (document.exitFullscreen || document.mozCancelFullScreen || document.webkitExitFullscreen || document.msExitFullscreen || (() => {})).call(document); },
  ipcRenderer: {
    send(ch, ...data) {
      if (ch === 'e_fullScreen') return electron.isFullscreen() ? electron.exitFullscreen() : electron.enterFullscreen();
      if (ch === 'e_window') return electron.exitFullscreen();
      if (ch === 'e_openURL') return window.open(data[0], '_blank');
    },
    sendSync(ch) { if (ch === 'e_isFullScreen') return electron.isFullscreen(); },
    on() {}
  },
  shell: { openExternal: url => window.open(url, '_blank') }
};
window.electron = electron;

// ── AP save slot redirect: inject PlayerIndex into PvZ2_Settings reads ────────
// This runs before any game code, so the game's mainScene.onLoad picks up our
// slot index when it calls getSettings().PlayerIndex.
(function(){
  const AP_SLOT_IDX_KEY = 'ap_pvz2_slot_idx';
  const SETTINGS_KEY = 'PvZ2_Settings';
  const SAVE_KEY     = 'PvZ2_PlayerProperties';
  const _origGet = Storage.prototype.getItem;

  // Resolve which save slot is ours, preferring the _ap_managed marker over
  // the stored index. The index alone is not safe: it is a fixed number into
  // an array whose length changes, and the game's getPlayer() reacts to an
  // out-of-range PlayerIndex by building a fresh player and PUSHING it --
  // which lands at allPlayers.length, not necessarily at PlayerIndex. Once
  // that happens the loaded player is a different object from the one we
  // write to, it starts with coin/gem 0, and everything saved into the old
  // slot is invisible from then on.
  function resolveApIdx() {
    let stored = parseInt(_origGet.call(localStorage, AP_SLOT_IDX_KEY), 10);
    if (isNaN(stored) || stored < 0) stored = -1;
    let players;
    try { players = JSON.parse(_origGet.call(localStorage, SAVE_KEY) || '[]'); }
    catch (e) { return stored; }
    if (!Array.isArray(players)) return stored;
    const marked = players.findIndex(p => p && p._ap_managed === true);
    if (marked >= 0) return marked;
    // Marker missing (older save, or the game replaced the object). Keep the
    // stored index only while it still points at something real -- forcing an
    // out-of-range PlayerIndex is what triggers the push-mismatch above.
    return (stored >= 0 && stored < players.length) ? stored : -1;
  }

  Storage.prototype.getItem = function(key) {
    const v = _origGet.call(this, key);
    if (key === SETTINGS_KEY) {
      const apIdx = resolveApIdx();
      if (apIdx >= 0) {
        try {
          const s = v ? JSON.parse(v) : {};
          s.PlayerIndex = apIdx;
          return JSON.stringify(s);
        } catch(e) {}
      }
    }
    return v;
  };
})();

// ── Capture AllPlayerProperties from SystemJS ─────────────────────────────────
// The game uses SystemJS module loading. We intercept the module registration
// for PlayerProperties.ts to capture AllPlayerProperties before the game starts.
// This gives us a live reference to the in-memory player data object.
(function() {
  // Returns a Proxy around a plantProps object that silently blocks writes for
  // any plant codename AP hasn't granted yet.  Uses window._AP_CN_TO_ID (set
  // up in the AP client IIFE after ID_TO_CN is built) to map codename→plantId.
  function makeGuardedProxy(target) {
    return new Proxy(target, {
      set(obj, key, value) {
        if (typeof key === 'string') {
          const cnToId = window._AP_CN_TO_ID;
          if (cnToId && Object.prototype.hasOwnProperty.call(cnToId, key)) {
            const granted = window._AP_grantedPlantIds || new Set();
            if (!granted.has(cnToId[key])) return true; // block — not AP-granted
          }
        }
        return Reflect.set(obj, key, value);
      }
    });
  }

  function installCurrentPlayerHooks(cp) {
    if (!cp || cp._ap_hooked_cp) return;
    // Intercept plantProps on the current player instance.
    // Using defineProperty so future reassignments of plantProps are also caught.
    let _pp = cp.plantProps;
    if (_pp && typeof _pp === 'object' && !_pp._ap_proxied) {
      _pp = makeGuardedProxy(_pp);
      _pp._ap_proxied = true;
    }
    Object.defineProperty(cp, 'plantProps', {
      get() { return _pp; },
      set(v) {
        if (v && typeof v === 'object' && !v._ap_proxied) {
          _pp = makeGuardedProxy(v);
          _pp._ap_proxied = true;
        } else { _pp = v; }
      },
      configurable: true, enumerable: true,
    });
    cp._ap_hooked_cp = true;
  }

  function installAPHooks(app) {
    // app = AllPlayerProperties (static class, not an instance)
    if (!app || app._ap_hooked) return; // never wrap twice

    // Layer 1: intercept the static unlockPlant() method.
    if (app.unlockPlant) {
      const _origUnlockPlant = app.unlockPlant.bind(app);
      app.unlockPlant = function(plantId) {
        const granted = window._AP_grantedPlantIds || new Set();
        if (!granted.has(plantId)) return;
        return _origUnlockPlant(plantId);
      };
    }

    // Permanent upgrades, same shape as the plant guard above. The game's own
    // upgrade loop applies an upgrade when its upgradeProps entry has
    // progress > 0 and enabled, and unlockUpgrade() is the single place that
    // sets progress -- both the level-reward path and the store purchase go
    // through it -- so blocking here withholds an upgrade however it was
    // earned. Only active when slot_data turned shuffle_upgrades on: seeds
    // generated before that option existed ship no upgrade items, so
    // withholding on them would mean never getting an upgrade at all.
    if (app.unlockUpgrade) {
      const _origUnlockUpgrade = app.unlockUpgrade.bind(app);
      app.unlockUpgrade = function(codename) {
        if (window._AP_shuffleUpgrades) {
          const granted = window._AP_grantedUpgrades || new Set();
          if (!granted.has(codename)) return;
        }
        return _origUnlockUpgrade(codename);
      };
    }

    // Layer 2: hook getPlayer so we install a plantProps Proxy on whichever
    // currentPlayer slot the game (or we) load.  AllPlayerProperties.plantProps
    // is undefined — the real data lives on currentPlayer.plantProps.
    if (app.getPlayer) {
      const _origGetPlayer = app.getPlayer.bind(app);
      app.getPlayer = function(idx) {
        const result = _origGetPlayer(idx);
        installCurrentPlayerHooks(app.currentPlayer);
        return result;
      };
    }

    // Layer 3: suppress the "first placement" description tip for every
    // plant, owned or not. The game decides via
    //   isTeacher = !(getPlantProgressByID(id).tutorialLevel > 0)
    // and this getter *creates* a fresh entry with tutorialLevel 0 for any
    // plant missing from plantProps. Plants AP hasn't granted are exactly the
    // ones rebuildAPSave() strips on every poll, so the entry is recreated at
    // 0 each time and the tip replays forever. Setting tutorialLevel on the
    // returned object covers granted and ungranted plants through one place,
    // whatever route the game took to get here.
    if (app.getPlantProgressByID) {
      const _origGetPlantProgress = app.getPlantProgressByID.bind(app);
      app.getPlantProgressByID = function(plantId) {
        const progress = _origGetPlantProgress(plantId);
        if (progress && !(progress.tutorialLevel > 0)) progress.tutorialLevel = 1;
        return progress;
      };
    }

    app._ap_hooked = true;
  }

  // DeathLink outgoing hook: the UI class's loseDarken() is the game's single
  // entry point for ending a level as a loss (screen darken + lose music +
  // gameLost flag), called from every death cause in the game (brain eaten,
  // ship destroyed, TNT trigger, etc.) -- so hooking it here catches all of
  // them without needing to special-case each cause site.
  function installUILoseHook(UI) {
    if (!UI || UI._ap_hooked_ui || !UI.prototype || !UI.prototype.loseDarken) return;
    const _origLoseDarken = UI.prototype.loseDarken;
    UI.prototype.loseDarken = function() {
      if (window._AP_onGameLose) window._AP_onGameLose();
      return _origLoseDarken.apply(this, arguments);
    };
    UI._ap_hooked_ui = true;
  }

  // Module export name -> what to do with the captured value. Note the
  // exported symbol is not always the filename: UI.ts exports 'UIInGame'.
  // CoinCount/GemCount are captured so currency can be granted through their
  // addCoinCount/addGemCount methods rather than by writing currentPlayer
  // directly -- those components snapshot currentPlayer.coin in start() and
  // write their own cached value back on every change, so a direct write
  // behind a live component's back gets stomped the next time it updates.
  const _AP_CAPTURES = {
    'AllPlayerProperties': function(v) {
      window._AP_AllPlayerProperties = v;
      // Install hooks immediately so BASEUNLOCKLIST calls are intercepted
      installAPHooks(v);
    },
    'UIInGame': function(v) { window._AP_UI = v; installUILoseHook(v); },
    // Lower-case l: levelController.ts exports 'levelController', not
    // 'LevelController'. module_SetConveyor lives on its prototype.
    'levelController': function(v) { window._AP_levelController = v; installConveyorHook(v); },
    'CoinCount': function(v) { window._AP_CoinCount = v; },
    'GemCount':  function(v) { window._AP_GemCount  = v; },
    // Square.getLane(0..4) is how the Lawn Mower Trap reaches each lane's
    // mower.
    'Square':    function(v) { window._AP_Square    = v; },
    'StoreCommodity': function(v) { installStoreHook(v); },
    // Lower-case z on purpose: Zombies.ts exports the static resolver class as
    // 'zombies'. The capitalised 'Zombies' export in the same module is the
    // Cocos component and carries none of the type-resolution statics.
    'zombies':   function(v) { window._AP_zombies = v; installZombieHook(v); },
  };

  // Shopsanity: unlockCommodity() is the single point every completed store
  // purchase passes through, and it still holds the commodity being bought,
  // so hooking it catches plants and upgrades alike without touching the
  // buy-button or currency paths.
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

  // Archipelago logo on shopsanity store cards. With shopsanity on, a card is
  // a location rather than a purchase -- buying it sends the check and grants
  // nothing -- so the plant or trophy pictured on it is not what the player is
  // getting. The art is swapped for the AP logo to say so, alongside the label
  // swap that puts the real reward in the card's name.
  //
  // The image is inlined as a data URI (substituted in from AP_LOGO_PNG, see
  // build_pvzge_ap.py) so the client stays one self-contained file.
  const AP_LOGO_URI  = '__AP_LOGO_PNG__';
  const AP_LOGO_NODE = 'ap-logo';
  // The display slot is roughly square and the game hangs its own art below
  // centre (plants at y-30 after a 1.2 scale, upgrades at y-50), so this sits
  // between the two. Both are eyeball values -- adjust here if the logo sits
  // badly once it is on screen.
  const AP_LOGO_SIZE = 110;
  const AP_LOGO_Y    = -40;

  let _apCC = null;          // the real cc module, not the legacy window.cc
  let _apLogoFrame = null;   // built once, shared by every card

  // window.cc is only the legacy namespace shell in this build -- the classes
  // live in the SystemJS 'cc' module, which import-map.json maps to
  // cocos-js/cc.js. It is already loaded by the time any of this runs, so the
  // import resolves immediately.
  //
  // Every step is feature-detected and every failure is swallowed: if the
  // engine's shape is not what is expected here, the cards simply stay exactly
  // as the game drew them. A missing logo is cosmetic; a throw in a store
  // screen is not.
  function initApLogo() {
    if (_apLogoFrame || _apCC) return;
    if (typeof System === 'undefined' || typeof System.import !== 'function') return;
    try {
      System.import('cc').then(function (cc) {
        if (!cc || !cc.ImageAsset || !cc.Texture2D || !cc.SpriteFrame ||
            !cc.Sprite || !cc.Node || !cc.UITransform) return;
        _apCC = cc;
        const img = new Image();
        img.onload = function () {
          try {
            const texture = new cc.Texture2D();
            texture.image = new cc.ImageAsset(img);
            const frame = new cc.SpriteFrame();
            frame.texture = texture;
            _apLogoFrame = frame;
          } catch (e) { /* cards keep the art the game gave them */ }
        };
        img.src = AP_LOGO_URI;
      }).catch(function () { /* no cc module: nothing to draw with */ });
    } catch (e) { /* System.import threw synchronously */ }
  }

  // Swap a card's art for the logo. Existing children are HIDDEN, never
  // destroyed: the game builds them with instantiatePooly(), so they belong to
  // a node pool and destroying one corrupts the pool for every later card.
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

  // Conveyor randomization. levelController.module_SetConveyor() is handed the
  // level's ConveyorSeedBankProperties and builds the belt from its
  // InitialPlantList, so rewriting each entry's PlantType on the way in swaps
  // the plants while leaving MinCount/MaxCount/Weight -- the level's pacing --
  // exactly as designed.
  //
  // FNV-1a plus mulberry32: the roll has to be reproducible without any stored
  // state, so it is derived from the level's own untouched plant list rather
  // than from a counter or Math.random().
  function _apHash(str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
  function _apRng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function installConveyorHook(LC) {
    if (!LC || LC._ap_hooked_conveyor || !LC.prototype || !LC.prototype.module_SetConveyor) return;
    const _origSetConveyor = LC.prototype.module_SetConveyor;
    LC.prototype.module_SetConveyor = function (props) {
      let patched = props;
      try {
        const pool  = window._AP_conveyorPool;
        const swaps = window._AP_conveyorSwaps || {};
        if (window._AP_randomizeConveyor && props &&
            Array.isArray(props.InitialPlantList) && pool && pool.length) {
          const list  = props.InitialPlantList;
          const known = window._AP_conveyorKnown;
          // Seeded off the ORIGINAL plant types, which is what makes the roll
          // stable: the same level always produces the same belt, and a retry
          // is not a reroll. That only holds because nothing below writes back
          // to props -- the entries are copied, see the map() further down.
          const rnd = _apRng(_apHash(String(window._AP_conveyorSeed || 0) + '|' +
                                     list.map(e => (e && e.PlantType) || '').join('|')));
          // Does this lawn have deep water? Two signals, because the grid may
          // not be built yet when the conveyor is set: the game's own flag, and
          // failing that the level's own belt -- a level handing out a water
          // plant self-evidently has water. Fails CLOSED to "no water", so an
          // unreadable level loses aquatic swaps rather than gaining dead slots.
          let hasWater = false;
          try {
            const lc = window._AP_levelController;
            hasWater = !!(lc && lc.component && lc.component.haveWater);
          } catch (e) { /* fall through to the belt signal */ }
          if (!hasWater) {
            hasWater = list.some(e => e && window._AP_conveyorTerrainLocked.has(e.PlantType) &&
                                      e.PlantType !== 'goldleaf');
          }
          const used = new Set();
          const newList = list.map(function (entry) {
            // Only genuine plants are swapped. A conveyor also delivers
            // bowling projectiles, power tiles and potions on the minigame
            // levels (tool_projectile_*, tool_powertile_*, zombiepotion_*),
            // and turning those into plants makes the level unplayable.
            if (!entry || !known || !known.has(entry.PlantType)) return entry;
            // Swap within the plant's own group, so a belt keeps the shape the
            // level was built around: a sun producer stays a sun producer, a
            // one-shot stays a one-shot, and the replacement costs about what
            // the original did. A plant with no group -- nothing comparable to
            // trade it for -- is left as the level had it.
            const candidates = swaps[entry.PlantType];
            if (!candidates) return entry;
            // A terrain-locked plant the level placed itself is left exactly as
            // it was. Swapping a Big Wave Beach belt's Lily Pad for a Wall-nut
            // takes away the only thing that makes its water columns usable,
            // which is the same class of bug in the other direction.
            if (window._AP_conveyorTerrainLocked.has(entry.PlantType)) return entry;
            // Drop candidates this lawn cannot host, then apply the group rule
            // that a plant with nothing left to trade for stays put -- the
            // original is always in its own group, so fewer than two survivors
            // means there is no alternative.
            const usable = candidates.filter(cn => window._AP_conveyorPlantable(cn, hasWater));
            if (usable.length < 2) return entry;
            let pick = entry.PlantType;
            for (let tries = 0; tries < 20; tries++) {
              const candidate = usable[Math.floor(rnd() * usable.length)];
              // Keep one belt from being three copies of the same plant while
              // the group has alternatives. Bounded, so a small group still
              // terminates rather than spinning.
              if (!used.has(candidate)) { pick = candidate; break; }
              pick = candidate;
            }
            used.add(pick);
            return Object.assign({}, entry, { PlantType: pick });
          });
          // Copy rather than mutate. The level's properties object is cached
          // and handed back on a replay, so writing to it would feed the next
          // roll its own output and the level would drift on every attempt.
          patched = Object.assign(Object.create(Object.getPrototypeOf(props) || Object.prototype), props);
          patched.InitialPlantList = newList;
        }
      } catch (e) { /* never stop a level from loading over this */ }
      const args = Array.prototype.slice.call(arguments);
      args[0] = patched;
      return _origSetConveyor.apply(this, args);
    };
    LC._ap_hooked_conveyor = true;
  }

  // Zombie shuffle. zombies.getZombieEnumWithPropByZombieTypes() is the one
  // place every spawn path turns a zombie codename into the enum and property
  // sheet it spawns from -- wave spawners, gravestones, dropships, the level's
  // zombie preview cards and the generic lawn/lawn_armor placeholders all
  // resolve through it -- so rewriting the codename on the way in changes what
  // a level fields without touching wave timing, counts, lanes or objectives.
  //
  // The swap is confined to the codename's own tier (see _AP_zombieTiers, sent
  // from slot_data), so the trade is between zombies the game prices the same.
  // Anything with no tier is returned untouched: a Zomboss, a type no shipped
  // level spawns, or a lawn placeholder, which has no properties of its own and
  // is meant to resolve to the current stage's zombie -- that resolution
  // re-enters this hook with a real codename, so placeholders still shuffle.
  //
  // Keyed off the level ID and the ORIGINAL codename rather than any counter,
  // so the roll needs no stored state, a level always fields the same zombies,
  // and a retry is not a reroll.
  function _apLevelKey() {
    try {
      const ids = window._AP_levelController && window._AP_levelController.thisLevelsID;
      if (ids && ids.length) return ids.join(',');
    } catch (e) { /* fall through to the shared key */ }
    // Levels with no ID -- local test levels, Level of the Day -- share one
    // key. They still roll deterministically, just not per level.
    return '';
  }

  let _apZombieCacheKey = null;
  let _apZombieCache = {};
  let _apZombieBespoke = false;

  // Levels built AROUND particular zombies are left alone completely. A
  // minigame module drives its zombies structurally rather than merely
  // spawning them, so a swap there can leave the level unwinnable rather than
  // just different:
  //   CamelMinigameProperties   egypt7/16/23 -- you win by MATCHING camels on
  //                             hump count. Swapping them left nothing to
  //                             match. Found in play testing.
  //   CannonMinigameProperties  pirate3/11/20 field nothing but seagulls, and
  //                             a seagull flies in -- its flight is behaviour
  //                             on PirateSeagullZombie, not a property, so
  //                             there is no flag to partition it by.
  //   Beghouled / Bowling / LastStand / Cowboy / Future / Rhythm -- same
  //                             shape: the level is a set piece.
  // 84 of the 1134 shipped levels carry one of these. Every other level still
  // shuffles, which is the overwhelming majority of the game.
  //
  // This is the general answer to a class of bug that excluding zombie
  // families one at a time only ever patches case by case.
  const AP_BESPOKE_MODULES = /Minigame|Beghouled|Rhythm/;

  function _apLevelIsBespoke() {
    try {
      const lc = window._AP_levelController;
      const objs = lc && lc.component && lc.component.currentLevelObjects;
      // Fails CLOSED: if the level's object list cannot be read, assume it is
      // bespoke and do not shuffle. currentLevelObjects is filled in by
      // readLevelJson before any zombie is resolved, so an unreadable one
      // means something has moved -- and a level that does not shuffle is a
      // far cheaper mistake than one that cannot be beaten.
      if (!Array.isArray(objs) || !objs.length) return true;
      for (const o of objs) {
        if (o && AP_BESPOKE_MODULES.test(o.objclass || '')) return true;
      }
    } catch (e) { return true; }
    return false;
  }

  // Wave data does NOT name zombies by bare codename. Of the ~62000 type
  // references in the shipped levels, 57855 are RTID(codename@ZombieTypes) and
  // only ~4800 are bare -- the bare ones being the LawnProps role slots and a
  // few scripted spawns. The tier table is keyed by bare codename, so the
  // wrapper has to come off before the lookup and go back on after it.
  // Matching on the raw string instead means every wave spawn misses, which
  // looks exactly like the option doing nothing.
  const _AP_RTID = /^RTID\(([^@()]+)@([^()]*)\)$/;

  function _apZombieSwap(type) {
    const tierOf = window._AP_zombieTierOf;
    if (!tierOf) return type;
    const wrapped = _AP_RTID.exec(type);
    const codename = wrapped ? wrapped[1] : type;
    const tier = tierOf[codename];
    if (!tier) return type;
    const pool = window._AP_zombieTiers[tier];
    // A tier of one has nothing to trade for, so the level keeps what it had.
    if (!pool || pool.length < 2) return type;
    const levelKey = _apLevelKey();
    // Cache per level: this runs on every spawn, and the answer cannot change
    // within a level. Dropped wholesale when the level changes rather than
    // grown forever. Keyed by CODENAME, so the same zombie resolves the same
    // way whether the caller named it bare or as an RTID -- the level's zombie
    // preview cards and its actual spawns come through both ways.
    if (_apZombieCacheKey !== levelKey) {
      _apZombieCacheKey = levelKey;
      _apZombieCache = {};
      // Worked out once per level, not once per spawn: it walks the level's
      // whole object list.
      _apZombieBespoke = _apLevelIsBespoke();
    }
    if (_apZombieBespoke) return type;
    let pick = _apZombieCache[codename];
    if (pick === undefined) {
      const rnd = _apRng(_apHash(String(window._AP_zombieSeed || 0) + '|' +
                                 levelKey + '|' + codename));
      pick = pool[Math.floor(rnd() * pool.length)];
      _apZombieCache[codename] = pick;
    }
    // Always re-wrapped as @ZombieTypes rather than the scope it arrived in.
    // Every codename in the tier table is an alias in the game's global
    // ZombieTypes table, so that scope always resolves; a level that defines
    // its own type (RTID(x@CurrentLevel), 69 of those) has no entry for the
    // replacement under its local scope and would resolve to nothing.
    return wrapped ? 'RTID(' + pick + '@ZombieTypes)' : pick;
  }

  // The original recurses through itself to resolve lawn placeholders and
  // ZombieRedirection entries, and each of those re-enters this hook. The
  // depth cap is insurance only: the swap is a pure function of the codename,
  // so it cannot introduce a cycle the game did not already have, but this is
  // a per-spawn hot path and a runaway here would hang the level rather than
  // just look wrong.
  let _apZombieDepth = 0;

  function installZombieHook(Z) {
    if (!Z || Z._ap_hooked_zombies ||
        typeof Z.getZombieEnumWithPropByZombieTypes !== 'function') return;
    const _origGetZombieEnum = Z.getZombieEnumWithPropByZombieTypes;
    Z.getZombieEnumWithPropByZombieTypes = function (type) {
      const args = Array.prototype.slice.call(arguments);
      try {
        if (window._AP_shuffleZombies && typeof type === 'string' &&
            _apZombieDepth < 8) {
          args[0] = _apZombieSwap(type);
        }
      } catch (e) { /* never stop a zombie from spawning over this */ }
      _apZombieDepth++;
      try {
        return _origGetZombieEnum.apply(this, args);
      } finally {
        _apZombieDepth--;
      }
    };
    Z._ap_hooked_zombies = true;
  }

  window._AP_initApLogo = initApLogo;

  const _origRegister = System.register.bind(System);
  System.register = function(name, deps, declare) {
    if (typeof name === 'string' &&
        /(?:PlayerProperties|UI|CoinCount|GemCount|Square|StoreCommodity|levelController|Zombies)\.ts/.test(name)) {
      const _origDeclare = declare;
      declare = function(_export, _context) {
        return _origDeclare(function(exportName, value) {
          const capture = _AP_CAPTURES[exportName];
          if (capture) capture(value);
          return _export(exportName, value);
        }, _context);
      };
    }
    return _origRegister(name, deps, declare);
  };
})();

// ── Archipelago Client ────────────────────────────────────────────────────────
(function () {
  'use strict';

  const SAVE_KEY        = 'PvZ2_PlayerProperties';
  const SETTINGS_KEY    = 'PvZ2_Settings';
  const AP_SLOT_IDX_KEY = 'ap_pvz2_slot_idx';
  const CFG_KEY         = 'ap_pvz2_cfg';
  const STATE_KEY       = 'ap_pvz2_state';
  const GAME_NAME       = 'PvZ2 Gardendless';
  const AP_VER          = { major: 0, minor: 6, build: 7 };

  let skipTutorial = false; // set from slot_data on Connected

  // World enum IDs (from WorldMapSceneDisplayEnum in game source)
  // World enum IDs (WorldMapSceneDisplayEnum from game source)
  const W = { egypt:1, pirate:2, cowboy:3, future:4, dark:5, beach:6,
               iceage:7, lostcity:8, epic:9, eighties:10, dino:11, modern:12, kongfu:13, sky:26 };

  // Plant enum IDs (from PlantEnum in game source)
  const P = {
    Peashooter:0, Sunflower:1, Wallnut:2, PotatoMine:3, CabbagePult:4, Bloomerang:5,
    IcebergLettuce:6, BonkChoy:7, Repeater:8, ScaredyShroom:10, FumeShroom:11,
    GraveBuster:12, Pumpkin:13, PeaVine:14,
    FirePeashooter:16, ThreePeater:17, PrimalPea:18, Rotobaga:19, HomingThistle:20,
    StarFruit:21, ShootingStarfruit:22, LilyPad:23, SunShroom:24, TwinSunflower:25,
    Dragonbruit:26, Moonflower:27, SnowPea:28, LightningReed:29, KernelPult:30,
    MeteorFlower:31, SpringBean:32, UmbrellaLeaf:33, MelonPult:34, WinterMelon:35,
    Blover:36, Spikeweed:37, Spikerock:38, Chomper:39, GlacierShroom:40,
    PrimalWallnut:41, Buttercup:42,
    BananaLauncher:43, MissileToe:44, CherryBomb:45, DoomShroom:46, CranJelly:47,
    Torchwood:49, Jalapeno:50, PuffShroom:51, GloomVine:52, Vamporcini:53,
    PrimalPotatoMine:54, Cactus:55, PowerLily:56, CoconutCannon:57, PeaPod:58,
    SnapDragon:59, GatlingPea:60, SplitPea:61, ChiliBean:62, Tallnut:63,
    Hurrikale:64, Stallia:65, ElectricPeashooter:66, Squash:67, GloomShroom:68,
    MagnifyingGrass:69, CeleryStalker:70, Sapfling:71, Parsnip:72, ExplodeONut:73,
    Grapeshot:74, Plantern:75, HeavenlyPeach:76, JackOLantern:77, Dandelion:78,
    ChardGuard:79, HypnoShroom:80, ElectricCurrant:81, EscapeRoot:82, Imitater:83,
    ShadowShroom:84, MagnetShroom:85, Turnip:86, EMPeach:87, Citron:88, LaserBean:89,
    SolarTomato:90, InfiNut:96, TileTurnip:97, AppleMortar:106, RedStinger:107, Skyshooter:108,
    SunBean:109, Peanut:110, TangleKelp:114, BowlingBulb:115, Guacodile:120,
    GhostPepper:127, SweetPotato:128, PepperPult:129, HotPotato:130, Stunion:131,
    GoldLeaf:132, AKEE:133, Endurian:134, Toadstool:135, LavaGuava:136, PhatBeet:137,
    Strawburst:138, ThymeWarp:139, SeaShroom:141, Garlic:142, ElectricBlueBerry:143,
    SporeShroom:144, IntensiveCarrot:145, PrimalSunflower:146, MoonBean:147,
    ColdSnapDragon:148, NightShade:149, DuskLobber:150, Grimrose:151, GoldBloom:152,
    BloomingHeart:153, ShrinkingViolet:154, HotDate:155, FireGourd:156, BambooShoot:157,
    Snowdrop:158, Lychee:159, PerfumeShroom:160, SolarSage:161, Bamboozle:162,
    Cantaloupe:164, Iceweed:165
  };

  // id -> actual CODENAME from PlantFeatures.json (game's save key)
  // These are the exact strings used as keys in plantProps in the save data.
  // Generated from PlantFeatures.json - do NOT use P enum key names, they differ!
  const ID_TO_CN = {
    0:'peashooter', 1:'sunflower', 2:'wallnut', 3:'potatomine',
    4:'cabbagepult', 5:'bloomerang', 6:'iceburg', 7:'bonkchoy',
    8:'repeater', 10:'scaredyshroom', 11:'fumeshroom',
    12:'gravebuster', 13:'pumpkin', 14:'pvine',
    16:'firepeashooter', 17:'threepeater', 18:'primalpeashooter',
    19:'rotobaga', 20:'homingthistle', 21:'starfruit', 22:'shootingstarfruit',
    23:'lilypad', 24:'sunshroom', 25:'twinsunflower', 26:'dragonbruit',
    27:'moonflower', 28:'snowpea', 29:'lightningreed', 30:'kernelpult',
    31:'meteorflower', 32:'springbean', 33:'umbrellaleaf',
    34:'melonpult', 35:'wintermelon', 36:'blover', 37:'spikeweed',
    38:'spikerock', 39:'chomper', 40:'glaciershroom',
    41:'primalwallnut', 42:'buttercup',
    43:'banana', 44:'missiletoe', 45:'cherry_bomb', 46:'doomshroom',
    47:'cranjelly', 49:'torchwood', 50:'jalapeno', 51:'puffshroom',
    52:'gloomvine', 53:'vamporcini', 54:'primalpotatomine',
    55:'cactus', 56:'powerlily', 57:'coconutcannon', 58:'peapod',
    59:'snapdragon', 60:'gatling', 61:'splitpea', 62:'chilibean',
    63:'tallnut', 64:'hurrikale', 65:'stallia', 66:'electricpeashooter',
    67:'squash', 68:'gloomshroom', 69:'magnifyinggrass', 70:'celerystalker',
    71:'sapfling', 72:'parsnip', 73:'explodeonut', 74:'grapeshot',
    75:'plantern', 76:'peach', 77:'jackolantern', 78:'dandelion',
    79:'chardguard', 80:'hypnoshroom', 81:'electriccurrant',
    82:'escaperoot', 83:'imitater', 84:'shadowshroom', 85:'magnetshroom',
    86:'turnip', 87:'empea', 88:'citron', 89:'laser_bean', 90:'solartomato',
    96:'holonut', 97:'powerplant', 106:'applemortar', 107:'redstinger', 108:'skyshooter',
    109:'sunbean', 110:'peanut', 114:'tanglekelp', 115:'bowlingbulb',
    120:'guacodile', 127:'ghostpepper', 128:'sweetpotato', 129:'pepperpult',
    130:'hotpotato', 131:'stunion', 132:'goldleaf', 133:'akee',
    134:'endurian', 135:'toadstool', 136:'lavaguava', 137:'phatbeet',
    138:'strawburst', 139:'thymewarp', 141:'seashroom', 142:'garlic',
    143:'electricblueberry', 144:'sporeshroom', 145:'intensivecarrot',
    146:'primalsunflower', 147:'moonbean', 148:'coldsnapdragon',
    149:'nightshade', 150:'dusklobber', 151:'grimrose', 152:'goldbloom',
    153:'bloominghearts', 154:'shrinkingviolet', 155:'hotdate',
    156:'firegourd', 157:'bambooshoot', 158:'snowdrop', 159:'lychee',
    160:'perfumeshroom', 161:'solarsage', 162:'bamboozle',
    164:'cantaloupe', 165:'iceweed',
  };

  // Reverse map exposed for the plantProps Proxy in the SystemJS hook IIFE above.
  window._AP_CN_TO_ID = {};
  for (const pid in ID_TO_CN) window._AP_CN_TO_ID[ID_TO_CN[pid]] = Number(pid);

  // How many costumes each plant has, from the game's PlantFeatures table
  // (its COSTUME field). Costume indices for a plant run 0..count-1, which is
  // how getAvailablePlantCostumeList() enumerates them. Only the plants
  // Archipelago manages are listed: 120 of them, 309 costumes between them.
  const PLANT_COSTUMES = {
    0:10, 1:8, 2:9, 3:3, 4:6, 5:3, 6:5, 7:10, 8:9, 10:2, 11:2, 12:3, 13:1, 14:1, 16:1, 17:3,
    18:2, 19:2, 20:1, 21:2, 23:1, 24:4, 25:8, 27:1, 28:5, 29:5, 30:5, 32:3, 33:1, 34:4,
    35:4, 36:3, 37:4, 38:3, 39:1, 41:2, 42:1, 43:1, 44:3, 45:3, 46:2, 49:4, 50:1, 51:2,
    54:2, 55:2, 56:3, 57:3, 58:2, 59:5, 60:1, 61:3, 62:3, 63:6, 64:1, 65:2, 66:1, 67:3,
    69:3, 70:2, 71:1, 72:2, 73:1, 74:2, 75:2, 76:1, 77:3, 78:2, 79:3, 80:2, 81:2, 82:3,
    84:1, 85:1, 86:1, 87:3, 88:3, 89:3, 90:2, 96:3, 97:4, 106:1, 107:2, 108:1, 109:1, 110:1,
    114:2, 120:1, 127:2, 128:1, 129:4, 130:1, 131:2, 132:3, 133:2, 134:2, 135:2, 136:2,
    137:2, 138:2, 139:2, 142:2, 143:2, 144:2, 145:2, 146:2, 148:2, 149:1, 150:2, 151:2,
    152:2, 153:2, 154:2, 155:1, 156:1, 157:1, 160:2, 161:1, 164:2, 165:1
  };

  // Conveyor swap groups: which plants count as interchangeable when the belt
  // is randomized. Keyed role:tier, where role separates plants that stay on
  // the lawn from those consumed or timed out, and sun producers from both --
  // a conveyor level that hands out Sunflower and gets an attacker back has no
  // sun economy left and cannot be won. tier buckets the game's own sun cost,
  // which is its pricing of a plant's power: budget <75, low 75-149,
  // mid 150-249, high 250+.
  //
  // Derived from the game's own tables, not by hand -- _PLANTPROPERTIES for
  // Cost / IsConsumable / Lifetime and PlantProps for Family. rotobaga is
  // absent because it has no sun cost anywhere in the data, so it is left
  // alone rather than guessed at.
  const CONVEYOR_GROUPS = {
    'sustained:mid': [
      'akee', 'bambooshoot', 'bamboozle', 'bloomerang', 'bloominghearts', 'bonkchoy',
      'bowlingbulb', 'cactus', 'chomper', 'coldsnapdragon', 'doomshroom', 'dragonbruit',
      'dusklobber', 'electricblueberry', 'electriccurrant', 'electricpeashooter',
      'firegourd', 'firepeashooter', 'hotdate', 'iceweed', 'jackolantern', 'laser_bean',
      'lychee', 'parsnip', 'peanut', 'pepperpult', 'phatbeet', 'primalpeashooter',
      'pumpkin', 'pvine', 'redstinger', 'repeater', 'skyshooter', 'snapdragon',
      'snowdrop', 'snowpea', 'sporeshroom', 'starfruit', 'sweetpotato', 'torchwood'
    ],
    'sustained:low': [
      'cabbagepult', 'chardguard', 'cranjelly', 'endurian', 'fumeshroom', 'gloomvine',
      'guacodile', 'intensivecarrot', 'kernelpult', 'lightningreed', 'magnetshroom',
      'nightshade', 'peach', 'peapod', 'peashooter', 'primalwallnut', 'sapfling',
      'spikeweed', 'splitpea', 'tallnut', 'umbrellaleaf', 'vamporcini'
    ],
    'single-use:budget': [
      'blover', 'chilibean', 'empea', 'escaperoot', 'goldbloom', 'goldleaf',
      'gravebuster', 'hotpotato', 'iceburg', 'potatomine', 'primalpotatomine',
      'shadowshroom', 'shrinkingviolet', 'solarsage', 'squash', 'stallia', 'stunion',
      'sunbean', 'tanglekelp'
    ],
    'sustained:high': [
      'applemortar', 'banana', 'cantaloupe', 'citron', 'coconutcannon', 'dandelion',
      'gatling', 'glaciershroom', 'gloomshroom', 'homingthistle', 'melonpult',
      'meteorflower', 'missiletoe', 'shootingstarfruit', 'spikerock', 'strawburst',
      'threepeater', 'wintermelon'
    ],
    'sustained:budget': [
      'buttercup', 'celerystalker', 'explodeonut', 'garlic', 'imitater', 'lilypad',
      'moonflower', 'puffshroom', 'scaredyshroom', 'seashroom', 'springbean', 'turnip',
      'wallnut'
    ],
    'single-use:low': [
      'ghostpepper', 'grimrose', 'hurrikale', 'hypnoshroom', 'jalapeno', 'lavaguava',
      'solartomato', 'thymewarp'
    ],
    'single-use:mid': [
      'cherry_bomb', 'grapeshot', 'perfumeshroom', 'powerlily'
    ],
    'sun:budget': [
      'magnifyinggrass', 'moonbean', 'sunflower', 'sunshroom'
    ],
    'sun:low': [
      'plantern', 'primalsunflower', 'twinsunflower'
    ],
    'sun:mid': [
      'toadstool'
    ]
  };

  // Conveyor randomization pool, also exposed for the hook in that IIFE.
  // Neither of these two is a plant you would hand a player off a belt:
  // powerplant is what a power tile turns into, and holonut is Infi-nut's
  // hologram. A level that puts either on its conveyor is doing something
  // specific with it, so they are excluded from the pool AND left in place
  // when they appear -- the hook only swaps entries it finds in this set.
  const CONVEYOR_EXCLUDE = new Set(['powerplant', 'holonut']);
  window._AP_conveyorPool  = Object.values(ID_TO_CN).filter(cn => !CONVEYOR_EXCLUDE.has(cn));
  window._AP_conveyorKnown = new Set(window._AP_conveyorPool);

  // Plants the lawn itself has to be able to host. A belt slot holding one of
  // these on a lawn that cannot take it is a dead slot: the player is handed a
  // plant with nowhere to put it. Kurt hit this in play testing -- an Ancient
  // Egypt level dealt out Lily Pad and Tangle Kelp, neither placeable on a
  // waterless lawn.
  //
  // The game makes exactly this check itself before offering a plant, so this
  // mirrors it rather than inventing a rule:
  //     haveWater || TYPE.indexOf("aquatic") == -1 && TYPE.indexOf("lilypad") == -1
  // Those TYPE tags are the live authority. The property that names water
  // plants in the resource files, IsZenGardenWaterPlant, appears ZERO times in
  // index.js and comes from a sheet the game never loads.
  //
  // seashroom is here on Kurt's word, not on data, and that gap is the point:
  // it has NO _PLANTPROPERTIES sheet at all, so the property route reported
  // "not flagged as water" when the honest answer was "unknown". A missing
  // sheet is not an absent property. 24 other plants in CONVEYOR_GROUPS have no
  // sheet either, so this list is a floor rather than a proof -- the durable fix
  // is to read each plant's own TYPE tags at runtime through
  // Plants.ts getPlantFeature(id), keyed by the ids already in ID_TO_CN.
  const CONVEYOR_WATER_ONLY = new Set(['lilypad', 'tanglekelp', 'seashroom']);

  // Needs a specific tile under it, from the live PlantProperties TileType:
  // goldleaf wants a goldtile, which only some Lost City levels lay down.
  // Unlike water there is no cheap level-wide flag for "this lawn has gold
  // tiles", so it is never swapped IN anywhere. A level that puts it on its own
  // belt keeps it -- see the terrain check in the hook.
  const CONVEYOR_TILE_LOCKED = new Set(['goldleaf']);

  // Can this lawn host this plant at all? Terrain only; the group system
  // already handles role and cost.
  window._AP_conveyorPlantable = function (cn, hasWater) {
    if (CONVEYOR_TILE_LOCKED.has(cn)) return false;
    if (CONVEYOR_WATER_ONLY.has(cn)) return !!hasWater;
    return true;
  };
  window._AP_conveyorTerrainLocked = new Set([
    ...CONVEYOR_WATER_ONLY, ...CONVEYOR_TILE_LOCKED,
  ]);

  // codename -> the list of plants it may be swapped for. Built here rather
  // than stored per plant so CONVEYOR_GROUPS above stays readable as groups.
  // A plant whose group has fewer than two usable members is left out
  // entirely, which the hook reads as "do not swap this one" -- swapping a
  // plant for itself is churn, and there is nothing else in its power band to
  // reach for. That is currently toadstool, the only mid-cost sun producer.
  window._AP_conveyorSwaps = {};
  for (const key of Object.keys(CONVEYOR_GROUPS)) {
    const members = CONVEYOR_GROUPS[key].filter(cn => !CONVEYOR_EXCLUDE.has(cn));
    if (members.length < 2) continue;
    for (const cn of members) window._AP_conveyorSwaps[cn] = members;
  }

  // Mirrors the conveyor slot_data onto window for that hook. Persisted on st
  // so a page reload keeps randomizing before the socket is back up, and read
  // as off when absent -- which is what seeds predating the option do.
  function syncConveyorConfig() {
    window._AP_randomizeConveyor = !!st.randomizeConveyor;
    window._AP_conveyorSeed      = st.conveyorSeed || 0;
  }

  // Same idea for the zombie shuffle. The tiers come from slot_data rather
  // than being duplicated here, so generation and the client cannot disagree
  // about which trades are legal; the codename -> tier index is inverted once
  // on arrival because the hook runs on every spawn.
  function syncZombieConfig() {
    window._AP_shuffleZombies = !!st.shuffleZombies;
    window._AP_zombieSeed     = st.zombieSeed || 0;
    window._AP_zombieTiers    = st.zombieTiers || {};
    const tierOf = {};
    for (const tier of Object.keys(window._AP_zombieTiers)) {
      for (const cn of window._AP_zombieTiers[tier]) tierOf[cn] = tier;
    }
    window._AP_zombieTierOf = tierOf;
  }

  // AP item name -> plant enum ID
  const ITEM_PLANT = {
    'Primal Peashooter':P.PrimalPea,'Scaredy-shroom':P.ScaredyShroom,
    'Fume-Shroom':P.FumeShroom,'Ice-shroom':P.GlacierShroom,
    'Infi-nut':P.InfiNut,'Resistant Radish':P.Turnip,
    'Peashooter':P.Peashooter,'Sunflower':P.Sunflower,'Wall-nut':P.Wallnut,
    'Potato Mine':P.PotatoMine,'Cabbage-pult':P.CabbagePult,'Bloomerang':P.Bloomerang,
    'Iceberg Lettuce':P.IcebergLettuce,'Bonk Choy':P.BonkChoy,'Repeater':P.Repeater,
    'Grave Buster':P.GraveBuster,'Pumpkin':P.Pumpkin,'Pea Vine':P.PeaVine,
    'Fire Peashooter':P.FirePeashooter,'Threepeater':P.ThreePeater,'Rotobaga':P.Rotobaga,
    'Homing Thistle':P.HomingThistle,'Star Fruit':P.StarFruit,
    'Shooting Starfruit':P.ShootingStarfruit,'Lily Pad':P.LilyPad,
    'Sun-Shroom':P.SunShroom,'Twin Sunflower':P.TwinSunflower,'Dragon Fruit':P.Dragonbruit,
    'Moonflower':P.Moonflower,'Snow Pea':P.SnowPea,'Lightning Reed':P.LightningReed,
    'Kernel-pult':P.KernelPult,'Meteor Flower':P.MeteorFlower,'Spring Bean':P.SpringBean,
    'Umbrella Leaf':P.UmbrellaLeaf,'Melon-Pult':P.MelonPult,'Winter Melon':P.WinterMelon,
    'Blover':P.Blover,'Spikeweed':P.Spikeweed,'Spikerock':P.Spikerock,'Chomper':P.Chomper,
    'Primal Wall-nut':P.PrimalWallnut,'Buttercup':P.Buttercup,
    'Banana Launcher':P.BananaLauncher,'Missile Toe':P.MissileToe,
    'Cherry Bomb':P.CherryBomb,'Doom-shroom':P.DoomShroom,'Cran-Jelly':P.CranJelly,
    'Torchwood':P.Torchwood,'Jalapeno':P.Jalapeno,'Puff-shroom':P.PuffShroom,
    'Gloom Vine':P.GloomVine,'Vamporcini':P.Vamporcini,
    'Primal Potato Mine':P.PrimalPotatoMine,'Cactus':P.Cactus,'Power Lily':P.PowerLily,
    'Coconut Cannon':P.CoconutCannon,'Pea Pod':P.PeaPod,'Snap Dragon':P.SnapDragon,
    'Gatling Pea':P.GatlingPea,'Split Pea':P.SplitPea,'Chili Bean':P.ChiliBean,
    'Tall-nut':P.Tallnut,'Hurrikale':P.Hurrikale,'Stallia':P.Stallia,
    'Electric Peashooter':P.ElectricPeashooter,'Squash':P.Squash,
    'Gloom-shroom':P.GloomShroom,'Magnifying Grass':P.MagnifyingGrass,
    'Celery Stalker':P.CeleryStalker,'Sap-fling':P.Sapfling,'Parsnip':P.Parsnip,
    'Explode-O-Nut':P.ExplodeONut,'Grapeshot':P.Grapeshot,'Plantern':P.Plantern,
    'Heavenly Peach':P.HeavenlyPeach,"Jack O' Lantern":P.JackOLantern,
    'Dandelion':P.Dandelion,'Chard Guard':P.ChardGuard,'Hypno-shroom':P.HypnoShroom,
    'Electric Currant':P.ElectricCurrant,'Escape Root':P.EscapeRoot,
    'Imitater':P.Imitater,'Shadow-shroom':P.ShadowShroom,'Magnet-shroom':P.MagnetShroom,
    'E.M. Peach':P.EMPeach,'Citron':P.Citron,'Laser Bean':P.LaserBean,
    'Solar Tomato':P.SolarTomato,'Tile Turnip':P.TileTurnip,'Apple Mortar':P.AppleMortar,
    'Red Stinger':P.RedStinger,'Skyshooter':P.Skyshooter,'Sun Bean':P.SunBean,
    'Pea-nut':P.Peanut,'Tangle Kelp':P.TangleKelp,'Bowling Bulb':P.BowlingBulb,
    'Guacodile':P.Guacodile,'Ghost Pepper':P.GhostPepper,'Sweet Potato':P.SweetPotato,
    'Pepper-pult':P.PepperPult,'Hot Potato':P.HotPotato,'Stunion':P.Stunion,
    'Gold Leaf':P.GoldLeaf,'A.K.E.E.':P.AKEE,'Endurian':P.Endurian,
    'Toadstool':P.Toadstool,'Lava Guava':P.LavaGuava,'Phat Beet':P.PhatBeet,
    'Strawburst':P.Strawburst,'Thyme Warp':P.ThymeWarp,'Sea-shroom':P.SeaShroom,
    'Garlic':P.Garlic,'Electric Blueberry':P.ElectricBlueBerry,
    'Spore-shroom':P.SporeShroom,'Intensive Carrot':P.IntensiveCarrot,
    'Primal Sunflower':P.PrimalSunflower,'Moon Bean':P.MoonBean,
    'Cold Snapdragon':P.ColdSnapDragon,'Nightshade':P.NightShade,
    'Dusk Lobber':P.DuskLobber,'Grimrose':P.Grimrose,'Gold Bloom':P.GoldBloom,
    'Blooming Heart':P.BloomingHeart,'Shrinking Violet':P.ShrinkingViolet,
    'Hot Date':P.HotDate,'Fire Gourd':P.FireGourd,'Bamboo Shoot':P.BambooShoot,
    'Snowdrop':P.Snowdrop,'Lychee':P.Lychee,'Perfume-shroom':P.PerfumeShroom,
    'Solar Sage':P.SolarSage,'Bamboozle':P.Bamboozle,'Cantaloupe-pult':P.Cantaloupe,
    'Iceweed':P.Iceweed
  };

  // World Key gates: [keysNeeded, [worldIds]]
  // Unique world key items -> which world they unlock
  // Each key unlocks exactly one world. No progressive gating.
  const WORLD_KEY_MAP = {
    'Pirate Seas Key':      [W.pirate],
    'Wild West Key':        [W.cowboy],
    'Far Future Key':       [W.future],
    'Dark Ages Key':        [W.dark],
    'Big Wave Beach Key':   [W.beach],
    'Frostbite Caves Key':  [W.iceage],
    'Lost City Key':        [W.lostcity],
    'Kongfu Temple Key':    [W.kongfu],
    'Neon Mixtape Tour Key':[W.eighties],
    'Jurassic Marsh Key':   [W.dino],
    'Aerial Fortress Key':  [W.sky],
    'Modern Day Key':       [W.modern],
  };

  // Auto-generated from level_rewards.csv
  const LOC_LEVELS = {
    'Sunflower Unlock':'tutorial1',
    'Wall-nut Unlock':'tutorial2',
    'Potatomine Unlock':'tutorial3',
    'Sauce Unlock':'tutorial4',
    'random_zomboss_egypt':'random_zomboss_egypt',
    'Map Unlock':'egypt1',
    'Cabbagepult Unlock':'egypt2',
    'Bloomerang Unlock':'egypt3',
    'Powerupgadget Unlock':'egypt4',
    'Iceburg Unlock':'egypt5',
    'Branch Unlock Egypt 6':'egypt6',
    'Note Egypt Unlock':'egypt7',
    'World Key - Ancient Egypt':'egypt8',
    'Gravebuster Unlock':'egypt9',
    'egypt10':'egypt10',
    'Branch Unlock Egypt 11':'egypt11',
    'Dangerroom Egypt Unlock':'egypt12',
    'Bonkchoy Unlock':'egypt13',
    'egypt14':'egypt14',
    'Branch Unlock Egypt 15':'egypt15',
    'egypt16':'egypt16',
    'Upgrade Pf Slots Lvl1 Unlock':'egypt17',
    'egypt18':'egypt18',
    'Repeater Unlock':'egypt19',
    'egypt20':'egypt20',
    'egypt20_1':'egypt20_1',
    'Upgrade Starting Sun Lvl1 Unlock':'egypt21',
    'egypt21_1':'egypt21_1',
    'Branch Unlock Egypt 22':'egypt22',
    'egypt22_1':'egypt22_1',
    'Dangerroom Egypt Minigame Unlock':'egypt23',
    'Twinsunflower Unlock':'egypt24',
    'egypt24_1':'egypt24_1',
    'Worldtrophy Egypt Unlock':'egypt25',
    'egypt26':'egypt26',
    'Branch Unlock Egypt 27':'egypt27',
    'egypt28':'egypt28',
    'egypt29':'egypt29',
    'Branch Unlock Egypt 30':'egypt30',
    'Dangerroom Egypt2 Unlock':'egypt31',
    'egypt32':'egypt32',
    'egypt33':'egypt33',
    'Branch Unlock Egypt 34':'egypt34',
    'egypt35':'egypt35',
    'egypt_dangerroom':'egypt_dangerroom',
    'egypt_dangerroom2':'egypt_dangerroom2',
    'egypt_dangerroom_minigame':'egypt_dangerroom_minigame',
    'random_egypt':'random_egypt',
    'random_zomboss_pirate':'random_zomboss_pirate',
    'Kernelpult Unlock':'pirate1',
    'pirate2':'pirate2',
    'Snapdragon Unlock':'pirate3',
    'Dangerroom Pirate Unlock':'pirate4',
    'Branch Unlock Pirate 5':'pirate5',
    'Spikeweed Unlock':'pirate6',
    'Note Pirate Unlock':'pirate7',
    'World Key - Pirate Seas':'pirate8',
    'Springbean Unlock':'pirate9',
    'pirate10':'pirate10',
    'Coconutcannon Unlock':'pirate11',
    'Upgrade Sunshovel Lvl1 Unlock':'pirate12',
    'pirate13':'pirate13',
    'Threepeater Unlock':'pirate14',
    'pirate15':'pirate15',
    'Branch Unlock Pirate 16':'pirate16',
    'pirate17':'pirate17',
    'Spikerock Unlock':'pirate18',
    'pirate18_1':'pirate18_1',
    'Branch Unlock Pirate 19':'pirate19',
    'pirate20':'pirate20',
    'pirate20_1':'pirate20_1',
    'Upgrade 7 Slots Unlock':'pirate21',
    'pirate22':'pirate22',
    'pirate22_1':'pirate22_1',
    'Branch Unlock Pirate 23':'pirate23',
    'pirate23_1':'pirate23_1',
    'Cherry Bomb Unlock':'pirate24',
    'pirate24_1':'pirate24_1',
    'Worldtrophy Pirate Unlock':'pirate25',
    'pirate26':'pirate26',
    'Branch Unlock Pirate 27':'pirate27',
    'pirate28':'pirate28',
    'pirate29':'pirate29',
    'Branch Unlock Pirate 30':'pirate30',
    'pirate31':'pirate31',
    'pirate32':'pirate32',
    'Dangerroom Pirate2 Unlock':'pirate33',
    'pirate34':'pirate34',
    'pirate35':'pirate35',
    'pirate_dangerroom':'pirate_dangerroom',
    'pirate_dangerroom2':'pirate_dangerroom2',
    'random_pirate':'random_pirate',
    'random_zomboss_cowboy':'random_zomboss_cowboy',
    'Splitpea Unlock':'cowboy1',
    'Branch Unlock Cowboy 2':'cowboy2',
    'Dangerroom Cowboy Unlock':'cowboy3',
    'Chilibean Unlock':'cowboy4',
    'cowboy5':'cowboy5',
    'Peapod Unlock':'cowboy6',
    'Note Cowboy Unlock':'cowboy7',
    'World Key - Wild West':'cowboy8',
    'Lightningreed Unlock':'cowboy9',
    'cowboy10':'cowboy10',
    'Upgrade Sunshovel Lvl2 Unlock':'cowboy11',
    'Melonpult Unlock':'cowboy12',
    'cowboy12_1':'cowboy12_1',
    'cowboy13':'cowboy13',
    'Branch Unlock Cowboy 14':'cowboy14',
    'Upgrade Wallnut Firstaid Unlock':'cowboy15',
    'cowboy16':'cowboy16',
    'Branch Unlock Cowboy 17':'cowboy17',
    'Tallnut Unlock':'cowboy18',
    'cowboy18_1':'cowboy18_1',
    'cowboy19':'cowboy19',
    'Upgrade Pf Refresh Unlock':'cowboy20',
    'cowboy21':'cowboy21',
    'Branch Unlock Cowboy 22':'cowboy22',
    'cowboy22_1':'cowboy22_1',
    'cowboy23':'cowboy23',
    'cowboy23_1':'cowboy23_1',
    'Wintermelon Unlock':'cowboy24',
    'cowboy24_1':'cowboy24_1',
    'Worldtrophy Cowboy Unlock':'cowboy25',
    'Branch Unlock Cowboy 26':'cowboy26',
    'cowboy27':'cowboy27',
    'cowboy28':'cowboy28',
    'cowboy29':'cowboy29',
    'Branch Unlock Cowboy 30':'cowboy30',
    'cowboy31':'cowboy31',
    'cowboy32':'cowboy32',
    'Dangerroom Cowboy2 Unlock':'cowboy33',
    'Branch Unlock Cowboy 34':'cowboy34',
    'cowboy35':'cowboy35',
    'cowboy_dangerroom':'cowboy_dangerroom',
    'cowboy_dangerroom2':'cowboy_dangerroom2',
    'random_cowboy':'random_cowboy',
    'random_zomboss_future':'random_zomboss_future',
    'Laser Bean Unlock':'future1',
    'future2':'future2',
    'Blover Unlock':'future3',
    'Dangerroom Future Unlock':'future4',
    'Branch Unlock Future 5':'future5',
    'Citron Unlock':'future6',
    'Note Future Unlock':'future7',
    'World Key - Far Future':'future8',
    'Empea Unlock':'future9',
    'future10':'future10',
    'future10_1':'future10_1',
    'future10_2':'future10_2',
    'future10_3':'future10_3',
    'future10_4':'future10_4',
    'Branch Unlock Future 11':'future11',
    'future12':'future12',
    'Holonut Unlock':'future13',
    'future14':'future14',
    'Branch Unlock Future 15':'future15',
    'future16':'future16',
    'Magnifyinggrass Unlock':'future17',
    'future18':'future18',
    'future19':'future19',
    'Upgrade Manual Mowers 1 Unlock':'future20',
    'future21':'future21',
    'Branch Unlock Future 22':'future22',
    'future23':'future23',
    'Powerplant Unlock':'future24',
    'Worldtrophy Future Unlock':'future25',
    'future26':'future26',
    'Branch Unlock Future 27':'future27',
    'future28':'future28',
    'future29':'future29',
    'Branch Unlock Future 30':'future30',
    'future31':'future31',
    'Dangerroom Future2 Unlock':'future32',
    'Dangerroom Future Sunbomb Unlock':'future33',
    'Branch Unlock Future 34':'future34',
    'future35':'future35',
    'future_dangerroom':'future_dangerroom',
    'future_dangerroom2':'future_dangerroom2',
    'future_dangerroom_sunbomb':'future_dangerroom_sunbomb',
    'random_future':'random_future',
    'random_zomboss_dark':'random_zomboss_dark',
    'Sunshroom Unlock':'dark1',
    'Puffshroom Unlock':'dark2',
    'dark3':'dark3',
    'Fumeshroom Unlock':'dark4',
    'dark5':'dark5',
    'Sunbean Unlock':'dark6',
    'dark7':'dark7',
    'Branch Unlock Dark 8':'dark8',
    'Note Dark Unlock':'dark9',
    'World Key - Dark Ages':'dark10',
    'Branch Unlock Dark 11':'dark11',
    'Dangerroom Dark Unlock':'dark12',
    'Branch Unlock Dark 13':'dark13',
    'dark14':'dark14',
    'Magnetshroom Unlock':'dark15',
    'dark16':'dark16',
    'dark17':'dark17',
    'Branch Unlock Dark 18':'dark18',
    'dark18_1':'dark18_1',
    'dark19':'dark19',
    'Worldtrophy Dark Unlock':'dark20',
    'Scaredyshroom Unlock':'dark21',
    'dark22':'dark22',
    'Branch Unlock Dark 23':'dark23',
    'Branch Unlock Dark 24':'dark24',
    'Branch Unlock Dark 25':'dark25',
    'Dangerroom Dark2 Unlock':'dark26',
    'Dangerroom Dark Potion Unlock':'dark27',
    'dark28':'dark28',
    'Branch Unlock Dark 29':'dark29',
    'dark30':'dark30',
    'dark_dangerroom':'dark_dangerroom',
    'dark_dangerroom2':'dark_dangerroom2',
    'dark_dangerroom_potion':'dark_dangerroom_potion',
    'random_dark':'random_dark',
    'random_beach':'random_beach',
    'Lilypad Unlock':'beach1',
    'beach2':'beach2',
    'beach3':'beach3',
    'Branch Unlock Beach 4':'beach4',
    'beach5':'beach5',
    'Tanglekelp Unlock':'beach6',
    'beach7':'beach7',
    'Branch Unlock Beach 8':'beach8',
    'beach9':'beach9',
    'beach10':'beach10',
    'Bowlingbulb Unlock':'beach11',
    'Branch Unlock Beach 12':'beach12',
    'beach13':'beach13',
    'Branch Unlock Beach 14':'beach14',
    'Note Beach Unlock':'beach15',
    'World Key - Big Wave Beach':'beach16',
    'Branch Unlock Beach 17':'beach17',
    'beach18':'beach18',
    'Guacodile Unlock':'beach19',
    'Dangerroom Beach Unlock':'beach20',
    'beach21':'beach21',
    'Branch Unlock Beach 22':'beach22',
    'beach23':'beach23',
    'Dangerroom Beach Minigame Unlock':'beach24',
    'Branch Unlock Beach 25':'beach25',
    'beach26':'beach26',
    'Banana Unlock':'beach27',
    'beach28':'beach28',
    'beach29':'beach29',
    'Branch Unlock Beach 30':'beach30',
    'Seashroom Unlock':'beach31',
    'Worldtrophy Beach Unlock':'beach32',
    'beach33':'beach33',
    'beach34':'beach34',
    'beach35':'beach35',
    'Dangerroom Beach2 Unlock':'beach36',
    'beach37':'beach37',
    'beach38':'beach38',
    'beach39':'beach39',
    'beach40':'beach40',
    'beach41':'beach41',
    'beach42':'beach42',
    'beach_dangerroom':'beach_dangerroom',
    'beach_dangerroom2':'beach_dangerroom2',
    'beach_dangerroom_minigame_beach':'beach_dangerroom_minigame_beach',
    'beach_dangerroom_minigame_cowboy':'beach_dangerroom_minigame_cowboy',
    'beach_dangerroom_minigame_dark':'beach_dangerroom_minigame_dark',
    'beach_dangerroom_minigame_egypt':'beach_dangerroom_minigame_egypt',
    'beach_dangerroom_minigame_future':'beach_dangerroom_minigame_future',
    'beach_dangerroom_minigame_iceage':'beach_dangerroom_minigame_iceage',
    'beach_dangerroom_minigame_lostcity':'beach_dangerroom_minigame_lostcity',
    'beach_dangerroom_minigame_pirate':'beach_dangerroom_minigame_pirate',
    'iceage_dangerroom':'iceage_dangerroom',
    'Hotpotato Unlock':'iceage1',
    'iceage2':'iceage2',
    'iceage3':'iceage3',
    'Branch Unlock Iceage 4':'iceage4',
    'iceage5':'iceage5',
    'Pepperpult Unlock':'iceage6',
    'iceage7':'iceage7',
    'Branch Unlock Iceage 8':'iceage8',
    'iceage9':'iceage9',
    'iceage10':'iceage10',
    'Chardguard Unlock':'iceage11',
    'Branch Unlock Iceage 12':'iceage12',
    'iceage13':'iceage13',
    'Branch Unlock Iceage 14':'iceage14',
    'Note Iceage Unlock':'iceage15',
    'World Key - Frostbite Caves':'iceage16',
    'Branch Unlock Iceage 17':'iceage17',
    'iceage18':'iceage18',
    'Stunion Unlock':'iceage19',
    'Dangerroom Iceage Unlock':'iceage20',
    'iceage21':'iceage21',
    'Branch Unlock Iceage 22':'iceage22',
    'iceage23':'iceage23',
    'Branch Unlock Iceage 24':'iceage24',
    'iceage24_B':'iceage24_B',
    'iceage25':'iceage25',
    'Xshot Unlock':'iceage26',
    'iceage27':'iceage27',
    'iceage28':'iceage28',
    'Branch Unlock Iceage 29':'iceage29',
    'Worldtrophy Iceage Unlock':'iceage30',
    'Branch Unlock Iceage 31':'iceage31',
    'iceage32':'iceage32',
    'iceage33':'iceage33',
    'Branch Unlock Iceage 34':'iceage34',
    'Dangerroom Iceage2 Unlock':'iceage35',
    'iceage36':'iceage36',
    'iceage37':'iceage37',
    'iceage38':'iceage38',
    'iceage39':'iceage39',
    'iceage40':'iceage40',
    'iceage_dangerroom2':'iceage_dangerroom2',
    'lostcity_dangerroom':'lostcity_dangerroom',
    'Redstinger Unlock':'lostcity1',
    'lostcity2':'lostcity2',
    'lostcity3':'lostcity3',
    'Branch Unlock Lostcity 4':'lostcity4',
    'lostcity5':'lostcity5',
    'Akee Unlock':'lostcity6',
    'lostcity7':'lostcity7',
    'Branch Unlock Lostcity 8':'lostcity8',
    'lostcity9':'lostcity9',
    'Endurian Unlock':'lostcity10',
    'lostcity11':'lostcity11',
    'Branch Unlock Lostcity 12':'lostcity12',
    'lostcity13':'lostcity13',
    'Branch Unlock Lostcity 14':'lostcity14',
    'Note Lostcity Unlock':'lostcity15',
    'World Key - Lost City':'lostcity16',
    'Branch Unlock Lostcity 17':'lostcity17',
    'lostcity18':'lostcity18',
    'Stallia Unlock':'lostcity19',
    'Dangerroom Lostcity Unlock':'lostcity20',
    'lostcity21':'lostcity21',
    'lostcity22':'lostcity22',
    'Branch Unlock Lostcity 23':'lostcity23',
    'lostcity24':'lostcity24',
    'lostcity25':'lostcity25',
    'Goldleaf Unlock':'lostcity26',
    'lostcity27':'lostcity27',
    'Branch Unlock Lostcity 28':'lostcity28',
    'lostcity29':'lostcity29',
    'Branch Unlock Lostcity 30':'lostcity30',
    'lostcity31':'lostcity31',
    'Worldtrophy Lostcity Unlock':'lostcity32',
    'Branch Unlock Lostcity 33':'lostcity33',
    'Branch Unlock Lostcity 34':'lostcity34',
    'Branch Unlock Lostcity 35':'lostcity35',
    'Branch Unlock Lostcity 36':'lostcity36',
    'lostcity37':'lostcity37',
    'Branch Unlock Lostcity 38':'lostcity38',
    'Dangerroom Lostcity2 Unlock':'lostcity39',
    'Branch Unlock Lostcity 40':'lostcity40',
    'Branch Unlock Lostcity 41':'lostcity41',
    'lostcity42':'lostcity42',
    'lostcity_dangerroom2':'lostcity_dangerroom2',
    'kongfu_dangerroom':'kongfu_dangerroom',
    'Firegourd Unlock':'kongfu1',
    'kongfu2':'kongfu2',
    'kongfu3':'kongfu3',
    'kongfu4':'kongfu4',
    'kongfu5':'kongfu5',
    'Snowpea Unlock':'kongfu6',
    'kongfu7':'kongfu7',
    'World Key - Kongfu Temple':'kongfu8',
    'kongfu9':'kongfu9',
    'Bambooshoot Unlock':'kongfu10',
    'kongfu11':'kongfu11',
    'kongfu12':'kongfu12',
    'Turnip Unlock':'kongfu13',
    'Dangerroom Kongfu Unlock':'kongfu14',
    'kongfu15':'kongfu15',
    'kongfu16':'kongfu16',
    'kongfu17':'kongfu17',
    'kongfu18':'kongfu18',
    'Peach Unlock':'kongfu19',
    'kongfu20':'kongfu20',
    'kongfu21':'kongfu21',
    'kongfu22':'kongfu22',
    'kongfu23':'kongfu23',
    'kongfu24':'kongfu24',
    'kongfu25':'kongfu25',
    'kongfu26':'kongfu26',
    'kongfu27':'kongfu27',
    'kongfu28':'kongfu28',
    'Lychee Unlock':'kongfu29',
    'Dangerroom Kongfu2 Unlock':'kongfu30',
    'kongfu31':'kongfu31',
    'kongfu32':'kongfu32',
    'kongfu33':'kongfu33',
    'Solarsage Unlock':'kongfu34',
    'kongfu35':'kongfu35',
    'kongfu36':'kongfu36',
    'kongfu37':'kongfu37',
    'kongfu38':'kongfu38',
    'kongfu39':'kongfu39',
    'kongfu40':'kongfu40',
    'kongfu41':'kongfu41',
    'kongfu42':'kongfu42',
    'kongfu43':'kongfu43',
    'kongfu44':'kongfu44',
    'kongfu45':'kongfu45',
    'Cantaloupe Unlock':'kongfu46',
    'Dangerroom Kongfu3 Unlock':'kongfu47',
    'kongfu48':'kongfu48',
    'kongfu_dangerroom2':'kongfu_dangerroom2',
    'kongfu_dangerroom3':'kongfu_dangerroom3',
    'kongfu_dangerroom4':'kongfu_dangerroom4',
    'eighties_dangerroom':'eighties_dangerroom',
    'Phatbeet Unlock':'eighties1',
    'eighties2':'eighties2',
    'eighties3':'eighties3',
    'eighties4':'eighties4',
    'Celerystalker Unlock':'eighties5',
    'eighties6':'eighties6',
    'eighties7':'eighties7',
    'eighties8':'eighties8',
    'Thymewarp Unlock':'eighties9',
    'eighties10':'eighties10',
    'eighties11':'eighties11',
    'Branch Unlock Eighties 12':'eighties12',
    'eighties13':'eighties13',
    'Branch Unlock Eighties 14':'eighties14',
    'eighties15':'eighties15',
    'World Key - Neon Mixtape Tour':'eighties16',
    'Garlic Unlock':'eighties17',
    'eighties18':'eighties18',
    'eighties19':'eighties19',
    'Dangerroom Eighties Unlock':'eighties20',
    'Sporeshroom Unlock':'eighties21',
    'eighties22':'eighties22',
    'eighties23':'eighties23',
    'Branch Unlock Eighties 24':'eighties24',
    'eighties25':'eighties25',
    'Intensivecarrot Unlock':'eighties26',
    'eighties27':'eighties27',
    'eighties28':'eighties28',
    'Branch Unlock Eighties 29':'eighties29',
    'eighties30':'eighties30',
    'eighties31':'eighties31',
    'Worldtrophy Eighties Unlock':'eighties32',
    'dino_dangerroom':'dino_dangerroom',
    'Primalpeashooter Unlock':'dino1',
    'dino2':'dino2',
    'dino3':'dino3',
    'Primalwallnut Unlock':'dino4',
    'dino5':'dino5',
    'Branch Unlock Dino 6':'dino6',
    'Branch Unlock Dino 7':'dino7',
    'Perfumeshroom Unlock':'dino8',
    'dino9':'dino9',
    'dino10':'dino10',
    'dino11':'dino11',
    'Branch Unlock Dino 12':'dino12',
    'dino13':'dino13',
    'Branch Unlock Dino 14':'dino14',
    'Note Dino Unlock':'dino15',
    'World Key - Jurassic Marsh':'dino16',
    'Primalsunflower Unlock':'dino17',
    'dino18':'dino18',
    'dino19':'dino19',
    'Dangerroom Dino Unlock':'dino20',
    'dino21':'dino21',
    'dino22':'dino22',
    'Primalpotatomine Unlock':'dino23',
    'Branch Unlock Dino 24':'dino24',
    'dino25':'dino25',
    'dino26':'dino26',
    'dino27':'dino27',
    'dino28':'dino28',
    'Branch Unlock Dino 29':'dino29',
    'dino30':'dino30',
    'dino31':'dino31',
    'Worldtrophy Dino Unlock':'dino32',
    'Branch Unlock Dino 33':'dino33',
    'dino34':'dino34',
    'dino35':'dino35',
    'Dangerroom Dino2 Unlock':'dino36',
    'Branch Unlock Dino 37':'dino37',
    'dino38':'dino38',
    'dino39':'dino39',
    'dino40':'dino40',
    'Branch Unlock Dino 41':'dino41',
    'dino42':'dino42',
    'dino_dangerroom2':'dino_dangerroom2',
    'modern_zomboss_01_egypt':'modern_zomboss_01_egypt',
    'Moonflower Unlock':'modern1',
    'modern2':'modern2',
    'modern3':'modern3',
    'Nightshade Unlock':'modern4',
    'modern5':'modern5',
    'Branch Unlock Modern 6':'modern6',
    'Branch Unlock Modern 7':'modern7',
    'modern8':'modern8',
    'modern9':'modern9',
    'Shadowshroom Unlock':'modern10',
    'modern11':'modern11',
    'Branch Unlock Modern 12':'modern12',
    'modern13':'modern13',
    'Branch Unlock Modern 14':'modern14',
    'Note Modern Unlock':'modern15',
    'World Key - Modern Day':'modern16',
    'Dusklobber Unlock':'modern17',
    'modern18':'modern18',
    'modern19':'modern19',
    'Dangerroom Modern Unlock':'modern20',
    'modern21':'modern21',
    'modern22':'modern22',
    'Grimrose Unlock':'modern23',
    'modern24':'modern24',
    'Branch Unlock Modern 25':'modern25',
    'modern26':'modern26',
    'modern27':'modern27',
    'modern28':'modern28',
    'Branch Unlock Modern 29':'modern29',
    'modern30':'modern30',
    'modern31':'modern31',
    'modern35':'modern35',
    'Branch Unlock Modern 36':'modern36',
    'modern37':'modern37',
    'modern38':'modern38',
    'Branch Unlock Modern 39':'modern39',
    'Dangerroom Modern2 Unlock':'modern40',
    'modern41':'modern41',
    'modern42':'modern42',
    'Branch Unlock Modern 43':'modern43',
    'modern44':'modern44',
    'modern_dangerroom':'modern_dangerroom',
    'modern_dangerroom2':'modern_dangerroom2',
    'modern_zomboss_02_pirate':'modern_zomboss_02_pirate',
    'modern_zomboss_03_cowboy':'modern_zomboss_03_cowboy',
    'modern_zomboss_04_future':'modern_zomboss_04_future',
    'modern_zomboss_05_dark':'modern_zomboss_05_dark',
    'modern_zomboss_06_beach':'modern_zomboss_06_beach',
    'modern_zomboss_07_iceage':'modern_zomboss_07_iceage',
    'modern_zomboss_08_lostcity':'modern_zomboss_08_lostcity',
    'modern_zomboss_09_eighties':'modern_zomboss_09_eighties',
    'modern_zomboss_10_dino':'modern_zomboss_10_dino',
    'Skyshooter Unlock':'sky1',
    'sky2':'sky2',
    'Upgrade Sky Shield Unlock':'sky3',
    'sky4':'sky4',
    'sky5':'sky5',
    'Pineapple Unlock':'sky6',
    'sky7':'sky7',
    'Moonbean Unlock':'sky8',
    'sky9':'sky9',
    'sky10':'sky10',
    'Anthurium Unlock':'sky11',
    'sky12':'sky12',
    'sky13':'sky13',
    'sky14':'sky14',
    'sky15':'sky15',
    'World Key - Aerial Fortress':'sky16',
    'aloe0':'aloe0.JSON',
    'aloe1':'aloe1.JSON',
    'aloe2':'aloe2.JSON',
    'aloe3':'aloe3.JSON',
    'aloe4':'aloe4.JSON',
    'Aloe Unlock':'aloe5.JSON',
    'appease1_0':'appease1_0',
    'appease1_1':'appease1_1',
    'appease1_2':'appease1_2',
    'Dandelion Unlock':'appease1_3',
    'appease1_4':'appease1_4',
    'appease1_5':'appease1_5',
    'Pvine Unlock':'appease1_6',
    'appease2_0':'appease2_0',
    'appease2_1':'appease2_1',
    'appease2_2':'appease2_2',
    'appease2_3':'appease2_3',
    'Gatling Unlock':'appease2_4',
    'Megagatling Unlock':'appease2_5',
    'Torchwood Unlock':'appease2_6',
    'atombomb0':'atombomb0',
    'atombomb1':'atombomb1',
    'atombomb2':'atombomb2',
    'atombomb3':'atombomb3',
    'atombomb4':'atombomb4',
    'Atombomb Seedling Unlock':'atombomb5',
    'bank_theft1':'bank_theft1',
    'bank_theft2':'bank_theft2',
    'bank_theft3':'bank_theft3',
    'bank_theft4':'bank_theft4',
    'bank_theft5':'bank_theft5',
    'bloominghearts0':'bloominghearts0',
    'bloominghearts1':'bloominghearts1',
    'bloominghearts2':'bloominghearts2',
    'bloominghearts3':'bloominghearts3',
    'bloominghearts4':'bloominghearts4',
    'Bloominghearts Unlock':'bloominghearts5',
    'buttercup0':'buttercup0',
    'buttercup1':'buttercup1',
    'buttercup2':'buttercup2',
    'buttercup3':'buttercup3',
    'buttercup4':'buttercup4',
    'Buttercup Unlock':'buttercup5',
    'conceal0':'conceal0',
    'conceal1':'conceal1',
    'conceal2':'conceal2',
    'conceal3':'conceal3',
    'conceal4':'conceal4',
    'Gloomvine Unlock':'conceal5',
    'conceal6':'conceal6',
    'Murkadamia Unlock':'conceal7',
    'conceal8':'conceal8',
    'Shadowpeashooter Unlock':'conceal9',
    'conceal10':'conceal10',
    'Noctarine Unlock':'conceal11',
    'doomshroom0':'doomshroom0',
    'doomshroom1':'doomshroom1',
    'doomshroom2':'doomshroom2',
    'doomshroom3':'doomshroom3',
    'doomshroom4':'doomshroom4',
    'Doomshroom Unlock':'doomshroom5',
    'electriccurrant0':'electriccurrant0',
    'electriccurrant1':'electriccurrant1',
    'electriccurrant2':'electriccurrant2',
    'electriccurrant3':'electriccurrant3',
    'electriccurrant4':'electriccurrant4',
    'Electriccurrant Unlock':'electriccurrant5',
    'enlighten0':'enlighten0',
    'enlighten1':'enlighten1',
    'enlighten2':'enlighten2',
    'enlighten3':'enlighten3',
    'enlighten4':'enlighten4',
    'enlighten5':'enlighten5',
    'enlighten6':'enlighten6',
    'Shinevine Unlock':'enlighten7',
    'epic_beghouled1':'epic_beghouled1',
    'epic_beghouled2':'epic_beghouled2',
    'epic_beghouled3':'epic_beghouled3',
    'epic_beghouled4':'epic_beghouled4',
    'epic_beghouled5':'epic_beghouled5',
    'floawerpot1':'floawerpot1',
    'floawerpot2':'floawerpot2',
    'floawerpot3':'floawerpot3',
    'ghostpepper0':'ghostpepper0',
    'ghostpepper1':'ghostpepper1',
    'ghostpepper2':'ghostpepper2',
    'Ghostpepper Unlock':'ghostpepper3',
    'gloomshroom0':'gloomshroom0',
    'gloomshroom1':'gloomshroom1',
    'gloomshroom2':'gloomshroom2',
    'gloomshroom3':'gloomshroom3',
    'gloomshroom4':'gloomshroom4',
    'gloomshroom5':'gloomshroom5',
    'gloomshroom6':'gloomshroom6',
    'Gloomshroom Unlock':'gloomshroom7',
    'goldbloom0':'goldbloom0',
    'goldbloom1':'goldbloom1',
    'goldbloom2':'goldbloom2',
    'Goldbloom Unlock':'goldbloom3',
    'hotdate1':'hotdate1',
    'hotdate2':'hotdate2',
    'Hotdate Unlock':'hotdate3',
    'icebloom0':'icebloom0',
    'icebloom1':'icebloom1',
    'icebloom2':'icebloom2',
    'icebloom3':'icebloom3',
    'icebloom4':'icebloom4',
    'Icebloom Unlock':'icebloom5',
    'iceshroom0':'iceshroom0',
    'iceshroom1':'iceshroom1',
    'iceshroom2':'iceshroom2',
    'iceshroom3':'iceshroom3',
    'iceshroom4':'iceshroom4',
    'Glaciershroom Unlock':'iceshroom5',
    'meteorflower0':'meteorflower0',
    'meteorflower1':'meteorflower1',
    'meteorflower2':'meteorflower2',
    'Meteorflower Unlock':'meteorflower3',
    'mixed_dangerroom2':'mixed_dangerroom2',
    'parsnip0':'parsnip0',
    'parsnip1':'parsnip1',
    'parsnip2':'parsnip2',
    'parsnip3':'parsnip3',
    'parsnip4':'parsnip4',
    'Parsnip Unlock':'parsnip5',
    'plantern0':'plantern0',
    'plantern1':'plantern1',
    'plantern2':'plantern2',
    'plantern3':'plantern3',
    'plantern4':'plantern4',
    'Plantern Unlock':'plantern5',
    'reinforce0':'reinforce0',
    'reinforce1':'reinforce1',
    'reinforce2':'reinforce2',
    'reinforce3':'reinforce3',
    'reinforce4':'reinforce4',
    'reinforce5':'reinforce5',
    'reinforce6':'reinforce6',
    'Pumpkin Unlock':'reinforce7',
    'reinforce8':'reinforce8',
    'Hollyknight Unlock':'reinforce9',
    'reinforce10':'reinforce10',
    'Gumnut Unlock':'reinforce11',
    'reinforcemint_try1':'reinforcemint_try1',
    'reinforcemint_try2':'reinforcemint_try2',
    'reinforcemint_try3':'reinforcemint_try3',
    'rhythm1':'rhythm1',
    'sandbox':'sandbox',
    'sandbox_green':'sandbox_green',
    'sandbox_modern':'sandbox_modern',
    'sandbox_modern_night':'sandbox_modern_night',
    'sandbox_sky':'sandbox_sky',
    'sapfling0':'sapfling0',
    'sapfling1':'sapfling1',
    'sapfling2':'sapfling2',
    'sapfling3':'sapfling3',
    'sapfling4':'sapfling4',
    'sapfling5':'sapfling5',
    'sapfling6':'sapfling6',
    'Sapfling Unlock':'sapfling7',
    'seashooter0':'seashooter0',
    'seashooter1':'seashooter1',
    'seashooter2':'seashooter2',
    'Seashooter Unlock':'seashooter3',
    'shootingstarfruit1':'shootingstarfruit1',
    'shootingstarfruit2':'shootingstarfruit2',
    'shootingstarfruit3':'shootingstarfruit3',
    'solartomato0':'solartomato0',
    'solartomato1':'solartomato1',
    'solartomato2':'solartomato2',
    'solartomato3':'solartomato3',
    'solartomato4':'solartomato4',
    'Solartomato Unlock':'solartomato5',
    'squash0':'squash0',
    'squash1':'squash1',
    'squash2':'squash2',
    'Squash Unlock':'squash3',
    'strawburst0':'strawburst0',
    'strawburst1':'strawburst1',
    'strawburst2':'strawburst2',
    'strawburst3':'strawburst3',
    'strawburst4':'strawburst4',
    'strawburst5':'strawburst5',
    'strawburst6':'strawburst6',
    'Strawburst Unlock':'strawburst7',
    'sweetpotato0':'sweetpotato0',
    'sweetpotato1':'sweetpotato1',
    'sweetpotato2':'sweetpotato2',
    'sweetpotato3':'sweetpotato3',
    'sweetpotato4':'sweetpotato4',
    'Sweetpotato Unlock':'sweetpotato5',
    'umbrellaleaf0':'umbrellaleaf0',
    'umbrellaleaf1':'umbrellaleaf1',
    'umbrellaleaf2':'umbrellaleaf2',
    'umbrellaleaf3':'umbrellaleaf3',
    'umbrellaleaf4':'umbrellaleaf4',
    'umbrellaleaf5':'umbrellaleaf5',
    'umbrellaleaf6':'umbrellaleaf6',
    'umbrellaleaf7':'umbrellaleaf7',
    'umbrellaleaf8':'umbrellaleaf8',
    'umbrellaleaf9':'umbrellaleaf9',
    'umbrellaleaf10':'umbrellaleaf10',
    'Umbrellaleaf Unlock':'umbrellaleaf11',
    'vamporcini0':'vamporcini0',
    'vamporcini1':'vamporcini1',
    'vamporcini2':'vamporcini2',
    'Vamporcini Unlock':'vamporcini3',
  };

  // Simple region lookup for Modern Day check
  function getRegion(locName){
    const md_prefixes=['modern_zomboss','modern_dangerroom','modern','Moonflower','Nightshade',
      'Shadowshroom','Dusklobber','Grimrose','Branch Unlock Modern','Dangerroom Modern',
      'Note Modern','World Key - Modern','Worldtrophy Modern'];
    if(md_prefixes.some(p=>locName.startsWith(p)||locName===p)) return 'Modern Day';
    return null;
  }

  // Which locations live in Modern Day. Constant for the life of the page, so
  // it is computed once here -- fireCheck() used to rebuild this list on every
  // single check, scanning all 761 LOC_LEVELS entries and running getRegion()
  // (a 13-prefix scan) on each one before it could answer.
  const MODERN_DAY_LOCS = new Set(
    Object.keys(LOC_LEVELS).filter(n => getRegion(n) === 'Modern Day'));

  // Goal config (st.goalLocs / st.worldsReq) is populated from slot_data on
  // connect and persisted on st so it survives a page reload -- rebuildAPSave
  // runs on the poll timer even before the player reconnects this session,
  // and canAccessModernDay() must see the real values then, not defaults.

  // ── State ─────────────────────────────────────────────────────────────────
  // Rebuild _AP_grantedPlantIds from persisted st.receivedItems.
  // Called synchronously at IIFE start (before DOMContentLoaded) so the
  // unlockPlant interceptor has the correct set before any game code runs.
  function syncGrantedPlants() {
    if(!window._AP_grantedPlantIds) window._AP_grantedPlantIds = new Set();
    if(st.receivedItems && st.receivedItems.length){
      st.receivedItems.forEach(name=>{
        const pid=ITEM_PLANT[name];
        if(pid!==undefined) window._AP_grantedPlantIds.add(pid);
      });
    }
  }

  // Same idea for the permanent upgrades, driven by the item name -> ordered
  // codename list slot_data hands over (st.upgradeItems). The upgrades are
  // progressive: N copies of "Progressive Sun Shovel" grant that group's
  // first N codenames. Which N is arbitrary as far as the game is concerned,
  // since every level of a group has the same effect and they are summed --
  // it only has to be consistent between calls, which taking a prefix is.
  //
  // Counts come from st.upgradeCounts rather than st.receivedItems, which is
  // deduplicated by name and so cannot tell one copy from three.
  //
  // The counts, the item map and the shuffle flag are all persisted on st, so
  // a page reload has the right answer before the socket is back up --
  // otherwise the first rebuildAPSave() of the session would strip every
  // upgrade the player legitimately holds.
  function syncGrantedUpgrades() {
    window._AP_shuffleUpgrades = !!st.shuffleUpgrades;
    const map = st.upgradeItems || {};
    const counts = st.upgradeCounts || {};
    const granted = new Set(), known = new Set();
    for(const name of Object.keys(map)){
      const cns = map[name] || [];
      cns.forEach(cn => known.add(cn));
      // Capped at the group's length: a pool that somehow over-delivered
      // would otherwise index past the end and add undefined to the set.
      const n = Math.min(counts[name] || 0, cns.length);
      for(let i = 0; i < n; i++) granted.add(cns[i]);
    }
    window._AP_grantedUpgrades = granted;
    // Which codenames AP manages at all, so rebuildAPSave() only ever resets
    // these -- an upgrade the game gains in a future version is left alone
    // rather than forced to 0 for not being in a map that predates it.
    window._AP_knownUpgradeCns = known;
    return granted;
  }

  let cfg   = { server:'localhost:38281', slot:'', password:'' };
  let st    = { checked:[], lastIdx:0, receivedKeys:[], receivedItems:[],
                upgradeCounts:{}, costumes:{}, wornCostume:{}, pendingCostumes:0, runKey:'' };
  let sessionActive = false; // set true only after explicit Connect + server ack
  // Whether this session has told the server the goal is met. Session state,
  // not persisted: it is reset on every disconnect so a reconnect re-sends,
  // which is what makes a StatusUpdate lost to a dropped socket self-healing.
  let goalSent = false;

  // st.checked stays an Array because it is persisted as JSON, but membership
  // is tested 761 times every poll tick -- Array.includes() made that O(n*m),
  // several hundred thousand string comparisons every 2s once a run is well
  // along. Mirror it into a Set for lookups.
  // The mirror is rebuilt whenever the array's identity OR length changes,
  // rather than being updated at each mutation site: st is replaced wholesale
  // in four places (init, load, run-key change, manual reset) and pushed to in
  // two, and a mirror that has to be maintained at every one of those is a
  // desync -- i.e. a silently dropped or duplicated check -- waiting to
  // happen. Identity plus length catches every mutation this code performs.
  let _checkedSet = null, _checkedSrc = null, _checkedLen = -1;
  function isChecked(loc){
    const arr = st.checked || [];
    if(_checkedSrc !== arr || _checkedLen !== arr.length){
      _checkedSet = new Set(arr);
      _checkedSrc = arr;
      _checkedLen = arr.length;
    }
    return _checkedSet.has(loc);
  }

  // Load persisted state and rebuild granted set SYNCHRONOUSLY right now,
  // before DOMContentLoaded fires, so installAPHooks sees the correct set.
  (function() {
    try { Object.assign(st, JSON.parse(localStorage.getItem('ap_pvz2_state')||'{}')); } catch(e){}
    syncGrantedPlants();
    syncGrantedUpgrades();
    syncConveyorConfig();
    syncZombieConfig();
    syncShopConfig();
  })();

  // ── Save guard ────────────────────────────────────────────────────────────
  // Intercepts ALL writes to PvZ2_PlayerProperties and strips unauthorized
  // plants from the AP-managed slot before they hit localStorage.
  (function() {
    const _origSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) {
      if (key === SAVE_KEY && window._AP_grantedPlantIds) {
        try {
          const arr = JSON.parse(value);
          if (Array.isArray(arr)) {
            // Prefer the marker over the stored index, which can point at the
            // wrong entry (or past the end) if the slot ever got reindexed.
            let apIdx = arr.findIndex(p => p && p._ap_managed === true);
            if (apIdx < 0) apIdx = parseInt(localStorage.getItem(AP_SLOT_IDX_KEY), 10);
            const p = !isNaN(apIdx) && apIdx >= 0 ? arr[apIdx] : null;
            if (p && p.plantProps) {
              const authorizedCns = new Set();
              for (const pid in ID_TO_CN) {
                if (window._AP_grantedPlantIds.has(Number(pid))) authorizedCns.add(ID_TO_CN[pid]);
              }
              for (const cn of Object.keys(p.plantProps)) {
                if (!authorizedCns.has(cn)) delete p.plantProps[cn];
              }
              value = JSON.stringify(arr);
            }
            // No upgrade equivalent here on purpose. Plants need this pass
            // because the game can write plantProps straight out mid-level,
            // ahead of the next poll. Upgrades have a single grant path,
            // unlockUpgrade(), which is hooked at source, and rebuildAPSave()
            // reconciles the whole set every poll on top of that -- so a
            // scrub here would add a third copy of the rule with nothing left
            // for it to catch, against a serialised shape (player_upgrades,
            // post-migration) this code would have to guess at.
          }
        } catch(e) {}
      }
      return _origSetItem.call(this, key, value);
    };
  })();

  const lsCfg  = () => { try { Object.assign(cfg, JSON.parse(localStorage.getItem(CFG_KEY)||'{}')); } catch(e){} };
  const svCfg  = () => localStorage.setItem(CFG_KEY, JSON.stringify(cfg));
  const lsSt   = () => { try { Object.assign(st,  JSON.parse(localStorage.getItem(STATE_KEY)||'{}')); } catch(e){} };
  const svSt   = () => localStorage.setItem(STATE_KEY, JSON.stringify(st));

  // ── AP-managed save slot ──────────────────────────────────────────────────
  // Finds or creates a slot marked _ap_managed in PvZ2_PlayerProperties,
  // stores its index, and updates PvZ2_Settings.PlayerIndex so the game
  // always loads our slot on startup (the getItem intercept enforces this).
  function findOrCreateAPSlot() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      const allPlayers = raw ? JSON.parse(raw) : [];
      let apIdx = allPlayers.findIndex(p => p && p._ap_managed === true);
      if(apIdx < 0) {
        apIdx = allPlayers.length;
        allPlayers.push({ _ap_managed: true, name: 'AP Multiworld' });
        localStorage.setItem(SAVE_KEY, JSON.stringify(allPlayers));
      }
      localStorage.setItem(AP_SLOT_IDX_KEY, String(apIdx));
      try {
        const sRaw = localStorage.getItem(SETTINGS_KEY);
        const s = sRaw ? JSON.parse(sRaw) : {};
        s.PlayerIndex = apIdx;
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
      } catch(e) {}
      return apIdx;
    } catch(e) { log('Error creating AP slot: ' + e); return -1; }
  }

  // The game nags you to open the almanac, the zen garden and the store the
  // first time each one unlocks: a pointing finger on the world map (its
  // *_LEADER flow), then an NPC walkthrough once you are inside (*_INTRO).
  // Every one of them is gated on its own "already seen" flag on
  // currentPlayer.tutorial, in the shape
  //     if (!tut.almanac_open) { tut.almanac_open = true; SetFlow(ALMANAC_LEADER); }
  // so setting the flag IS the game's own way of recording that it has been
  // shown. No hook needed, and nothing to keep in sync with a game update.
  //
  // Only the six pure-prompt flags are listed. _PlayerTutorialProps carries
  // three more that each do something besides prompt, so setting them would
  // change the game rather than get out of its way: `plantfood` spawns the
  // tutorial's peashooter, `worldmap` decides which screen you land on, and
  // `worldkey` advances worldChooserPos and shows an advice tip. The three
  // premium_* flags are left alone for the same reason.
  const FEATURE_TUTORIAL_FLAGS = [
    'almanac_open', 'almanac_intro',
    'zengarden_open', 'zengarden_intro',
    'store_open', 'store_intro',
  ];

  // Which cp.features flag each level clear turns on, straight out of the
  // game's own unlock chain in index.js:
  //     n.feature_store || getLevelProgressByID("egypt6").progress >= 3
  //                        && (n.feature_store = true)
  // The store BUTTON is gated on that flag alone
  // (!feature_store || (this.storeButton.node.active = false)), so a save with
  // egypt6 cleared and the flag unset has no way into the store at all.
  //
  // That is reachable under AP: the flag is only ever written while the game
  // watches you finish the level, but an AP save is rebuilt from checked
  // locations, so a slot resumed on another machine, or one whose egypt6 check
  // arrived from the multiworld rather than from play, has the progress and
  // not the flag. Re-deriving it from progress on every rebuild makes that
  // self-correcting.
  //
  // Confirmed against a real save (2026-08-16): a slot with egypt1, tutorial1-4
  // and eleven Modern Day levels checked had ALL NINE flags still false. The
  // chain evidently runs when the save is loaded, before the client has
  // rebuilt levelProps from the multiworld, and not again -- so under AP these
  // never turn on by themselves. That is not only a missing store button:
  //
  //     feature_plantfood || (this.showPlantfood = false)
  //     feature_powerup   || (this.showPowerUps  = false)
  //     feature_coins     || (this.dropCoins     = false)
  //     feature_zengarden || (this.dropSprouts   = false)
  //
  // With feature_coins false, zombies drop no coins at all, which is why an AP
  // save can show currency granted by the multiworld and none ever earned.
  //
  // Each flag lists [level, threshold] pairs and needs any ONE of them, which
  // is how the game writes it: coins unlock on tutorial4 being finished OR on
  // egypt1 being merely unlocked (> locked, so 1 rather than 3).
  //
  // feature_lod and feature_worldkeys are deliberately absent: neither is ever
  // set to true anywhere in index.js, so there is no condition to mirror and
  // inventing one would grant something the game never grants.
  const FEATURE_UNLOCK_LEVELS = {
    feature_almanac:   [['egypt2', 3]],
    feature_coins:     [['tutorial4', 3], ['egypt1', 1]],
    feature_plantfood: [['egypt1', 3]],
    feature_worldmap:  [['egypt1', 3]],
    feature_powerup:   [['egypt5', 3]],
    feature_zengarden: [['egypt5', 3]],
    feature_store:     [['egypt6', 3]],
  };

  // The game's LevelProgress enum: locked 0, unlocked_neverPlayed 1,
  // unlocked_played 2, unlocked_willbeFinished 3, finished 4. 3 is what
  // rebuildAPSave writes for a checked location and what most of the chain
  // compares against; the thresholds above name their own so the two coins
  // conditions stay distinguishable.
  const PROGRESS_FINISHED = 3;

  // Returns the flags it turned on, so the caller can log a change without
  // logging every poll. Never turns one off: the game's chain does not either,
  // and a flag that flickered would hide the store button mid-session.
  function syncFeatureFlags(cp) {
    const opened = [];
    if (!cp) return opened;
    const levels = cp.levelProps || {};
    // getFeatureProps() builds this on demand and returns whatever is there,
    // so an object carrying only the keys below reads correctly: those are
    // set, every other flag is undefined and therefore still falsy, exactly as
    // the game's own all-false constructor leaves them.
    const feats = cp.features || (cp.features = {});
    for (const flag of Object.keys(FEATURE_UNLOCK_LEVELS)) {
      if (feats[flag]) continue;
      const met = FEATURE_UNLOCK_LEVELS[flag].some(function(cond) {
        const entry = levels[cond[0]];
        return !!entry && entry.progress >= cond[1];
      });
      if (met) {
        feats[flag] = true;
        opened.push(flag);
      }
    }
    return opened;
  }

  // Reconstructs the AP save slot entirely from AP state.
  // Plants = received items; level progress = checked locations; worlds = received keys.
  // Called after Connected, after each ReceivedItems, and in the poll loop.
  function rebuildAPSave() {
    const APP = window._AP_AllPlayerProperties;
    if(!APP || !APP.currentPlayer) return;

    // 0a. currentPlayer is not always an element of allPlayers, and savePP()
    // serialises allPlayers:
    //     savePP() { localStorage.setItem(KEY, JSON.stringify(allPlayers)) }
    // so every write against an orphaned currentPlayer is discarded silently.
    // savePP returns normally, the value is right in memory, and nothing
    // reaches disk.
    //
    // Measured at startup (2026-08-16): currentPlayer was an orphan
    // (indexOf === -1) carrying the previous session's feature flags. The
    // balance restore ran against it and logged success; the splash scene then
    // finished, getPlayer() re-read localStorage, and a second object took its
    // place at coin 0 with the flags unset. That is the whole restart bug --
    // in-session saves work because currentPlayer IS in the array by then.
    //
    // Prefer the marked entry already in the array: it is what savePP writes
    // and what the game reloads. Only push the orphan when nothing else claims
    // the slot, since pushing while a marked entry exists would duplicate it.
    const _all = APP.allPlayers || (APP.allPlayers = []);
    if(_all.indexOf(APP.currentPlayer) < 0){
      const _marked = _all.findIndex(p => p && p._ap_managed === true);
      if(_marked >= 0){
        APP.currentPlayer = _all[_marked];
      } else {
        _all.push(APP.currentPlayer);
      }
      log('Reattached the save slot: writes were not reaching disk');
    }
    const cp = APP.currentPlayer;

    // 0. Keep the slot marker and index pinned to whatever object the game
    // actually loaded. The stored index is a fixed number into an array whose
    // length changes, and getPlayer() answers an out-of-range PlayerIndex by
    // creating a fresh player and pushing it -- so currentPlayer can end up at
    // a different index than the one we think we own, with coin/gem back at
    // 0 and everything previously saved stranded in an entry nothing loads.
    // Re-stamping the marker and rewriting the index each rebuild makes that
    // self-correcting instead of permanent.
    cp._ap_managed = true;
    const liveIdx = (APP.allPlayers || []).indexOf(cp);
    if(liveIdx >= 0 && String(liveIdx) !== localStorage.getItem(AP_SLOT_IDX_KEY)){
      localStorage.setItem(AP_SLOT_IDX_KEY, String(liveIdx));
    }

    // 1. Rebuild granted plant set
    if(!window._AP_grantedPlantIds) window._AP_grantedPlantIds = new Set();
    else window._AP_grantedPlantIds.clear();
    (st.receivedItems||[]).forEach(name => {
      const pid = ITEM_PLANT[name];
      if(pid !== undefined) window._AP_grantedPlantIds.add(pid);
    });

    // 2. Clear all AP-known plants, then grant only received ones
    const knownCns = new Set(Object.values(ID_TO_CN));
    if(!cp.plantProps) cp.plantProps = {};
    for(const cn of Object.keys(cp.plantProps)) {
      if(knownCns.has(cn)) delete cp.plantProps[cn];
    }
    for(const pid of window._AP_grantedPlantIds) {
      const cn = ID_TO_CN[pid];
      // tutorialLevel>0 keeps the game's isTeacher flag false, suppressing
      // the "first placement" description tip -- since this object is
      // recreated from scratch every poll, tutorialLevel:0 here would make
      // the game re-show the tip every time a plant is placed, not just once.
      // Costumes come from st, not from whatever was in the save: this object
      // is rebuilt from scratch every poll, so anything the game wrote here
      // is about to be discarded. costume is the one being worn -- the most
      // recently granted, matching what unlockPlantCostume() does.
      const owned = ownedCostumes(pid);
      if(cn) cp.plantProps[cn] = {progress:1,medal:false,tutorialLevel:1,boost:0,
        costume: wornCostume(pid), costumes: owned.slice()};
    }

    // 2b. Same treatment for the permanent upgrades, when this seed shuffles
    // them. Reconciling the whole set every poll -- rather than only granting
    // on receipt -- is what takes an upgrade back off the player if some path
    // the unlockUpgrade() hook does not cover managed to set it.
    //
    // This goes through the game's own accessors rather than writing
    // cp.upgradeProps directly. upgradeProps is a LEGACY field: the first
    // getUpgradeProgressProps() call folds it into cp.player_upgrades and
    // then sets it to undefined, so a write here would take effect once and
    // silently stop mattering. getUpgradeProgressProps() returns the live
    // store, keyed by codename, which is the same thing
    // getUpgradeProgressByID() looks names up in.
    //
    // progress 2 is the game's `obtained`. 1 is `unlocked_willBeObtained`,
    // which leaves the upgrade queued for a pickup animation the player never
    // earned. The game applies an upgrade whenever progress > 0 and enabled.
    const grantedUpgrades = syncGrantedUpgrades();
    if(window._AP_shuffleUpgrades && APP.getUpgradeProgressProps){
      try {
        const props = APP.getUpgradeProgressProps();
        if(props){
          for(const cn of window._AP_knownUpgradeCns){
            const want = grantedUpgrades.has(cn) ? 2 : 0;
            let entry = props[cn];
            if(!entry){
              // Absent and not granted is already the desired state; leave it
              // alone rather than materialising an entry for every upgrade.
              if(!want) continue;
              // getUpgradeProgressByID both builds the entry the way the game
              // expects and stores it, so let it do that instead of guessing
              // the shape.
              entry = APP.getUpgradeProgressByID ? APP.getUpgradeProgressByID(cn) : null;
              if(!entry) continue;
            }
            if(entry.progress !== want) entry.progress = want;
            if(want && entry.enabled === false) entry.enabled = true;
          }
        }
      } catch(e) {}
    }

    // 3. Reset AP-tracked level progress, then restore checked locations
    if(!cp.levelProps) cp.levelProps = {};
    for(const lvl of new Set(Object.values(LOC_LEVELS))) delete cp.levelProps[lvl];
    for(const locName of (st.checked||[])) {
      const lvl = LOC_LEVELS[locName];
      if(lvl) cp.levelProps[lvl] = { progress: 3 };
    }

    // 4. Unlock worlds for received keys.
    if(!cp.worldProps) cp.worldProps = {};
    const unlockWorld = (wid) => {
      if(!cp.worldProps[wid]) cp.worldProps[wid] = {};
      cp.worldProps[wid].unlocked = true;
    };
    (st.receivedKeys||[]).forEach(keyName => {
      const worldIds = WORLD_KEY_MAP[keyName];
      // Modern Day is never key-driven; it is handled below. Older seeds can
      // still deliver a Modern Day Key, and honouring it here would open the
      // world before the goal is met -- fireCheck() would then withhold its
      // location checks, so any progress made there would silently not count.
      if(worldIds) worldIds.forEach(wid => { if(wid !== W.modern) unlockWorld(wid); });
    });
    // Modern Day unlocks on the world-goal requirement alone.
    if(canAccessModernDay()) unlockWorld(W.modern);

    // 5. Set forceLevel based on tutorial progress
    const tutSteps = ['tutorial1','tutorial2','tutorial3','tutorial4'];
    if(skipTutorial) {
      cp.forceLevel = '';
    } else {
      let fl = 'tutorial1';
      for(const tut of tutSteps) {
        const loc = Object.keys(LOC_LEVELS).find(k => LOC_LEVELS[k] === tut);
        if(loc && isChecked(loc)) {
          const ni = tutSteps.indexOf(tut) + 1;
          fl = ni < tutSteps.length ? tutSteps[ni] : '';
        } else { break; }
      }
      cp.forceLevel = fl;
    }

    // 5b. Mark the feature tutorials as already seen. Runs every rebuild rather
    // than once, because the flags live in the save and a feature can unlock at
    // any point -- the almanac at egypt2, the zen garden at egypt5, the store at
    // egypt6 -- so there is no single moment to do it. getTutorialProps() builds
    // the object on demand and returns whatever is there, so an object with only
    // these keys set is read exactly as intended: the six are seen, everything
    // else is still falsy and still runs.
    if(skipTutorial) {
      const tut = cp.tutorial || (cp.tutorial = {});
      for(const flag of FEATURE_TUTORIAL_FLAGS) tut[flag] = true;
    }

    // 5c. Re-derive the game's feature flags from level progress. Runs after
    // step 3 has rebuilt levelProps, so it reads exactly what the game would.
    // Unconditional on skipTutorial: this is not about suppressing a prompt,
    // it is about coins dropping and buttons existing at all.
    const _opened = syncFeatureFlags(cp);
    if(_opened.length) log('Unlocked feature(s) from level progress: ' + _opened.join(', '));

    try { APP.savePP(); } catch(e) {}

    // 6. Currency, in order: put back what the boot wipe took, then flush any
    // grant that couldn't be applied earlier (no player slot loaded at the
    // time, or the UI component wasn't up yet), then record the result as the
    // balance to restore to next boot. Observing last is what keeps the wiped
    // 0 from becoming the remembered balance.
    // A newly built component may have just overwritten the balance, so let
    // the restore run again for it. Checked before restoring, seeded after, so
    // the component ends the pass agreeing with whatever the player now holds.
    const _compChanged = currencyComponentChanged();
    if(_compChanged) _currencyRestoreDone = false;
    const _restored = restoreLostCurrency();
    if(_restored.length) log('Restored balance the display overwrote: ' + _restored.join(', '));
    applyPendingCurrency();
    // After the grants, so a grant and a trap arriving in the same batch net
    // out in the player's favour rather than the trap taking from the older,
    // smaller balance.
    const _taken = applyCurrencyTraps();
    for(const t of _taken){
      toast((t[0] === 'coin' ? '🪙 ' : '💎 ') + '-' + t[1]
            + (t[0] === 'coin' ? ' Coins' : ' Gems'), '#f66');
    }
    syncCurrencyDisplay();
    observeCurrency(_compChanged);
  }

  // forceLevel order for tutorial progression
  const TUTORIAL_ORDER = ['tutorial1','tutorial2','tutorial3','tutorial4','egypt1'];

  function isTutorialComplete() {
    const APP = window._AP_AllPlayerProperties;
    const fl = (APP && APP.currentPlayer ? APP.currentPlayer.forceLevel : null) || '';
    return !['tutorial1','tutorial2','tutorial3','tutorial4'].includes(fl);
  }

  function isTutorialDone(tutorialId) {
    const APP = window._AP_AllPlayerProperties;
    const forceLevel = (APP && APP.currentPlayer ? APP.currentPlayer.forceLevel : null) || '';
    const myIdx = TUTORIAL_ORDER.indexOf(tutorialId);
    if(myIdx < 0) return false;
    if(forceLevel === '') return true;
    const forceLevelIdx = TUTORIAL_ORDER.indexOf(forceLevel);
    if(forceLevelIdx < 0) return true;
    return forceLevelIdx > myIdx;
  }

  function isFinished(levelId) {
    if(TUTORIAL_ORDER.includes(levelId)) return isTutorialDone(levelId);
    const APP = window._AP_AllPlayerProperties;
    const cp = APP ? APP.currentPlayer : null;
    const lp = cp ? cp.levelProps : null;
    if(!lp) return false;
    const e = lp[levelId]; return e && (e.progress||0) >= 3;
  }

  // ── WebSocket / AP Protocol ───────────────────────────────────────────────
  let ws=null, conn=false, rtimer=null, rdelay=5000;
  let locIds={}, itemNames={}, idToLoc={};

  // Scheme probe order for an address typed without one. wss:// leads because
  // every hosted room requires it; ws:// is the fallback for a self-hosted or
  // LAN server with no certificate. cfg.scheme remembers the winner.
  const WS_SCHEMES  = ['wss://', 'ws://'];
  const WS_SCHEME_RE = /^wss?:\/\//i;
  // True once this connect cycle has already fallen back, so the probe runs at
  // most once per cycle rather than ping-ponging between the two schemes.
  let schemeProbed = false;

  // Shopsanity card labels. A shop card is a location, so what the player is
  // buying is whatever the multiworld put there -- which may belong to another
  // slot, and to another game entirely.
  //
  // Three pieces have to line up: LocationScouts says which item id sits on
  // each shop location, slot_info says which game that item's owner plays, and
  // that game's DataPackage turns the id into a name. They arrive in that
  // order, so the label is computed lazily on read rather than baked once.
  //
  // All three are persisted on st, so reopening the store after a reload shows
  // the labels straight away instead of waiting on a reconnect. Seeded from st
  // right here rather than from the startup block further up: these are `let`
  // bindings, so a call from up there would hit the temporal dead zone and
  // throw at load -- taking the whole client with it. st is already restored
  // from localStorage by the time this line runs.
  let itemNamesByGame = st.itemNamesByGame || {};   // game -> { item id: name }
  let slotGame        = st.slotGame        || {};   // slot id -> game name
  let slotName        = st.slotName        || {};   // slot id -> player name
  let shopScout       = st.shopScout       || {};   // commodity -> {item, player}

  // Mirrors shopsanity onto window for the store hook, which lives in the
  // other IIFE and cannot see st. Also kicks off building the logo sprite,
  // which is a no-op once it has one.
  function syncShopConfig(){
    window._AP_shopsanity = !!st.shopsanity;
    if(window._AP_shopsanity && window._AP_initApLogo) window._AP_initApLogo();
  }

  function saveShopLabelCache(){
    st.itemNamesByGame = itemNamesByGame;
    st.slotGame        = slotGame;
    st.slotName        = slotName;
    st.shopScout       = shopScout;
    svSt();
  }

  // Ask for every shop location at once, with create_as_hint 0 so this reveals
  // the items to us without spending anyone's hints or announcing them.
  // Read straight off locIds by prefix rather than from a copy of the
  // commodity list -- location_name_to_id is the server's own answer to which
  // shop locations exist, so this cannot drift from constants.py.
  function scoutShopLocations(){
    if(!st.shopsanity) return;
    const ids = Object.keys(locIds)
      .filter(n => n.startsWith('Shop: '))
      .map(n => locIds[n]);
    if(!ids.length) return;   // DataPackage not in yet; it re-runs this on arrival
    send([{cmd:'LocationScouts', locations:ids, create_as_hint:0}]);
  }

  // Fetch the DataPackage for the games the scouted items actually belong to,
  // and nothing else. Asking for every game in the room would pull megabytes
  // in a large async multiworld to name at most 39 items.
  function fetchScoutedGames(){
    const wanted = new Set();
    for(const cn of Object.keys(shopScout)){
      const game = slotGame[shopScout[cn].player];
      if(game && !itemNamesByGame[game]) wanted.add(game);
    }
    if(wanted.size) send([{cmd:'GetDataPackage', games:[...wanted]}]);
  }

  // commodity name -> what to show on the card, or null to leave it as the
  // game built it (nothing scouted, or the owning game's names not in yet).
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
  let apTeam=0, apSlotId=0; // set from Connected; namespaces DataStorage keys

  function connect() {
    if(!cfg.slot){setStatus('Enter slot name','#fa0');return;}
    // First connect: create the dedicated AP save slot, then reload so the game
    // loads it fresh (the getItem intercept will redirect PlayerIndex going forward).
    if(!localStorage.getItem(AP_SLOT_IDX_KEY)) {
      const apIdx = findOrCreateAPSlot();
      if(apIdx < 0) { setStatus('Could not create AP save slot','#f44'); return; }
      log('AP save slot created at index ' + apIdx + ' — reloading…');
      toast('AP save created — reloading…','#fa0');
      setTimeout(()=>window.location.reload(), 1500);
      return;
    }
    if(ws){try{ws.onclose=null;ws.close();}catch(e){}ws=null;}
    setStatus('Connecting…','#fa0');
    // The address box takes a bare host:port, so the client picks the scheme.
    // Hosted rooms -- multiworld.gg, archipelago.gg -- are TLS only, and answer
    // a plain ws:// handshake by closing the socket before replying, which the
    // browser reports as "Connection closed before receiving a handshake
    // response". A self-hosted or LAN server usually has no certificate and
    // only speaks ws://. So try wss:// first and fall back once, and remember
    // whichever answered so a reconnect does not pay for the probe again.
    const explicit = WS_SCHEME_RE.test(cfg.server);
    const scheme = explicit ? ''
                 : (WS_SCHEMES.indexOf(cfg.scheme) >= 0 ? cfg.scheme : WS_SCHEMES[0]);
    let opened = false;
    try {
      ws=new WebSocket(explicit ? cfg.server : scheme + cfg.server);
      // Only that the socket opened, not that the server liked us -- enough to
      // tell "wrong scheme" apart from "rejected", which is the whole question.
      ws.onopen=()=>{
        opened=true; schemeProbed=false;
        if(!explicit && cfg.scheme!==scheme){ cfg.scheme=scheme; svCfg(); }
      };
      ws.onmessage=e=>{try{JSON.parse(e.data).forEach(onPkt);}catch(ex){}};
      ws.onclose=()=>{
        conn=false;sessionActive=false;goalSent=false;ws=null;setStatus('Disconnected','#f44');
        // Closed without ever opening, on an address that named no scheme: the
        // OTHER scheme is worth one immediate try before the backoff loop, so a
        // plain-ws server is not stuck behind a 5s wait on every attempt. "The
        // other" rather than "the next" matters when cfg.scheme is a remembered
        // ws:// and the player has since moved to a hosted room.
        const alt = (!explicit && !opened && !schemeProbed)
                  ? WS_SCHEMES.find(s => s !== scheme) : null;
        if(alt){
          schemeProbed=true; cfg.scheme=alt; svCfg();
          setStatus('Retrying over '+alt.replace('://','')+'…','#fa0');
          rtimer=setTimeout(connect,300);
          return;
        }
        // Both failed. Clearing the flag in the backoff callback gives every
        // cycle one fresh pair of attempts, so a server that only later comes
        // up with TLS is still found instead of being pinned to the loser.
        rtimer=setTimeout(()=>{
          schemeProbed=false;
          rdelay=Math.min(rdelay*1.5,30000);
          connect();
        },rdelay);
      };
      ws.onerror=()=>{};
    } catch(e) { setStatus('Connection failed: '+e.message,'#f44'); }
  }

  function send(pkts){if(ws&&ws.readyState===1)ws.send(JSON.stringify(pkts));}

  // ── Server -> local check sync ────────────────────────────────────────────
  // The server tracks every location this slot has ever checked, but the
  // client only ever marked levels cleared from its own st.checked. Anything
  // the server knew and we didn't -- wiped localStorage, a second machine, a
  // seed resumed after an AP state reset -- left the save with those levels
  // still locked, so the player had to replay them to get past.
  // Fold the server's list in so rebuildAPSave() can restore the progression.
  let serverCheckedIds = [];

  function mergeServerChecks(){
    if(!serverCheckedIds.length) return;
    // Needs the DataPackage; Connected and DataPackage can arrive in either
    // order, so this is called from both and no-ops until the map exists.
    if(!idToLoc || !Object.keys(idToLoc).length) return;
    let added = 0;
    // Local Set rather than isChecked(): this loop pushes as it goes, which
    // would invalidate the shared mirror on every iteration and rebuild it
    // each time. One Set built up front stays O(n + m).
    const known = new Set(st.checked);
    for(const id of serverCheckedIds){
      const name = idToLoc[id];
      if(name && !known.has(name)){ st.checked.push(name); known.add(name); added++; }
    }
    serverCheckedIds = [];
    if(added){
      svSt();
      rebuildAPSave();
      log('Restored ' + added + ' check(s) from server');
      toast('↺ Restored ' + added + ' check(s)', '#4af');
    }
  }

  function onPkt(pkt) {
    switch(pkt.cmd){
      case 'RoomInfo':
        rdelay=5000;
        // Capture seed_name to key our state to this specific run
        window._AP_seedName = pkt.seed_name || '';
        send([{cmd:'GetDataPackage',games:[GAME_NAME]}]);
        send([{cmd:'Connect',game:GAME_NAME,name:cfg.slot,password:cfg.password||'',
               version:{...AP_VER,class:'Version'},tags:['AP'],items_handling:0b111,
               uuid:'pvz2ge_'+cfg.slot,slot_data:true}]);
        break;
      case 'Connected':
        conn=true;sessionActive=true;setStatus('✓ '+cfg.slot,'#4f4');
        apTeam   = pkt.team || 0;
        apSlotId = pkt.slot || 0;
        // Check if this is a different seed/slot from last session
        const runKey = cfg.slot + '@' + (window._AP_seedName||'');
        if(st.runKey !== runKey){
          // upgradeCounts is a running tally rather than a deduplicated list,
          // so it has to be cleared here explicitly -- carrying it into a new
          // seed would grant upgrades that seed never sent.
          st = { checked:[], lastIdx:0, receivedKeys:[], receivedItems:[],
                 upgradeCounts:{}, costumes:{}, wornCostume:{}, pendingCostumes:0, runKey };
          window._AP_grantedPlantIds = new Set();
          window._AP_grantedUpgrades = new Set();
          // st was replaced wholesale, so the in-memory shop label maps are
          // now the previous seed's placements. Dropping them here stops a
          // card being labelled with an item this seed never put there.
          itemNamesByGame = {}; slotGame = {}; slotName = {}; shopScout = {};
          svSt();
          toast('New seed detected — state reset','#fa0');
        }
        // Who plays what, so a scouted item id can be turned into a name and
        // attributed. slot_info is keyed by slot id as a string.
        slotGame = {}; slotName = {};
        for(const [sid, info] of Object.entries(pkt.slot_info || {})){
          slotGame[sid] = info && info.game;
          slotName[sid] = (info && info.name) || '';
        }
        // Aliases beat slot names when a player has set one.
        for(const p of (pkt.players || [])){
          if(p && p.alias) slotName[p.slot] = p.alias;
        }
        if(pkt.slot_data){
          st.goalLocs  = pkt.slot_data.goal_locations  || [];
          st.worldsReq = pkt.slot_data.worlds_required || 7;
          st.shopsanity = !!pkt.slot_data.shopsanity;
          st.victoryLoc = pkt.slot_data.modern_day_victory || 'modern_zomboss_01_egypt';
          skipTutorial = !!pkt.slot_data.skip_tutorial;
          // Absent on seeds generated before the option existed, which reads
          // as off -- the game keeps granting upgrades itself and nothing is
          // withheld. The item map is persisted alongside it so a reload can
          // rebuild the granted set before the socket is back.
          st.shuffleUpgrades = !!pkt.slot_data.shuffle_upgrades;
          st.upgradeItems    = pkt.slot_data.upgrade_items || {};
          syncGrantedUpgrades();
          st.randomizeConveyor = !!pkt.slot_data.randomize_conveyor;
          st.conveyorSeed      = pkt.slot_data.conveyor_seed || 0;
          syncConveyorConfig();
          // Absent on seeds predating the option, which reads as off. The
          // tiers are persisted on st alongside the flag so a page reload can
          // keep shuffling before the socket is back up, the same way the
          // conveyor config does.
          st.shuffleZombies = !!pkt.slot_data.shuffle_zombies;
          st.zombieSeed     = pkt.slot_data.zombie_seed || 0;
          st.zombieTiers    = pkt.slot_data.zombie_tiers || {};
          syncZombieConfig();
          syncShopConfig();
          svSt();
          // DeathLink isn't known until slot_data arrives (after the initial
          // Connect), so it's applied via ConnectUpdate rather than being in
          // the Connect packet's tags from the start.
          deathLinkEnabled = !!pkt.slot_data.death_link;
          if(deathLinkEnabled) send([{cmd:'ConnectUpdate', tags:['AP','DeathLink']}]);
        }
        // Locations the server already has for this slot. Merged in before
        // the rebuild so any level we'd forgotten comes back marked cleared.
        serverCheckedIds = (pkt.checked_locations || []).slice();
        mergeServerChecks();
        rebuildAPSave();
        const ids=st.checked.map(n=>locIds[n]).filter(Boolean);
        if(ids.length) send([{cmd:'LocationChecks',locations:ids}]);
        send([{cmd:'Sync'}]);
        fetchCurrencyFromServer();
        // Needs locIds, so this no-ops if the DataPackage has not landed yet
        // -- its handler calls this too, and the two can arrive either way round.
        scoutShopLocations();
        break;
      case 'RoomUpdate':
        // Checks can also land mid-session (another client on this slot, or
        // an admin !collect).
        if(pkt.checked_locations && pkt.checked_locations.length){
          serverCheckedIds = serverCheckedIds.concat(pkt.checked_locations);
          mergeServerChecks();
        }
        break;
      case 'ConnectionRefused':
        setStatus('Refused: '+(pkt.errors||[]).join(', '),'#f44');break;
      case 'ReceivedItems':
        (pkt.items||[]).forEach((item,i)=>{
          const gi=(pkt.index||0)+i;
          if(gi<st.lastIdx) return;
          const name=itemNames[item.item];
          if(name){
            if(!st.receivedItems) st.receivedItems=[];
            if(!st.receivedItems.includes(name)) st.receivedItems.push(name);
            applyItem(name);
          }
          st.lastIdx=gi+1;
        });
        svSt();
        rebuildAPSave();
        break;
      case 'DataPackage': {
        const allGames=(pkt.data&&pkt.data.games)||{};
        // Every game in the payload, not just ours: the follow-up request for
        // the games owning scouted shop items comes back through here too.
        for(const[game,data] of Object.entries(allGames)){
          const byId={};
          for(const[n,id] of Object.entries(data.item_name_to_id||{})) byId[id]=n;
          itemNamesByGame[game]=byId;
        }
        const gd=allGames[GAME_NAME];
        if(gd){
          locIds=gd.location_name_to_id||{};
          itemNames=itemNamesByGame[GAME_NAME]||{};
          idToLoc={};
          for(const[n,id] of Object.entries(locIds)) idToLoc[id]=n;
          // Connected may have landed first, with ids we couldn't name yet.
          mergeServerChecks();
          // ...and the scout needs locIds, so it may have been skipped there.
          scoutShopLocations();
        }
        saveShopLabelCache();
        break;
      }
      case 'LocationInfo': {
        // Answers our LocationScouts. Only the shop locations were asked for,
        // but filter by name anyway so a scout from anywhere else cannot end
        // up labelling a card.
        let found=0;
        for(const it of (pkt.locations||[])){
          const name=idToLoc[it.location];
          if(!name||!name.startsWith('Shop: ')) continue;
          shopScout[name.slice(6)]={item:it.item,player:it.player};
          found++;
        }
        if(found){
          saveShopLabelCache();
          // Names for the owning games, which are usually not ours. Comes
          // back through the DataPackage case above.
          fetchScoutedGames();
        }
        break;
      }
      case 'Bounced':
        if(deathLinkEnabled && pkt.tags && pkt.tags.includes('DeathLink') &&
           pkt.data && pkt.data.source !== cfg.slot) {
          applyRemoteDeath(pkt.data);
        }
        break;
      case 'Retrieved': {
        // Server-side backup of the granted currency totals. Only ever adopt
        // a HIGHER value: local may legitimately be ahead (grants received
        // while offline), and taking a lower one would re-grant on the next
        // poll since applied would exceed granted.
        const ck = currencyKeys();
        const kv = pkt.keys || {};
        let restored = false;
        for(const c of CURRENCY_FIELDS){
          const v = kv[c.field === 'coin' ? ck.coin : ck.gem];
          if(typeof v === 'number' && v > (st[c.granted]||0)){
            st[c.granted] = v;
            restored = true;
          }
        }
        if(restored){ svSt(); applyPendingCurrency(); }
        pushCurrencyToServer(); // push local back up if we were ahead
        break;
      }
    }
  }

  // ── DeathLink ─────────────────────────────────────────────────────────────
  let deathLinkEnabled = false;
  let suppressDeathLinkSend = false;
  let lastDeathLinkSentAt = 0;

  // Called (via window._AP_onGameLose) from the loseDarken hook installed on
  // the game's UI class the moment a level is actually lost.
  window._AP_onGameLose = function(){
    if(!deathLinkEnabled || suppressDeathLinkSend) return;
    const now = Date.now();
    if(now - lastDeathLinkSentAt < 3000) return; // debounce: loseDarken can
    lastDeathLinkSentAt = now;                   // fire more than once per loss
    // 'Bounce' is the client->server command; 'Bounced' is what the server
    // sends back out (see the onPkt case). Sending 'Bounced' here is not a
    // command the server recognises, so nothing gets broadcast.
    // No 'games' filter: DeathLink should reach every slot carrying the tag,
    // not just other players of this game.
    send([{cmd:'Bounce', tags:['DeathLink'],
           data:{time: now/1000, source: cfg.slot, cause: cfg.slot+' lost a level'}}]);
  };

  function applyRemoteDeath(data){
    const inst = window._AP_UI && window._AP_UI.component;
    if(!inst) return; // not currently in a level -- can't kill what isn't running
    // loseDarken is itself hooked to send DeathLink on loss; suppress that
    // while we're the ones triggering it, or this becomes an infinite ping-pong.
    suppressDeathLinkSend = true;
    try { inst.loseDarken(null, data.cause || ((data.source||'Someone')+' died'), ''); }
    catch(e) {}
    setTimeout(()=>{ suppressDeathLinkSend = false; }, 500);
    toast('💀 '+(data.cause || ((data.source||'Someone')+' died')), '#f66');
  }

  function applyItem(name) {
    // Track keys for Modern Day check; actual game-state changes happen in rebuildAPSave
    if(WORLD_KEY_MAP[name]){
      if(!st.receivedKeys) st.receivedKeys=[];
      if(!st.receivedKeys.includes(name)) st.receivedKeys.push(name);
      svSt();
      toast('🔑 '+name,'#fa0');
      return;
    }
    if(ITEM_PLANT[name]!==undefined){ toast('🌱 '+name,'#4f4'); return; }
    // Permanent upgrades. rebuildAPSave() runs straight after every
    // ReceivedItems and reconciles the game's upgrade state against the
    // granted set, so the grant itself is handled there; this only has to
    // count the copy and say something.
    // Counting here is safe against the post-connect replay for the same
    // reason the coin/gem running totals are: applyItem() is only reached for
    // items at or past st.lastIdx, so a replayed item is never counted twice.
    if(name === COSTUME_TRAP){
      // Applied straight away rather than queued like the mower trap: it only
      // rewrites saved state, so it does not need a level to be running, and
      // a player with no costumes yet simply has nothing to scramble.
      if(!shuffleCostumes()) toast('🎭 Costume Shuffle — nothing to scramble', '#f66');
      return;
    }
    if(name === RANDOM_COSTUME){
      // Banked first, then drained: grantRandomCostume() can legitimately fail
      // (no plants yet, or every costume already worn) and the bank is what
      // makes that recoverable on a later poll.
      st.pendingCostumes = (st.pendingCostumes || 0) + 1;
      svSt();
      applyPendingCostumes();
      return;
    }
    const upgradeCns = (st.upgradeItems||{})[name];
    if(upgradeCns){
      if(!st.upgradeCounts) st.upgradeCounts = {};
      st.upgradeCounts[name] = (st.upgradeCounts[name]||0) + 1;
      svSt();
      syncGrantedUpgrades();
      // "2/3" for a progressive group, plain for the one-shot upgrades.
      const held = Math.min(st.upgradeCounts[name], upgradeCns.length);
      const label = upgradeCns.length > 1
        ? name + ' (' + held + '/' + upgradeCns.length + ')' : name;
      toast('⭐ '+label,'#a78bfa');
      return;
    }
    // Currency fillers (e.g. "500 Coins", "20 Gems"). Only the cumulative
    // GRANTED total is recorded here; actually pushing it into the game is
    // applyPendingCurrency()'s job. Applying inline would silently drop the
    // grant whenever currentPlayer isn't loaded yet -- which is exactly the
    // case during the Sync item replay right after connecting -- and
    // st.lastIdx would then stop it from ever being reprocessed.
    // Currency traps ("-500 Coins", "-20 Gems"). Queued rather than applied
    // inline for the same reason grants are: currentPlayer is often absent
    // during the post-connect Sync replay, and st.lastIdx would stop a dropped
    // one from ever being reprocessed. Queued as a running total per currency,
    // so several arriving at once are taken together.
    const currencyTrapMatch = /^-(\d+) (Coins|Gems)$/.exec(name);
    if(currencyTrapMatch){
      const amount = parseInt(currencyTrapMatch[1], 10);
      const isCoin = currencyTrapMatch[2] === 'Coins';
      const key = isCoin ? 'coinDebt' : 'gemDebt';
      st[key] = (st[key]||0) + amount;
      svSt();
      applyCurrencyTraps();
      return;
    }
    const currencyMatch = /^(\d+) (Coins|Gems)$/.exec(name);
    if(currencyMatch){
      const amount = parseInt(currencyMatch[1], 10);
      const isCoin = currencyMatch[2] === 'Coins';
      const grantedKey = isCoin ? 'coinGranted' : 'gemGranted';
      st[grantedKey] = (st[grantedKey]||0) + amount;
      svSt();
      pushCurrencyToServer();
      applyPendingCurrency();
      toast((isCoin ? '🪙 ' : '💎 ') + name, '#fbbf24');
      return;
    }
    if(name === LAWN_MOWER_TRAP){
      // Queue rather than fire-and-forget: traps replayed during the
      // post-connect Sync (or received on the world map) would otherwise be
      // wasted, since there are no mowers to remove outside a level.
      st.pendingMowerTraps = (st.pendingMowerTraps||0) + 1;
      svSt();
      applyPendingTraps();
      return;
    }
    toast('📦 '+name,'#4af');
  }

  // ── Currency (coins / gems) ───────────────────────────────────────────────
  // st.coinGranted/gemGranted = cumulative total AP has ever awarded.
  // st.coinApplied/gemApplied = how much of that has been pushed into the
  // game. The difference is applied whenever a player slot is available, so
  // a grant is never lost just because it arrived at a bad moment. Spending
  // in-game lowers the balance but not these counters, so nothing is
  // re-granted afterwards.
  const CURRENCY_FIELDS = [
    { field:'coin', granted:'coinGranted', applied:'coinApplied',
      seen:'coinSeen',
      cls:function(){ return window._AP_CoinCount; }, add:'addCoinCount' },
    { field:'gem',  granted:'gemGranted',  applied:'gemApplied',
      seen:'gemSeen',
      cls:function(){ return window._AP_GemCount; },  add:'addGemCount' },
  ];

  // ── The boot wipe ─────────────────────────────────────────────────────────
  // The game contains exactly ONE write to a player's coin or gem in the whole
  // bundle -- the HUD component's value setter:
  //     addCoinCount(n) { this.value += n; }
  //     onValueSet(n)   { currentPlayer.coin = n; savePP(); }
  // and its load does `this._shownValue = currentPlayer.coin; this.value =
  // this._shownValue`. At boot that runs against a currentPlayer that is not
  // the loaded save yet, reads 0, and writes the 0 straight through. So every
  // restart begins with the balance erased, before anything is on screen.
  //
  // Measured, not inferred (2026-08-16): 12345 written and confirmed in
  // localStorage, then location.reload() with no shutdown at all -- 0 on the
  // other side. A save/restart loses it the same way.
  //
  // st.coinSeen/gemSeen is the last balance the client actually observed on
  // the live player, refreshed every poll. Restoring the shortfall puts back
  // only what was seen; it can never invent currency.
  //
  // Once per session, because the wipe happens once, at boot. Spending later
  // also lowers the balance and must NOT be undone -- after this has run,
  // observeCurrency() simply follows the balance down.
  let _currencyRestoreDone = false;

  function restoreLostCurrency(){
    if(_currencyRestoreDone) return [];
    const APP = window._AP_AllPlayerProperties;
    const cp  = APP ? APP.currentPlayer : null;
    if(!cp) return []; // no player yet; retried on the next poll
    _currencyRestoreDone = true;
    const restored = [];
    for(const c of CURRENCY_FIELDS){
      const seen = st[c.seen] || 0;
      const have = cp[c.field] || 0;
      const short = seen - have;
      if(short <= 0) continue;
      // Through the component where possible, exactly as applyPendingCurrency
      // does: its setter owns the displayed value, and writing cp directly
      // behind its back leaves the HUD showing the old number until the next
      // addCoinCount overwrites the save with it.
      const comp = c.cls() && c.cls().component;
      if(comp && typeof comp[c.add] === 'function'){
        try { comp[c.add](short); } catch(e) { cp[c.field] = seen; }
      } else {
        cp[c.field] = seen;
      }
      restored.push(c.field + ' +' + short);
    }
    if(restored.length){ try { APP.savePP(); } catch(e) {} }
    return restored;
  }

  // Currency traps take from the balance. Queued as a debt per currency
  // (st.coinDebt/gemDebt) because currentPlayer is often absent when the item
  // arrives; the debt is cleared as soon as a player exists.
  //
  // A trap can never push a balance below zero. It takes min(balance, debt)
  // and FORGIVES the remainder rather than holding it against future income:
  // a hidden debt that silently ate the next coins earned would be a much
  // nastier item than the one the option describes.
  //
  // The ledger is lowered by hand here rather than left to observeCurrency.
  // A trap that empties a balance is a legitimate drop to exactly zero, which
  // is otherwise the one case observeCurrency refuses to record -- so without
  // this the next restore would hand the money straight back.
  function applyCurrencyTraps(){
    const APP = window._AP_AllPlayerProperties;
    const cp  = APP ? APP.currentPlayer : null;
    if(!cp) return []; // retried from rebuildAPSave() on the next poll
    const taken = [];
    let cleared = false;
    for(const c of CURRENCY_FIELDS){
      const debtKey = c.field + 'Debt';
      const debt = st[debtKey] || 0;
      if(debt <= 0) continue;
      const have = cp[c.field] || 0;
      const take = Math.min(have, debt);
      const left = have - take;
      st[debtKey] = 0;          // forgiven, not carried
      cleared = true;
      // Nothing to take from an empty balance. The debt is still cleared, but
      // it is not reported: the caller toasts whatever comes back, and a
      // "-0 Coins" toast is a lie about what happened.
      if(take <= 0) continue;
      // Through the component where there is one, so the display and the save
      // agree -- writing cp behind a live component's back leaves it holding
      // the old number for the next add to push back over the save.
      const comp = c.cls() && c.cls().component;
      if(comp && typeof comp.value === 'number'){
        try { comp.value = left; } catch(e) { cp[c.field] = left; }
      } else {
        cp[c.field] = left;
      }
      st[c.seen] = left;        // the ledger follows a trap down
      taken.push([c.field, take]);
    }
    if(taken.length){
      try { APP.savePP(); } catch(e) {}
    }
    if(cleared) svSt();
    return taken;
  }

  // The HUD component's setter writes an ABSOLUTE value, not a delta:
  //     addCoinCount(n) { this.value += n; }   // n added to ITS value
  //     onValueSet(n)   { currentPlayer.coin = n; savePP(); }
  // and it seeds its own `value` from the player once, at load. Whenever it
  // loads without the real save as currentPlayer it holds 0, and from then on
  // the first coin event of any kind -- a single coin picked up in a level,
  // value 0 -> 10 -- writes that absolute total straight over the balance.
  //
  // Measured on the world map (2026-08-16): cp.coin 2000 while component.value
  // sat at 0, ten seconds apart, with nothing rewriting cp in between. The
  // component simply never re-reads the player. So this is not a boot-time
  // event; it is a stale display waiting to overwrite the save.
  //
  // Seeding the component from the player each poll inverts that: the display
  // follows the save. Assigning `value` runs the same setter, so it also
  // rewrites cp with the value it already has and saves -- idempotent.
  let _lastCurrencyComp = {};

  // A component object we have not seen before has just initialised, and may
  // already have stamped its 0 over the balance -- so the restore is allowed
  // to run again. Identity, not presence: the component is torn down and
  // rebuilt on every scene change.
  function currencyComponentChanged(){
    let changed = false;
    for(const c of CURRENCY_FIELDS){
      const comp = (c.cls() && c.cls().component) || null;
      if(_lastCurrencyComp[c.field] !== comp){
        _lastCurrencyComp[c.field] = comp;
        if(comp) changed = true;
      }
    }
    return changed;
  }

  function syncCurrencyDisplay(){
    const APP = window._AP_AllPlayerProperties;
    const cp  = APP ? APP.currentPlayer : null;
    if(!cp) return [];
    const fixed = [];
    for(const c of CURRENCY_FIELDS){
      const comp = c.cls() && c.cls().component;
      if(!comp) continue;
      const have = cp[c.field] || 0;
      if(comp.value !== have){
        try { comp.value = have; fixed.push(c.field); } catch(e) {}
      }
    }
    return fixed;
  }

  // Records what the player actually holds, so the next launch has something
  // to restore to. Runs after restoreLostCurrency on the first poll, so a
  // wiped 0 is never what gets recorded.
  function observeCurrency(wipeSuspected){
    const APP = window._AP_AllPlayerProperties;
    const cp  = APP ? APP.currentPlayer : null;
    if(!cp) return;
    let dirty = false;
    for(const c of CURRENCY_FIELDS){
      const have = cp[c.field] || 0;
      // A balance at zero is ambiguous on its face: it is either the display
      // stamping over the save, or a player who spent their last coin. The
      // caller resolves it, because only a NEWLY BUILT component can have
      // stamped a zero -- and when one has, restoreLostCurrency ran earlier in
      // this same pass and already repaired the balance, so a zero still
      // standing here is a real spend.
      //
      // Recording a wipe is unrecoverable: it destroys the only record of the
      // balance and leaves the restore nothing to put back. Refusing to record
      // a spend is merely a refund. So when the two cannot be told apart, this
      // errs toward keeping the ledger.
      if(have === 0 && wipeSuspected && (st[c.seen] || 0) > 0) continue;
      if(st[c.seen] !== have){ st[c.seen] = have; dirty = true; }
    }
    if(dirty) svSt();
  }

  function applyPendingCurrency(){
    const APP = window._AP_AllPlayerProperties;
    const cp  = APP ? APP.currentPlayer : null;
    if(!cp) return; // retried from rebuildAPSave() on the next poll
    let dirty = false;
    for(const c of CURRENCY_FIELDS){
      const pending = (st[c.granted]||0) - (st[c.applied]||0);
      if(pending <= 0) continue;
      const comp = c.cls() && c.cls().component;
      if(comp && typeof comp[c.add] === 'function'){
        // Preferred path: the live UI component owns the value while it
        // exists, and its setter writes currentPlayer + saves for us.
        try { comp[c.add](pending); } catch(e) { continue; }
      } else {
        cp[c.field] = (cp[c.field]||0) + pending;
        try { APP.savePP(); } catch(e) {}
      }
      st[c.applied] = (st[c.applied]||0) + pending;
      dirty = true;
    }
    if(dirty) svSt();
  }

  // AP DataStorage keys are shared across the whole room, so they must be
  // namespaced per team+slot.
  function currencyKeys(){
    return { coin:'pvz2ge_coin_'+apTeam+'_'+apSlotId,
             gem: 'pvz2ge_gem_'+apTeam+'_'+apSlotId };
  }

  function pushCurrencyToServer(){
    if(!conn) return;
    const k = currencyKeys();
    // 'max' rather than 'replace': the granted totals only ever increase, so
    // a stale client can never lower the stored value.
    send([
      {cmd:'Set', key:k.coin, default:0, want_reply:false,
       operations:[{operation:'max', value: st.coinGranted||0}]},
      {cmd:'Set', key:k.gem,  default:0, want_reply:false,
       operations:[{operation:'max', value: st.gemGranted||0}]},
    ]);
  }

  function fetchCurrencyFromServer(){
    if(!conn) return;
    const k = currencyKeys();
    send([{cmd:'Get', keys:[k.coin, k.gem]}]);
  }

  // ── Traps ─────────────────────────────────────────────────────────────────
  // Lawn Mower Trap: sets off every mower on the field at once. They roll out
  // and are spent, leaving the lanes with no last line of defence.
  // launch() does all the bookkeeping itself -- clears inLane.mower, calls
  // LevelPlay.onMowerLose, plays the Trans animation and the sound -- so it is
  // the whole implementation. Note this also mows down whatever zombies are
  // already on screen, so firing the trap during a heavy wave can help the
  // player in the short term while still costing them the mowers.
  const LAWN_MOWER_TRAP = 'Lawn Mower Trap';

  function applyLawnMowerTrap(){
    const Square = window._AP_Square;
    // Square.getLane() dereferences Square.component, so bail out when no
    // level is running rather than throwing.
    if(!Square || typeof Square.getLane !== 'function' || !Square.component) return false;
    let fired = 0;
    for(let i = 0; i < 5; i++){
      let lane;
      try { lane = Square.getLane(i); } catch(e) { continue; }
      // A mower that has already been set off is no longer on its lane, so
      // only idle ones are picked up here.
      const mower = lane && lane.mower;
      if(!mower || typeof mower.launch !== 'function') continue;
      try { mower.launch(); fired++; } catch(e) { /* try the rest */ }
    }
    return fired > 0;
  }

  // ── Shopsanity ────────────────────────────────────────────────────────────
  // Called (via window._AP_onShopPurchase) from the StoreCommodity hook.
  window._AP_onShopPurchase = function(commodityName){
    // location_name_to_id always carries the shop entries, so their presence
    // proves nothing -- slot_data is what says this slot actually has them.
    if(!st.shopsanity) return;
    fireCheck('Shop: ' + commodityName);
  };

  // ── Random Plant Costume ──────────────────────────────────────────────────
  // A cosmetic filler. Each one grants a costume the player does not own yet,
  // for a plant they DO own -- a costume for a plant Archipelago has not sent
  // is not something anyone can look at.
  //
  // The roll is stored, not recomputed. rebuildAPSave() rewrites plantProps
  // from scratch every poll, so a costume that only existed in the game's save
  // would be wiped within two seconds; st.costumes is the record and the
  // rebuild restores from it.
  const RANDOM_COSTUME = 'Random Plant Costume';

  const COSTUME_TRAP = 'Costume Shuffle Trap';

  function ownedCostumes(pid){
    return (st.costumes || {})[pid] || [];
  }

  // Which costume a plant is actually wearing. Separate from what it owns so
  // the shuffle trap can move it around without ever costing the player a
  // costume -- st.costumes is the collection, st.wornCostume is the outfit.
  // Absent means "wear the most recent", which is what granting one does.
  function wornCostume(pid){
    const owned = ownedCostumes(pid);
    if(!owned.length) return -1;
    const worn = (st.wornCostume || {})[pid];
    // -1 is a real choice the trap can make: it means wearing none.
    if(worn === -1) return -1;
    if(worn === undefined || owned.indexOf(worn) < 0) return owned[owned.length-1];
    return worn;
  }

  // The Costume Shuffle Trap. Re-rolls what every dressed plant is wearing,
  // "none" included, so a collection the player has arranged gets scrambled.
  // Nothing is taken away: only st.wornCostume changes, so every costume can
  // be put back on from the almanac.
  function shuffleCostumes(){
    const owned = st.costumes || {};
    const pids = Object.keys(owned).filter(pid => owned[pid].length);
    if(!pids.length) return false;
    if(!st.wornCostume) st.wornCostume = {};
    let moved = 0;
    for(const pid of pids){
      // The choices are everything that plant owns, plus taking it off.
      const choices = owned[pid].concat([-1]);
      const before = wornCostume(pid);
      const pick = choices[Math.floor(Math.random() * choices.length)];
      st.wornCostume[pid] = pick;
      if(pick !== before) moved++;
    }
    svSt();
    toast('🎭 Costume Shuffle — ' + moved + ' plant' + (moved===1?'':'s') + ' redressed', '#f66');
    return true;
  }

  // Returns true if it managed to grant one.
  function grantRandomCostume(){
    const granted = window._AP_grantedPlantIds || new Set();
    const options = [];
    for(const pid of granted){
      const total = PLANT_COSTUMES[pid] || 0;
      if(!total) continue;
      const have = ownedCostumes(pid);
      for(let i = 0; i < total; i++) if(have.indexOf(i) < 0) options.push([pid, i]);
    }
    if(!options.length) return false;
    const [pid, idx] = options[Math.floor(Math.random() * options.length)];
    if(!st.costumes) st.costumes = {};
    if(!st.costumes[pid]) st.costumes[pid] = [];
    st.costumes[pid].push(idx);
    svSt();
    const cn = ID_TO_CN[pid];
    toast('👕 Costume for ' + (cn || ('plant ' + pid)), '#f0abfc');
    return true;
  }

  // Costumes received before the player owned any plant -- or before any plant
  // still had an unworn costume -- are banked rather than dropped, and retried
  // on the poll. Without this, a costume that arrived early would simply
  // vanish, which is the same bug the trap queue exists to avoid.
  function applyPendingCostumes(){
    let pending = st.pendingCostumes || 0;
    if(pending <= 0) return;
    let granted = 0;
    while(pending > 0 && grantRandomCostume()){ pending--; granted++; }
    if(granted){
      st.pendingCostumes = pending;
      svSt();
    }
  }

  // Whether the store should still be offering a commodity.
  //
  // The game hides a store card by asking whether the thing is already owned
  // -- getPlantProgressByID(id).progress > 0 for a plant, and
  // getUpgradeProgressByID(name).progress > 0 for an upgrade -- and destroying
  // the card node if so. Under AP that answer is permanently no: the plant
  // guard blocks unlockPlant(), the upgrade guard blocks unlockUpgrade() when
  // the seed shuffles upgrades, and rebuildAPSave() resets both every poll.
  // The card therefore never went away, so a purchase could be repeated for
  // as long as the player had gems -- spending them on a location that was
  // already checked and an item that was never going to be granted here.
  //
  // The check is the real record of the purchase, so that is what this reads.
  window._AP_isShopCommodityChecked = function(commodityName){
    if(!st.shopsanity) return false;
    return isChecked('Shop: ' + commodityName);
  };

  function applyPendingTraps(){
    let pending = st.pendingMowerTraps || 0;
    if(pending <= 0) return;
    // Every queued trap collapses into one activation -- once the mowers have
    // gone off there is nothing left for the extras to set off, so they are
    // consumed rather than held for the next level.
    if(applyLawnMowerTrap()){
      st.pendingMowerTraps = 0;
      svSt();
      toast('🚜 Lawn Mower Trap — mowers activated!', '#f66');
    }
  }

  // ── Location polling (every 2s) ───────────────────────────────────────────
  // Modern Day has no key -- it unlocks purely on the world-goal count.
  // (Older seeds may still hand out a "Modern Day Key" item; it is simply
  // ignored rather than being required, so those seeds stay completable.)
  // The location whose check ends the run, chosen by the modern_day_victory
  // option. Falls back to the Zomboss for seeds generated before that option
  // existed, which is what used to be hardcoded in fireCheck().
  function victoryLoc(){ return st.victoryLoc || 'modern_zomboss_01_egypt'; }

  function canAccessModernDay(){
    const goalLocs  = st.goalLocs || [];
    const worldsReq = st.worldsReq || 7;
    if(!goalLocs.length) return false; // slot_data not in yet; don't open early
    const completed = goalLocs.filter(l=>isChecked(l)).length;
    return completed >= worldsReq;
  }

  function pollChecks(){
    // Detect newly-finished levels BEFORE rebuildAPSave() runs: isFinished()
    // for tutorial levels reads cp.forceLevel, which rebuildAPSave() step 5
    // unconditionally overwrites from st.checked -- if rebuild ran first, it
    // would stomp the game's live forceLevel back to the last-known tutorial
    // step before isFinished() ever saw the advanced value, permanently
    // deadlocking tutorial check detection (and regressing forceLevel/
    // levelProps for whichever tutorial step the player is actually on).
    if(conn && sessionActive){
      for(const[loc,levelId] of Object.entries(LOC_LEVELS)){
        // Checked locations are skipped, with one exception: the victory
        // location while the goal is still unsent this session, which is how
        // fireCheck() gets the chance to retry the StatusUpdate. goalSent is
        // tested first so the common case stays a boolean, not a string
        // compare against all 761 entries every tick.
        if(isChecked(loc) && (goalSent || loc!==victoryLoc())) continue;
        if(isFinished(levelId)) fireCheck(loc);
      }
    }
    rebuildAPSave();
    // Fires once a level is actually running, for traps banked while the
    // player was on the world map or reconnecting.
    applyPendingTraps();
    // Costumes banked before the player owned a plant to put one on.
    applyPendingCostumes();
  }

  function fireCheck(loc){
    // Modern Day accessibility gates everything below, the goal included: a
    // Modern Day check fired before the world is legitimately unlocked is not
    // one the run has earned.
    if(MODERN_DAY_LOCS.has(loc) && !canAccessModernDay()) return;
    // The goal is settled BEFORE the already-checked bail-out. StatusUpdate is
    // independent of the location send, and a victory location can reach
    // st.checked without the server ever hearing the goal -- the reconnect
    // merge in mergeServerChecks() pushes names straight into st.checked, and
    // a StatusUpdate can be lost to a socket that drops between the two sends.
    // With the isChecked() test first, that state was terminal: fireCheck()
    // returned immediately every time, and pollChecks() skips checked
    // locations, so nothing ever retried the goal.
    if(loc===victoryLoc() && !goalSent && conn){
      send([{cmd:'StatusUpdate',status:30}]);
      goalSent = true;
    }
    if(isChecked(loc)) return;
    st.checked.push(loc);svSt();
    const id=locIds[loc];
    if(id&&conn) send([{cmd:'LocationChecks',locations:[id]}]);
  }

  // ── UI ────────────────────────────────────────────────────────────────────
  let statusEl=null, logEl=null, panel=null, logs=[];

  function buildUI(){
    const s=document.createElement('style');
    s.textContent=`
      #ap-btn{position:fixed;top:8px;left:8px;z-index:99999;background:#111827;
        color:#6ee7b7;border:1px solid #059669;border-radius:6px;padding:4px 12px;
        font:bold 13px monospace;cursor:pointer;user-select:none;letter-spacing:.05em}
      #ap-btn:hover{background:#1f2937}
      #ap-panel{position:fixed;top:38px;left:8px;z-index:99999;background:#0f172a;
        color:#e2e8f0;border:1px solid #059669;border-radius:10px;padding:16px;
        font:12px monospace;width:280px;display:none;box-shadow:0 8px 32px #000c}
      #ap-panel label{display:block;margin-top:8px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.08em}
      #ap-panel input{width:100%;box-sizing:border-box;background:#1e293b;color:#e2e8f0;
        border:1px solid #334155;border-radius:5px;padding:4px 8px;font:12px monospace;
        margin-top:3px;outline:none}
      #ap-panel input:focus{border-color:#059669}
      #ap-panel button{background:#065f46;color:#6ee7b7;border:1px solid #059669;
        border-radius:5px;padding:5px 14px;margin-top:10px;cursor:pointer;font:12px monospace}
      #ap-panel button:hover{background:#047857}
      #ap-disc{background:#1c1917!important;color:#f87171!important;border-color:#dc2626!important;margin-left:6px}
      #ap-disc:hover{background:#292524!important}
      #ap-reset{background:#1e1b4b!important;color:#a5b4fc!important;border-color:#6366f1!important;margin-left:6px}
      #ap-reset:hover{background:#312e81!important}
      #ap-status{margin-top:10px;font-weight:bold;font-size:12px}
      #ap-log{margin-top:8px;max-height:100px;overflow-y:auto;background:#020617;
        border-radius:5px;padding:6px;font-size:10px;color:#64748b;line-height:1.5}
      #ap-toast{position:fixed;bottom:72px;left:50%;transform:translateX(-50%);
        z-index:99999;background:#0f172a;color:#e2e8f0;border:1px solid #059669;
        border-radius:8px;padding:8px 20px;font:13px monospace;
        opacity:0;transition:opacity .3s;pointer-events:none;white-space:nowrap}
    `;
    document.head.appendChild(s);

    const btn=document.createElement('div');
    btn.id='ap-btn';btn.textContent='AP';
    btn.onclick=()=>{panel.style.display=panel.style.display==='none'?'block':'none';};
    document.body.appendChild(btn);

    panel=document.createElement('div');panel.id='ap-panel';
    panel.innerHTML=`<div style="font-weight:bold;font-size:13px;color:#6ee7b7;margin-bottom:4px">🏝 Archipelago</div>
      <label>Server<br><input id=ap-srv placeholder="localhost:38281"></label>
      <label>Slot Name<br><input id=ap-slt placeholder="Player"></label>
      <label>Password<br><input id=ap-pwd type=password placeholder="(optional)"></label>
      <button id=ap-go>Connect</button><button id=ap-disc>Disconnect</button><button id=ap-reset>Reset</button>
      <div id=ap-status style="color:#64748b">Not connected</div>
      <div id=ap-log></div>`;
    document.body.appendChild(panel);

    statusEl=document.getElementById('ap-status');
    logEl=document.getElementById('ap-log');
    document.getElementById('ap-srv').value=cfg.server||'';
    document.getElementById('ap-slt').value=cfg.slot||'';
    document.getElementById('ap-pwd').value=cfg.password||'';

    document.getElementById('ap-go').onclick=()=>{
      cfg.server=document.getElementById('ap-srv').value.trim()||'localhost:38281';
      cfg.slot=document.getElementById('ap-slt').value.trim();
      cfg.password=document.getElementById('ap-pwd').value;
      svCfg();rdelay=5000;connect();
    };
    document.getElementById('ap-disc').onclick=()=>{
      clearTimeout(rtimer);
      if(ws){ws.onclose=null;ws.close();ws=null;}
      conn=false;sessionActive=false;goalSent=false;setStatus('Disconnected','#f44');
    };
    document.getElementById('ap-reset').onclick=()=>{
      if(!confirm('Reset all AP progress for this slot? This clears checked locations, received items, and run state.')) return;
      st={checked:[],lastIdx:0,receivedKeys:[],receivedItems:[],upgradeCounts:{},costumes:{},wornCostume:{},pendingCostumes:0,runKey:''};
      // The victory location is no longer checked, so clearing goalSent lets
      // re-earning it send the goal again.
      goalSent=false;
      svSt();
      window._AP_grantedPlantIds=new Set();
      window._AP_grantedUpgrades=new Set();
      log('State reset.');toast('AP state cleared','#a5b4fc');
    };

    const t=document.createElement('div');t.id='ap-toast';
    document.body.appendChild(t);
  }

  function setStatus(msg,color){
    if(statusEl){statusEl.textContent=msg;statusEl.style.color=color||'#64748b';}
  }

  let toastTimer=null;
  function pushLog(msg){
    logs.unshift(msg);if(logs.length>40)logs.pop();
    if(logEl)logEl.innerHTML=logs.map(m=>`<div>${m}</div>`).join('');
  }

  // Panel-only message, no transient toast. This was being called from
  // findOrCreateAPSlot(), connect() and the reset button without ever having
  // been defined, so each of those threw a ReferenceError instead: the slot
  // creation path never reached its reload, and the catch in
  // findOrCreateAPSlot() threw again before it could return -1.
  function log(msg){ pushLog(msg); }

  function toast(msg,color){
    pushLog(msg);
    const el=document.getElementById('ap-toast');if(!el)return;
    el.textContent=msg;el.style.color=color||'#e2e8f0';el.style.opacity='1';
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.style.opacity='0',3500);
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  // ── Speed control ────────────────────────────────────────────────────────
  let _speed = 1.0;
  const _SPEED_STEP = 0.25, _SPEED_MIN = 0.5, _SPEED_MAX = 8.0;

  // The engine is loaded as a SystemJS module, not a global: index.html
  // bootstraps with System.import('./index.js') and nothing ever assigns
  // window.cc or globalThis.cc. A bare `cc` reference is therefore always
  // undefined, which is why the old check fell through to its warning and
  // the speed never actually changed. Pull the module out of the registry
  // instead -- 'cc' is in the import map, and it is already loaded by the
  // time any key can be pressed.
  let _ccModule = null;
  function getCC() {
    if (_ccModule) return _ccModule;
    try {
      if (typeof System === 'undefined') return null;
      _ccModule = System.get(System.resolve('cc')) || null;
    } catch (e) { _ccModule = null; }
    return _ccModule;
  }

  function setSpeed(s) {
    const clamped = Math.round(Math.min(_SPEED_MAX, Math.max(_SPEED_MIN, s)) * 100) / 100;
    const CC = getCC();
    if (!CC || !CC.director) { toast('⚠️ engine not ready', '#f88'); return; }
    try {
      CC.director.getScheduler().setTimeScale(clamped);
    } catch (e) { toast(`⚠️ ${e.message}`, '#f88'); return; }
    // Only commit the new speed once it actually took, so the displayed
    // value can't drift away from the engine's.
    _speed = clamped;
    toast(`⏩ ${_speed}x`, '#aaf');
  }

  function init(){
    lsCfg();lsSt();
    // Re-sync granted set (catches any items received while game was closed)
    syncGrantedPlants();
    buildUI();
    setInterval(pollChecks,2000);
    // Never auto-connect — user must click Connect manually each session

    // Use window capture phase so this fires before the game's own keydown
    // handlers, even if the game canvas calls stopPropagation().
    window.addEventListener('keydown', function(e) {
      if (e.target.tagName === 'INPUT') return;
      if (e.key === ']') setSpeed(_speed + _SPEED_STEP);
      else if (e.key === '[') setSpeed(_speed - _SPEED_STEP);
    }, true);
  }

  document.readyState==='loading'
    ? document.addEventListener('DOMContentLoaded',init)
    : setTimeout(init,100);
})();
""".strip().replace("__AP_LOGO_PNG__", AP_LOGO_PNG)


# ── Build steps ───────────────────────────────────────────────────────────────

STEPS = [
    ("Checking requirements",        "check_requirements"),
    ("Cloning Electron wrapper",      "clone_electron"),
    ("Cloning game source",           "clone_game"),
    ("Patching tmpPatch.js",          "patch_tmpatch"),
    ("Installing Node dependencies",  "npm_install"),
    ("Building executable",           "npm_build"),
    ("Copying output",                "copy_output"),
]


def run_cmd(cmd, cwd, log):
    """Run a shell command, streaming output to log callback. Returns returncode."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    for line in proc.stdout:
        log(line.rstrip())
    proc.wait()
    return proc.returncode


def find_tool(name):
    return shutil.which(name)


def git_capture(args, cwd):
    """Run a git command and return (returncode, stripped stdout).

    Quiet by design -- this is for reading repository state during an update
    check, where streaming every line into the build log would bury the answer.
    """
    try:
        proc = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def _remote_head(repo_dir):
    """Resolve this repo's upstream commit, whatever its default branch is.

    The clones here are --depth=1, so origin/HEAD is often not set and the
    branch is not always master -- PVZGE-Electron and pvzge_web do not agree.
    Ask for each candidate in turn rather than assuming one.
    """
    for ref in ("origin/HEAD", "origin/master", "origin/main"):
        rc, out = git_capture(["rev-parse", ref], repo_dir)
        if rc == 0 and out:
            return out
    return None


def check_for_updates(build_dir, log):
    """Report what in an existing build is out of date. Runs in a thread.

    Returns (stale, summary_lines). `stale` is True when a rebuild would
    actually change something, so the caller can offer the update rather than
    making the user guess.

    Reads only: fetches refs and compares hashes, never touches the working
    tree. A fetch is cheap on an existing shallow clone, unlike the ~300MB
    first clone.
    """
    electron_dir  = os.path.join(build_dir, "PVZGE-Electron")
    pvzge_web_dir = os.path.join(electron_dir, "pvzge_web")
    docs_dir      = os.path.join(pvzge_web_dir, "docs")
    lines = []
    stale = False

    if not find_tool("git"):
        return False, ["git is not installed, so no update check is possible."]

    if not os.path.isdir(docs_dir):
        return True, [
            "No build found in this folder yet.",
            "Run a full build first -- there is nothing to update.",
        ]

    def check_repo(label, repo_dir, fetch_args):
        nonlocal stale
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            lines.append(f"{label}: not a git checkout, cannot check")
            return
        log(f"  Fetching {label}...")
        rc, out = git_capture(["fetch"] + fetch_args, repo_dir)
        if rc != 0:
            lines.append(f"{label}: could not reach GitHub ({out.splitlines()[-1] if out else 'no output'})")
            return
        _, local = git_capture(["rev-parse", "HEAD"], repo_dir)
        remote = _remote_head(repo_dir)
        if remote is None:
            lines.append(f"{label}: no upstream ref to compare against")
            return
        if local == remote:
            _, subject = git_capture(["log", "--oneline", "-1"], repo_dir)
            lines.append(f"{label}: up to date  ({subject})")
        else:
            stale = True
            rc, count = git_capture(["rev-list", "--count", f"HEAD..{remote}"], repo_dir)
            n = count if rc == 0 and count.isdigit() else "new"
            lines.append(f"{label}: {n} commit(s) behind upstream")

    check_repo("Electron wrapper", electron_dir, ["origin"])
    check_repo("Game source", pvzge_web_dir, ["origin", "master", "--depth=1"])

    # The Archipelago client. This is the one that changes most often and the
    # one a git fetch says nothing about -- it ships inside this apworld, so it
    # moves when the apworld is updated, not when either repo does.
    tmppatch_path = os.path.join(docs_dir, "tmpPatch.js")
    if not os.path.isfile(tmppatch_path):
        stale = True
        lines.append("AP client: not injected yet")
    else:
        with open(tmppatch_path, "r", encoding="utf-8") as f:
            on_disk = f.read()
        if on_disk == TMPPATCH_CONTENT:
            lines.append(f"AP client: up to date  ({len(TMPPATCH_CONTENT):,} bytes)")
        else:
            stale = True
            delta = len(TMPPATCH_CONTENT) - len(on_disk)
            lines.append(f"AP client: differs from this apworld "
                         f"({delta:+,} bytes)")

    # Even with everything above current, the packaged app can predate the
    # patch: electron-builder bakes the client into the executable, so editing
    # tmpPatch.js alone changes nothing the player runs.
    exe = None
    for name in ("PvZ Gardendless AP.exe", "PvZ Gardendless AP.dmg",
                 "PvZ Gardendless AP.AppImage"):
        p = os.path.join(build_dir, name)
        if os.path.isfile(p):
            exe = p
            break
    if exe is None:
        stale = True
        lines.append("Packaged app: not built yet")
    elif os.path.isfile(tmppatch_path) and \
            os.path.getmtime(exe) < os.path.getmtime(tmppatch_path):
        stale = True
        lines.append("Packaged app: older than the injected client, "
                     "so it does not contain it")
    else:
        lines.append(f"Packaged app: {os.path.basename(exe)}")

    return stale, lines


def build(build_dir, log, done_cb, error_cb, fast=False):
    """Full build sequence. Runs in a thread.

    fast=True is the update path: it requires an existing checkout, still pulls
    both repos (incremental on a shallow clone, so seconds rather than the
    ~300MB first fetch), and skips `npm install` when node_modules is already
    there. electron-builder still runs -- the client is baked into the
    executable, so there is no way to change what the player runs without
    repackaging.
    """

    electron_dir = os.path.join(build_dir, "PVZGE-Electron")
    docs_dir     = os.path.join(electron_dir, "pvzge_web", "docs")
    release_dir  = os.path.join(electron_dir, "release")

    def step(msg):
        log(f"\n{'─'*50}")
        log(f"  {msg}")
        log(f"{'─'*50}")

    if fast and not os.path.isdir(docs_dir):
        error_cb(
            "Update needs an existing build, and none was found at:\n"
            f"{docs_dir}\n\nRun a full build first.")
        return

    # ── 1. Check requirements ─────────────────────────────────────────────────
    step("Checking requirements")
    missing = []
    for tool in ("git", "node", "npm"):
        if not find_tool(tool):
            missing.append(tool)
    if missing:
        error_cb(
            f"Missing required tools: {', '.join(missing)}\n\n"
            "Please install:\n"
            + ("  • Git:    https://git-scm.com/download/win\n" if "git" in missing else "")
            + ("  • Node.js: https://nodejs.org (LTS version)\n" if "node" in missing else "")
            + "If this message continues to appear, run powershell as administrator and run\n"
            + "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser\n"
            + "Then run archipelago as an administrator."
        )
        return

    node_ver = subprocess.check_output("node --version", shell=True, text=True).strip()
    npm_ver  = subprocess.check_output("npm --version",  shell=True, text=True).strip()
    git_ver  = subprocess.check_output("git --version",  shell=True, text=True).strip()
    log(f"  node {node_ver}  |  npm {npm_ver}  |  {git_ver}")

    # ── 2. Clone Electron wrapper ─────────────────────────────────────────────
    step("Cloning Electron wrapper")
    os.makedirs(build_dir, exist_ok=True)

    if os.path.isdir(electron_dir):
        log("  Already exists — pulling latest...")
        rc = run_cmd("git pull", electron_dir, log)
    else:
        rc = run_cmd(
            "git clone --depth=1 https://github.com/Twig6943/PVZGE-Electron.git",
            build_dir, log
        )
    if rc != 0:
        error_cb("Failed to clone Electron wrapper. Check your internet connection.")
        return

    # ── 3. Clone game source ──────────────────────────────────────────────────
    # Always clone pvzge_web directly from master — never use the submodule pin
    # in the Electron repo, which may point to an older version.
    step("Cloning game source (pvzge_web master) — this may take a few minutes (~300MB)")
    pvzge_web_dir = os.path.join(electron_dir, "pvzge_web")

    if os.path.isdir(os.path.join(pvzge_web_dir, "docs")):
        log("  Already exists — fetching latest from master...")
        rc = run_cmd("git fetch origin master --depth=1", pvzge_web_dir, log)
        if rc == 0:
            rc = run_cmd("git reset --hard origin/master", pvzge_web_dir, log)
        if rc != 0:
            log("  Warning: could not update pvzge_web, using existing copy")
            rc = 0  # non-fatal, proceed with what we have
    else:
        # Detach any existing submodule tracking and clone fresh
        os.makedirs(pvzge_web_dir, exist_ok=True)
        rc = run_cmd(
            "git clone --depth=1 --branch master "
            "https://github.com/Gzh0821/pvzge_web.git .",
            pvzge_web_dir, log
        )
    if rc != 0:
        error_cb("Failed to clone game source. Check your internet connection.")
        return

    if not os.path.isdir(docs_dir):
        error_cb(f"Expected docs/ folder not found at:\n{docs_dir}\n\nClone may be incomplete.")
        return

    # Log the actual game version we got
    ver_result = run_cmd("git log --oneline -1", pvzge_web_dir, log)

    # ── 4. Patch tmpPatch.js ──────────────────────────────────────────────────
    step("Patching tmpPatch.js with Archipelago client")
    tmppatch_path = os.path.join(docs_dir, "tmpPatch.js")

    bak_path = tmppatch_path + ".original"
    if not os.path.exists(bak_path) and os.path.exists(tmppatch_path):
        shutil.copy2(tmppatch_path, bak_path)
        log(f"  Backed up original to tmpPatch.js.original")

    with open(tmppatch_path, "w", encoding="utf-8") as f:
        f.write(TMPPATCH_CONTENT)
    log(f"  Written: {tmppatch_path}")
    log(f"  Size: {len(TMPPATCH_CONTENT):,} bytes")

    # Patch main.js to enable devtools (F12) so the AP overlay errors are visible
    main_js_path = os.path.join(electron_dir, "main.js")
    if os.path.isfile(main_js_path):
        with open(main_js_path, "r", encoding="utf-8") as f:
            main_js = f.read()
        main_js = main_js.replace("devTools: false", "devTools: true")
        # Use before-input-event instead of globalShortcut for F12.
        # globalShortcut steals keys from the game (breaks F10 GP-Next menu etc).
        # before-input-event fires in the renderer process so unhandled keys
        # still reach the game's own keydown listeners.
        f12_hook = (
            "  win.webContents.on('before-input-event', (event, input) => {\n"
            "    if (input.type === 'keyDown' && input.key === 'F12') {\n"
            "      win.webContents.toggleDevTools();\n"
            "      event.preventDefault();\n"
            "    }\n"
            "  });\n"
        )
        if "before-input-event" not in main_js:
            # Inject after win.removeMenu() line
            main_js = main_js.replace(
                "  win.removeMenu(); // hides the top menu bar",
                "  win.removeMenu(); // hides the top menu bar\n" + f12_hook
            )
        with open(main_js_path, "w", encoding="utf-8") as f:
            f.write(main_js)
        log("  Enabled F12 devtools in main.js")


    # ── 5. npm install ────────────────────────────────────────────────────────
    # Skipped on the update path when node_modules is already populated. This
    # is the one step an update genuinely saves: the clones above are
    # incremental once they exist, and electron-builder below is unavoidable.
    node_modules = os.path.join(electron_dir, "node_modules")
    if fast and os.path.isdir(node_modules) and os.listdir(node_modules):
        step("Node.js dependencies already installed — skipping")
    else:
        step("Installing Node.js dependencies (electron, electron-builder)")
        log("  This downloads ~200MB of packages the first time...")
        rc = run_cmd("npm install", electron_dir, log)
        if rc != 0:
            error_cb("npm install failed. See log above for details.")
            return

    # ── 6. Build ──────────────────────────────────────────────────────────────
    import platform as _platform
    plat = _platform.system()
    if plat == "Windows":
        build_cmd = "npm run build:win -- --publish=never"
        output_exts = [".exe"]
        output_name = "PvZ Gardendless AP.exe"
    elif plat == "Darwin":
        build_cmd = "npm run build:mac -- --publish=never"
        output_exts = [".dmg", ".app"]
        output_name = "PvZ Gardendless AP.dmg"
    else:  # Linux
        build_cmd = "npm run build:linux -- --publish=never"
        output_exts = [".AppImage", ".appimage"]
        output_name = "PvZ Gardendless AP.AppImage"

    step(f"Building {plat} application (this takes 2-5 minutes)")
    rc = run_cmd(build_cmd, electron_dir, log)
    if rc != 0:
        error_cb("Build failed. See log above for details.")
        return

    # ── 7. Find and copy output ───────────────────────────────────────────────
    step("Locating output file")
    built_path = None
    for root, dirs, files in os.walk(release_dir):
        for f in files:
            if any(f.endswith(ext) for ext in output_exts):
                built_path = os.path.join(root, f)
                break
        if built_path:
            break

    if not built_path:
        error_cb(f"Build succeeded but no output found in:\n{release_dir}\n\nExpected: {output_exts}")
        return

    final_path = os.path.join(build_dir, output_name)
    shutil.copy2(built_path, final_path)
    # Make executable on Linux/Mac
    if plat != "Windows":
        os.chmod(final_path, 0o755)
    log(f"\n  Output: {final_path}")
    log(f"  Size:   {os.path.getsize(final_path)/1024/1024:.0f} MB")

    done_cb(final_path)


# ── GUI ───────────────────────────────────────────────────────────────────────

class BuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PvZ2 Gardendless — Archipelago Builder")
        self.root.resizable(True, True)
        self.root.minsize(640, 480)
        self._configure_style()
        self._build_ui()
        self.q = queue.Queue()
        self.root.after(100, self._poll_queue)

    def _configure_style(self):
        self.root.configure(bg="#0f172a")

    def _build_ui(self):
        BG   = "#0f172a"
        BG2  = "#1e293b"
        ACC  = "#059669"
        ACCL = "#6ee7b7"
        TEXT = "#e2e8f0"
        MUTE = "#64748b"
        FONT = ("Consolas", 10)

        # Title
        title_frame = tk.Frame(self.root, bg=BG, pady=16)
        title_frame.pack(fill="x", padx=24)
        tk.Label(title_frame, text="🌻  PvZ2 Gardendless", font=("Consolas", 18, "bold"),
                 bg=BG, fg=ACCL).pack(anchor="w")
        tk.Label(title_frame, text="Archipelago Mod Builder",
                 font=("Consolas", 11), bg=BG, fg=MUTE).pack(anchor="w")

        # Divider
        tk.Frame(self.root, bg=ACC, height=1).pack(fill="x", padx=24)

        # Build folder picker
        dir_frame = tk.Frame(self.root, bg=BG, pady=12)
        dir_frame.pack(fill="x", padx=24)
        tk.Label(dir_frame, text="BUILD FOLDER", font=("Consolas", 9, "bold"),
                 bg=BG, fg=MUTE).pack(anchor="w")

        row = tk.Frame(dir_frame, bg=BG)
        row.pack(fill="x", pady=(4, 0))

        # Try to load saved build directory from host.yaml
        saved_dir = ""
        try:
            from settings import get_settings
            saved_dir = str(get_settings().pvz2gardendless.build_directory or "")
        except Exception:
            pass
        default_dir = saved_dir if saved_dir else os.path.normpath(os.path.expanduser("~/pvzge_ap_build"))
        self.dir_var = tk.StringVar(value=default_dir)
        self.dir_entry = tk.Entry(row, textvariable=self.dir_var, font=FONT,
                                  bg=BG2, fg=TEXT, insertbackground=TEXT,
                                  relief="flat", bd=6)
        self.dir_entry.pack(side="left", fill="x", expand=True)

        tk.Button(row, text="Browse…", font=FONT, bg=BG2, fg=ACCL,
                  activebackground="#334155", activeforeground=ACCL,
                  relief="flat", bd=0, padx=10, pady=4,
                  cursor="hand2",
                  command=self._browse).pack(side="left", padx=(6, 0))

        # Info box
        info = tk.Frame(self.root, bg=BG2, padx=12, pady=10)
        info.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(info,
                 text="START BUILD does everything:\n"
                      "  1. Clone the Electron wrapper from GitHub (~5 MB)\n"
                      "  2. Clone the game source from GitHub (~300 MB)\n"
                      "  3. Inject the Archipelago client into the game\n"
                      "  4. Build the game application for your platform via npm\n\n"
                      "CHECK FOR UPDATES reads what you already have and says\n"
                      "whether a rebuild would change anything. UPDATE then does\n"
                      "steps 3 and 4 only, reusing the downloads.\n\n"
                      "Requirements: Git + Node.js (LTS) must be installed.",
                 font=("Consolas", 9), bg=BG2, fg=MUTE, justify="left"
                 ).pack(anchor="w")

        # Actions. Check is the cheap read-only path and sits first, so the
        # habit is "check, then act" rather than "rebuild and hope".
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(pady=(0, 12))

        self.check_btn = tk.Button(
            btn_row, text="⟳  CHECK FOR UPDATES", font=("Consolas", 11),
            bg=BG2, fg=ACCL, activebackground="#334155", activeforeground=ACCL,
            relief="flat", bd=0, padx=16, pady=10, cursor="hand2",
            command=self._start_check
        )
        self.check_btn.pack(side="left", padx=(0, 8))

        # Disabled until a check finds something to do -- offering an update
        # before knowing one is needed is what the check exists to replace.
        self.update_btn = tk.Button(
            btn_row, text="⬆  UPDATE", font=("Consolas", 11, "bold"),
            bg=BG2, fg=MUTE, activebackground="#334155", activeforeground=ACCL,
            relief="flat", bd=0, padx=16, pady=10, cursor="hand2",
            state="disabled", command=self._start_update
        )
        self.update_btn.pack(side="left", padx=(0, 8))

        self.build_btn = tk.Button(
            btn_row, text="▶  START BUILD", font=("Consolas", 12, "bold"),
            bg=ACC, fg="#022c22", activebackground="#047857", activeforeground="#022c22",
            relief="flat", bd=0, padx=20, pady=10, cursor="hand2",
            command=self._start_build
        )
        self.build_btn.pack(side="left")

        # Log area
        log_frame = tk.Frame(self.root, bg=BG, padx=24, pady=0)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="BUILD LOG", font=("Consolas", 9, "bold"),
                 bg=BG, fg=MUTE).pack(anchor="w")

        log_inner = tk.Frame(log_frame, bg="#020617")
        log_inner.pack(fill="both", expand=True, pady=(4, 16))
        scrollbar = tk.Scrollbar(log_inner)
        scrollbar.pack(side="right", fill="y")
        self.log_area = tk.Text(
            log_inner, font=("Consolas", 9), bg="#020617", fg="#94a3b8",
            insertbackground=TEXT, relief="flat", bd=4,
            state="disabled", wrap="word", yscrollcommand=scrollbar.set
        )
        self.log_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_area.yview)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.root, textvariable=self.status_var, font=("Consolas", 9),
                 bg=BG2, fg=MUTE, anchor="w", padx=8, pady=4
                 ).pack(fill="x", side="bottom")

    def _browse(self):
        d = filedialog.askdirectory(title="Choose build folder",
                                    initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(os.path.normpath(d))

    def _log(self, msg):
        self.q.put(("log", msg))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "log":
                    self.log_area.configure(state="normal")
                    self.log_area.insert("end", data + "\n")
                    self.log_area.see("end")
                    self.log_area.configure(state="disabled")
                elif kind == "status":
                    self.status_var.set(data)
                elif kind == "done":
                    self._on_done(data)
                elif kind == "check_done":
                    self._on_check_done(*data)
                elif kind == "error":
                    self._on_error(data)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _resolve_dir(self):
        """Validate the chosen folder and remember it. None means don't start."""
        build_dir = os.path.normpath(self.dir_var.get().strip())
        if not build_dir or build_dir == ".":
            self._on_error("Please choose a build folder first.")
            return None
        # Persist chosen directory to host.yaml
        try:
            from settings import get_settings
            get_settings().pvz2gardendless.build_directory = build_dir
            get_settings().save()
        except Exception:
            pass  # non-fatal if settings unavailable
        return build_dir

    def _clear_log(self):
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")

    def _busy(self, busy):
        state = "disabled" if busy else "normal"
        self.build_btn.configure(state=state)
        self.check_btn.configure(state=state)
        # The update button follows the last check rather than coming back on
        # its own: after a build there is nothing left to update.
        if busy:
            self.update_btn.configure(state="disabled")

    def _start_check(self):
        build_dir = self._resolve_dir()
        if build_dir is None:
            return
        self._busy(True)
        self.check_btn.configure(text="Checking…")
        self._clear_log()
        self.status_var.set("Checking for updates…")

        def _thread():
            log = lambda m: self.q.put(("log", m))
            log(f"{'─'*50}")
            log("  Checking for updates")
            log(f"{'─'*50}")
            try:
                stale, lines = check_for_updates(build_dir, log)
            except Exception as e:
                # A read-only check must never be able to take the app down.
                self.q.put(("error", f"Update check failed: {e}"))
                return
            self.q.put(("check_done", (stale, lines)))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_check_done(self, stale, lines):
        self._busy(False)
        self.check_btn.configure(text="⟳  CHECK FOR UPDATES")
        self._log("")
        for line in lines:
            self._log(f"  {line}")
        self._log("")
        if stale:
            self.update_btn.configure(state="normal", fg="#6ee7b7")
            self.status_var.set("Updates available — press UPDATE.")
            self._log("  Something is out of date. UPDATE re-injects the client")
            self._log("  and repackages the app, reusing what is already")
            self._log("  downloaded. It still runs electron-builder (2-5 min),")
            self._log("  because the client is baked into the executable.")
        else:
            self.update_btn.configure(state="disabled", fg="#64748b")
            self.status_var.set("✓ Everything is up to date.")
            self._log("  Everything is up to date. No rebuild needed.")

    def _start_build(self, fast=False):
        build_dir = self._resolve_dir()
        if build_dir is None:
            return

        self._busy(True)
        self.build_btn.configure(text="Updating…" if fast else "Building…")
        self._clear_log()
        self.status_var.set("Updating…" if fast else "Building…")

        def _thread():
            build(
                build_dir,
                log=lambda m: self.q.put(("log", m)),
                done_cb=lambda exe: self.q.put(("done", exe)),
                error_cb=lambda err: self.q.put(("error", err)),
                fast=fast,
            )

        threading.Thread(target=_thread, daemon=True).start()

    def _start_update(self):
        self._start_build(fast=True)

    def _on_done(self, exe_path):
        self._busy(False)
        self.build_btn.configure(text="▶  BUILD AGAIN")
        self.update_btn.configure(state="disabled", fg="#64748b")
        self.status_var.set("✓ Build complete!")
        self._log(f"\n{'='*50}")
        self._log("  BUILD COMPLETE!")
        self._log(f"{'='*50}")
        self._log(f"  Your modded game is at:")
        self._log(f"  {exe_path}")
        self._log("")
        self._log("  Launch it, then click the AP button in the")
        self._log("  top-left corner to connect to your server.")

        # Ask to open folder
        folder = os.path.dirname(exe_path)
        import tkinter.messagebox as mb
        if mb.askyesno("Build Complete",
                        f"Build successful!\n\nSaved to:\n{exe_path}\n\nOpen folder?"):
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _on_error(self, msg):
        self._busy(False)
        self.build_btn.configure(text="▶  START BUILD")
        self.check_btn.configure(text="⟳  CHECK FOR UPDATES")
        self.status_var.set("✗ Build failed.")
        self._log(f"\n{'!'*50}")
        self._log("  ERROR")
        self._log(f"{'!'*50}")
        for line in msg.splitlines():
            self._log(f"  {line}")
        import tkinter.messagebox as mb
        mb.showerror("Build Failed", msg)


def main():
    root = tk.Tk()
    app = BuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
