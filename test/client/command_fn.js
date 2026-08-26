// Harness for the chat command channel. See drift_test.py: the functions
// below are verbatim copies from build_pvzge_ap.py; everything above the
// dashed line is a stub that stands in for the live client.
const window = {};
let apSlotId = 1, apTeam = 0;
let st = {};
const logs = [], toasts = [];
function log(m){ logs.push(String(m)); }
function toast(m, c){ toasts.push({ msg: String(m), color: c }); }
function svSt(){ svSt.calls = (svSt.calls || 0) + 1; }

// Stands in for the real currency plumbing: the component setter path is what
// the live client prefers, so the harness models the player object it writes.
let player = null;
const CURRENCY_FIELDS = [
  { field: 'coin', granted: 'coinGranted', applied: 'coinApplied', seen: 'coinSeen' },
  { field: 'gem',  granted: 'gemGranted',  applied: 'gemApplied',  seen: 'gemSeen'  },
];
function applyPendingCurrency(){
  if(!player) return;
  for(const c of CURRENCY_FIELDS){
    const pending = (st[c.granted] || 0) - (st[c.applied] || 0);
    if(pending <= 0) continue;
    player[c.field] = (player[c.field] || 0) + pending;
    st[c.applied] = (st[c.applied] || 0) + pending;
  }
}

// ── copied verbatim from build_pvzge_ap.py ───────────────────────────────────
const AP_CHAT_PREFIX = 'pvz2';

function apChatLedger(){
  const APP = window._AP_AllPlayerProperties;
  const cp  = APP ? APP.currentPlayer : null;
  const out = [];
  for(const c of CURRENCY_FIELDS){
    const granted = st[c.granted] || 0, applied = st[c.applied] || 0;
    out.push(c.field + ': granted ' + granted + ', applied ' + applied +
             ', pending ' + (granted - applied) +
             ', on the save ' + (cp ? (cp[c.field] || 0) : '?'));
  }
  return out;
}

function apChatResync(){
  const at = st.resyncAt || (st.resyncAt = {});
  const done = [];
  for(const c of CURRENCY_FIELDS){
    const granted = st[c.granted] || 0;
    if(!granted || at[c.field] === granted) continue;
    st[c.applied] = 0;
    at[c.field] = granted;
    done.push(c.field);
  }
  svSt();
  if(!done.length){
    return ['Nothing to restore: every currency is already reconciled.']
      .concat(apChatLedger());
  }
  applyPendingCurrency();
  return ['Re-applied: ' + done.join(', ')].concat(apChatLedger());
}

const AP_CHAT_COMMANDS = {
  ledger: { help: 'show granted / applied / pending currency', run: apChatLedger },
  resync: { help: 're-apply every coin and gem this seed has granted',
            run: apChatResync },
  help:   { help: 'list these commands', run: function(){
    return Object.keys(AP_CHAT_COMMANDS).sort().map(
      k => AP_CHAT_PREFIX + ' ' + k + ' -- ' + AP_CHAT_COMMANDS[k].help);
  } },
};

function handleChatCommand(pkt){
  if(!pkt || pkt.type !== 'Chat') return false;
  if(pkt.slot !== apSlotId || (pkt.team || 0) !== apTeam) return false;
  const raw = String(pkt.message == null ? '' : pkt.message).trim();
  const parts = raw.split(/\s+/);
  if(!parts.length || parts[0].toLowerCase() !== AP_CHAT_PREFIX) return false;
  const name = (parts[1] || 'help').toLowerCase();
  const cmd = AP_CHAT_COMMANDS[name];
  if(!cmd){
    toast('Unknown command: ' + name, '#fa0');
    log('Chat command not recognised: ' + name + ' (try "' +
        AP_CHAT_PREFIX + ' help")');
    return true;
  }
  let lines;
  // A command that throws must not take the socket down with it: onPkt is
  // handling a live packet when this runs.
  try { lines = cmd.run() || []; }
  catch(e){ toast('Command failed: ' + name, '#f44');
            log('Chat command ' + name + ' failed: ' + e); return true; }
  for(const line of lines) log(line);
  toast(AP_CHAT_PREFIX + ' ' + name, '#4f4');
  return true;
}

// ── harness controls ─────────────────────────────────────────────────────────
function reset(state, cp, slot, team){
  st = state || {};
  player = cp === undefined ? { coin: 0, gem: 0 } : cp;
  apSlotId = slot === undefined ? 1 : slot;
  apTeam = team === undefined ? 0 : team;
  window._AP_AllPlayerProperties = player ? { currentPlayer: player } : null;
  logs.length = 0; toasts.length = 0; svSt.calls = 0;
}

module.exports = { handleChatCommand, reset, logs, toasts, svSt,
                   AP_CHAT_PREFIX, AP_CHAT_COMMANDS,
                   state: () => st, current: () => player };
