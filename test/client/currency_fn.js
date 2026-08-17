// VERBATIM COPIES from build_pvzge_ap.py -- drift_test.py asserts these still
// match the real client. If it fails, re-copy from there; never relax it.
//
// Harness stubs for the module scope the real functions close over.
const window = {};
const st = {};
let _currencyRestoreDone = false;
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

function observeCurrency(){
  const APP = window._AP_AllPlayerProperties;
  const cp  = APP ? APP.currentPlayer : null;
  if(!cp) return;
  let dirty = false;
  for(const c of CURRENCY_FIELDS){
    const have = cp[c.field] || 0;
    if(st[c.seen] !== have){ st[c.seen] = have; dirty = true; }
  }
  if(dirty) svSt();
}

function reset(state, players) {
  for (const k of Object.keys(st)) delete st[k];
  Object.assign(st, state);
  _currencyRestoreDone = false;
  saved = 0;
  window._AP_AllPlayerProperties = players;
  window._AP_CoinCount = undefined;
  window._AP_GemCount = undefined;
}

module.exports = {
  restoreLostCurrency, observeCurrency, CURRENCY_FIELDS,
  st, window, reset, savedCount: () => saved,
};
