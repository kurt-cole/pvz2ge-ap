// VERBATIM COPIES from build_pvzge_ap.py -- drift_test.py asserts these still
// match the real client. If it fails, re-copy from there; never relax it.
//
// Harness stubs for the module scope the real functions close over.
const window = {};
const st = {};
let _currencyRestoreDone = false;
let _lastCurrencyComp = {};
let saved = 0;
function svSt() { saved++; }

const CURRENCY_FIELDS = [
  { field:'coin', granted:'coinGranted', applied:'coinApplied',
    seen:'coinSeen',
    cls:function(){ return window._AP_CoinCount; }, add:'addCoinCount' },
  { field:'gem',  granted:'gemGranted',  applied:'gemApplied',
    seen:'gemSeen',
    cls:function(){ return window._AP_GemCount; },  add:'addGemCount' },
];

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

function clearWorldKeys(cp){
  if(!cp) return 0;
  const had = cp.worldkey || 0;
  const comp = window._AP_WorldKeyCount && window._AP_WorldKeyCount.component;
  if(comp && typeof comp.value === 'number'){
    if(comp.value !== 0){ try { comp.value = 0; } catch(e) { cp.worldkey = 0; } }
    else if(had) cp.worldkey = 0;
  } else if(had){
    cp.worldkey = 0;
  }
  return had;
}

function reset(state, players) {
  for (const k of Object.keys(st)) delete st[k];
  Object.assign(st, state);
  _currencyRestoreDone = false;
  _lastCurrencyComp = {};
  saved = 0;
  window._AP_AllPlayerProperties = players;
  window._AP_CoinCount = undefined;
  window._AP_GemCount = undefined;
  window._AP_WorldKeyCount = undefined;
}
function restoreDone(v) {
  if (v !== undefined) _currencyRestoreDone = v;
  return _currencyRestoreDone;
}

module.exports = {
  restoreLostCurrency, observeCurrency, currencyComponentChanged,
  applyCurrencyTraps, clearWorldKeys,
  syncCurrencyDisplay, CURRENCY_FIELDS,
  st, window, reset, restoreDone, savedCount: () => saved,
};
